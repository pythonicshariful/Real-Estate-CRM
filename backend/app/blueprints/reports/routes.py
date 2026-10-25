from flask import jsonify, request, make_response
from app.blueprints.reports import reports_bp
from app.models import Opportunity, Contact, PipelineStage, User, CallLog, Appointment, AppointmentStatus, Objection, ObjectionCategory, Sale, Expense, ExpenseCategory, ExpenseStatus, Invoice, InvoiceStatus, SLAEvent, SLAStatus, ActivityOutcome, PipelineHistory, db
from app.models import UserRole
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta, date, timezone
from sqlalchemy import func
from decimal import Decimal
import io
import csv
from app.utils.rbac import is_admin

_reports_cache = {}
CACHE_TTL_SECONDS = 15

def _get_cache(key):
    entry = _reports_cache.get(key)
    if entry:
        data, ts = entry
        if (datetime.now(timezone.utc) - ts).total_seconds() < CACHE_TTL_SECONDS:
            return data
    return None

def _set_cache(key, data):
    if len(_reports_cache) > 200:
        _reports_cache.clear()
    _reports_cache[key] = (data, datetime.now(timezone.utc))

@reports_bp.route('/kpis', methods=['GET'])
@jwt_required()
def get_reports_kpis():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    # Date range filters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # In-memory fast cache lookup
    cache_key = f"kpis:{user_id}:{role}:{start_date_str}:{end_date_str}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return jsonify(cached)

    # Filter base queries by role if not admin
    def filter_by_role(q, user_id_col):
        if not is_admin(role):
            return q.filter(user_id_col == user_id)
        return q

    start_dt = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_dt = datetime.fromisoformat(end_date_str) if end_date_str else None

    # Base Opportunity query
    opps_q = Opportunity.query.filter(Opportunity.is_deleted == False)
    if not is_admin(role):
        opps_q = opps_q.filter(Opportunity.assigned_to_id == user_id)
    if start_dt:
        opps_q = opps_q.filter(Opportunity.created_at >= start_dt)
    if end_dt:
        opps_q = opps_q.filter(Opportunity.created_at <= end_dt)

    # Opportunity Stage Grouping
    stage_counts_q = db.session.query(Opportunity.pipeline_stage, func.count(Opportunity.id)).filter(Opportunity.is_deleted == False)
    if not is_admin(role):
        stage_counts_q = stage_counts_q.filter(Opportunity.assigned_to_id == user_id)
    if start_dt:
        stage_counts_q = stage_counts_q.filter(Opportunity.created_at >= start_dt)
    if end_dt:
        stage_counts_q = stage_counts_q.filter(Opportunity.created_at <= end_dt)
    stage_counts_result = stage_counts_q.group_by(Opportunity.pipeline_stage).all()
    stage_map = {row[0]: row[1] for row in stage_counts_result if row[0] is not None}
    
    total_leads = sum(stage_map.values())

    # 1. Speed-to-lead (Avg minutes from assignment to first CallLog created_at).
    # Response-time analytics are manager-only (see /response-times): for
    # EXECUTIVE / LEAD_OWNER callers this is not computed and not returned.
    is_manager_role = role in ('MANAGER', 'GM', 'CEO', 'ADMIN')
    speed_to_lead_min = 0.0
    if is_manager_role:
        first_calls = db.session.query(
            Opportunity.id,
            Opportunity.created_at,
            func.min(CallLog.created_at).label('first_call_at')
        ).join(CallLog, CallLog.opportunity_id == Opportunity.id)\
         .filter(Opportunity.is_deleted == False)

        if not is_admin(role):
            first_calls = first_calls.filter(Opportunity.assigned_to_id == user_id)

        first_calls = first_calls.group_by(Opportunity.id).all()

        if first_calls:
            durations = []
            for opp_id, created_at, first_call_at in first_calls:
                if first_call_at and created_at:
                    diff = (first_call_at - created_at).total_seconds() / 60.0
                    if diff > 0:
                        durations.append(diff)
            if durations:
                speed_to_lead_min = round(sum(durations) / len(durations), 1)

    # 2. Contact Rate (% of call logs connected vs total call logs)
    contact_rate = 0
    calls_q = CallLog.query
    if not is_admin(role):
        calls_q = calls_q.filter_by(logged_by_id=user_id)
    total_calls = calls_q.count()
    if total_calls > 0:
        connected_calls = calls_q.filter_by(connected=True).count()
        contact_rate = round((connected_calls / total_calls) * 100)

    # 3. Show Rate (COMPLETED appointments / (COMPLETED + NO_SHOW))
    show_rate = 0
    appts_q = db.session.query(Appointment.status, func.count(Appointment.id))
    if not is_admin(role):
        appts_q = appts_q.filter(Appointment.scheduled_by_id == user_id)
    appts_res = appts_q.group_by(Appointment.status).all()
    appt_map = {row[0]: row[1] for row in appts_res if row[0] is not None}
    
    completed_appts = appt_map.get(AppointmentStatus.COMPLETED, 0)
    no_show_appts = appt_map.get(AppointmentStatus.NO_SHOW, 0)
    total_appts = sum(appt_map.values())
    
    total_show_denom = completed_appts + no_show_appts
    if total_show_denom > 0:
        show_rate = round((completed_appts / total_show_denom) * 100)

    # 4. Conversion Rate (% of sold leads out of total leads)
    conversion_rate = 0.0
    closed_won = stage_map.get(PipelineStage.SOLD, 0)
    if total_leads > 0:
        conversion_rate = round((closed_won / total_leads) * 100, 1)

    # 5. Avg Deal Size (total sale value / count of sales)
    avg_deal_size = 0.0
    sales_q = Sale.query
    if not is_admin(role):
        sales_q = sales_q.filter(Sale.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    total_sales_count = sales_q.count()
    if total_sales_count > 0:
        sum_sales = db.session.query(func.sum(Sale.total_sale_value))
        if not is_admin(role):
            sum_sales = sum_sales.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = sum_sales.scalar() or 0.0
        avg_deal_size = float(total_val) / total_sales_count

    # 6. CAC (Total Marketing Expense / count of closed won sales)
    cac = 0.0
    marketing_expense_q = Expense.query.filter_by(category=ExpenseCategory.MARKETING, status=ExpenseStatus.APPROVED)
    if not is_admin(role):
        marketing_expense_q = marketing_expense_q.filter_by(submitted_by_id=user_id)
    total_marketing_cost = db.session.query(func.sum(Expense.amount)).filter(
        Expense.id.in_(db.session.query(marketing_expense_q.subquery().c.id))
    ).scalar() or Decimal('0.00')

    if closed_won > 0:
        cac = float(total_marketing_cost) / closed_won
    elif total_marketing_cost > 0:
        cac = float(total_marketing_cost)

    # 7. Rev/100 Leads
    rev_per_100_leads = 0.0
    if total_leads > 0:
        sum_sales = db.session.query(func.sum(Sale.total_sale_value))
        if not is_admin(role):
            sum_sales = sum_sales.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = sum_sales.scalar() or 0.0
        rev_per_100_leads = (float(total_val) / total_leads) * 100

    # Funnel counts for Section D 20-KPI Framework
    connected_stages = [
        PipelineStage.CONNECTED, PipelineStage.QUALIFIED, PipelineStage.APPOINTMENT_SCHEDULED,
        PipelineStage.APPOINTMENT_CONFIRMED, PipelineStage.VISIT_COMPLETED, PipelineStage.PROPOSAL_PRESENTED,
        PipelineStage.NEGOTIATION, PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS,
        PipelineStage.SOLD
    ]
    connected_leads = sum(stage_map.get(s, 0) for s in connected_stages)

    qualified_stages = [
        PipelineStage.QUALIFIED, PipelineStage.APPOINTMENT_SCHEDULED,
        PipelineStage.APPOINTMENT_CONFIRMED, PipelineStage.VISIT_COMPLETED, PipelineStage.PROPOSAL_PRESENTED,
        PipelineStage.NEGOTIATION, PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS,
        PipelineStage.SOLD
    ]
    qualified_leads = sum(stage_map.get(s, 0) for s in qualified_stages)

    # 4. Qualification Rate (Qualified leads ÷ connected leads)
    qualification_rate = round((qualified_leads / connected_leads) * 100, 1) if connected_leads > 0 else 0.0

    # 5. Appointment Booking Rate (Appointments scheduled ÷ qualified leads)
    appointment_booking_rate = round((total_appts / qualified_leads) * 100, 1) if qualified_leads > 0 else 0.0

    # 6. Confirmation Rate (Confirmed appointments ÷ scheduled appointments)
    confirmed_appts = appt_map.get(AppointmentStatus.CONFIRMED, 0) + completed_appts
    confirmation_rate = round((confirmed_appts / total_appts) * 100, 1) if total_appts > 0 else 0.0

    # 7. Show Rate (Completed visits or meetings ÷ confirmed appointments)
    show_rate = round((completed_appts / confirmed_appts) * 100, 1) if confirmed_appts > 0 else 0.0

    # 8. Visit-to-Negotiation Rate (Negotiations opened ÷ completed visits)
    negotiation_or_further = [
        PipelineStage.NEGOTIATION, PipelineStage.RESERVATION_RECEIVED,
        PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.SOLD
    ]
    negotiations_count = sum(stage_map.get(s, 0) for s in negotiation_or_further)
    visit_to_negotiation_rate = round((negotiations_count / completed_appts) * 100, 1) if completed_appts > 0 else 0.0

    # 9. Visit-to-Reservation Rate (Reservations received ÷ completed visits)
    res_or_further = [
        PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.SOLD
    ]
    reservations_count = sum(stage_map.get(s, 0) for s in res_or_further)
    visit_to_reservation_rate = round((reservations_count / completed_appts) * 100, 1) if completed_appts > 0 else 0.0

    # 10. Reservation-to-Sale Rate (Sales verified ÷ total reservations received)
    reservation_to_sale_rate = round((closed_won / reservations_count) * 100, 1) if reservations_count > 0 else 0.0

    # 11. Follow-Up Compliance (Follow-ups completed on time ÷ follow-ups due in period)
    overdue_count = opps_q.filter(Opportunity.next_action_deadline < datetime.now(timezone.utc)).count()
    total_with_deadlines = opps_q.filter(Opportunity.next_action_deadline != None).count()
    if total_with_deadlines > 0:
        follow_up_compliance = round(((total_with_deadlines - overdue_count) / total_with_deadlines) * 100, 1)
    else:
        follow_up_compliance = 100.0

    # 12. SLA Compliance % — manager-only, same gating as speed-to-lead.
    sla_compliance = 100
    if is_manager_role:
        sla_q = SLAEvent.query
        if not is_admin(role):
            sla_q = sla_q.filter(SLAEvent.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_sla = sla_q.count()
        if total_sla > 0:
            clean_sla = sla_q.filter(~SLAEvent.status.in_([SLAStatus.ESCALATED, SLAStatus.MANAGER_ALERTED])).count()
            sla_compliance = round((clean_sla / total_sla) * 100)

    # 12. Lead Aging Heatmap (Open leads grouped by age: 1 / 3 / 7 / 14 / 30 days untouched)
    now_utc = datetime.now(timezone.utc)
    terminal_stages = [PipelineStage.SOLD, PipelineStage.CLOSED_LOST, PipelineStage.INVALID, PipelineStage.UNREACHABLE, PipelineStage.BOUGHT_ELSEWHERE]
    open_leads = opps_q.filter(~Opportunity.pipeline_stage.in_(terminal_stages))\
        .with_entities(Opportunity.last_activity_at, Opportunity.created_at).all()
    aging_1d = 0
    aging_3d = 0
    aging_7d = 0
    aging_14d = 0
    aging_30d = 0
    for last_activity_at, created_at in open_leads:
        last_t = last_activity_at or created_at
        if last_t:
            if last_t.tzinfo is None: last_t = last_t.replace(tzinfo=timezone.utc)
            d_diff = (now_utc - last_t).total_seconds() / 86400.0
            if d_diff >= 30: aging_30d += 1
            elif d_diff >= 14: aging_14d += 1
            elif d_diff >= 7: aging_7d += 1
            elif d_diff >= 3: aging_3d += 1
            else: aging_1d += 1
    lead_aging_summary = f"{aging_1d}/{aging_3d}/{aging_7d}/{aging_14d}/{aging_30d}"

    # 13. Reactivation Rate (Old leads moved to Qualified ÷ total reactivation attempts)
    reactivated_count = opps_q.filter(Opportunity.pipeline_stage.in_(qualified_stages)).join(
        PipelineHistory, PipelineHistory.opportunity_id == Opportunity.id
    ).filter(PipelineHistory.from_stage == PipelineStage.NURTURE).distinct().count()
    nurture_count = stage_map.get(PipelineStage.NURTURE, 0) + reactivated_count
    reactivation_rate = round((reactivated_count / nurture_count) * 100, 1) if nurture_count > 0 else 0.0

    # 14. Closed-Lost Rate (Lost leads ÷ qualified leads with mandatory reason codes)
    lost_count = stage_map.get(PipelineStage.CLOSED_LOST, 0)
    closed_lost_rate = round((lost_count / qualified_leads) * 100, 1) if qualified_leads > 0 else 0.0

    # 15. Average Sales Cycle (Days) (Mean days from inquiry creation to verified sale)
    avg_sales_cycle_days = 0.0
    sold_opps = opps_q.filter(Opportunity.pipeline_stage == PipelineStage.SOLD)\
        .with_entities(Opportunity.sold_date, Opportunity.updated_at, Opportunity.created_at).all()
    if sold_opps:
        cycle_durations = []
        for sold_date, updated_at, created_at in sold_opps:
            end_d = sold_date or updated_at
            start_d = created_at
            if end_d and start_d:
                if end_d.tzinfo is None: end_d = end_d.replace(tzinfo=timezone.utc)
                if start_d.tzinfo is None: start_d = start_d.replace(tzinfo=timezone.utc)
                d_days = (end_d - start_d).total_seconds() / 86400.0
                if d_days >= 0:
                    cycle_durations.append(d_days)
        if cycle_durations:
            avg_sales_cycle_days = round(sum(cycle_durations) / len(cycle_durations), 1)

    # 16. Revenue per 100 Leads
    rev_per_100_leads = 0.0
    sum_sales = db.session.query(func.sum(Sale.total_sale_value))
    if not is_admin(role):
        sum_sales = sum_sales.filter(Sale.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    total_val = sum_sales.scalar() or 0.0
    if total_leads > 0:
        rev_per_100_leads = round((float(total_val) / total_leads) * 100, 2)

    # 17. Collection Rate (Amount collected ÷ amount contractually due per period)
    collection_rate = 0.0
    inv_totals_q = db.session.query(
        func.sum(Invoice.amount),
        func.sum(db.case((Invoice.status == InvoiceStatus.PAID, Invoice.amount), else_=0))
    ).filter(Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PAID, InvoiceStatus.OVERDUE]))
    if not is_admin(role):
        inv_totals_q = inv_totals_q.filter(Invoice.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    inv_res = inv_totals_q.first()
    total_invoiced = float(inv_res[0] or 0.0) if inv_res else 0.0
    total_paid = float(inv_res[1] or 0.0) if inv_res else 0.0
    if total_invoiced > 0:
        collection_rate = round((total_paid / total_invoiced) * 100, 1)

    # 18. Source Conversion Rate (Sales from Campaign X ÷ leads from Campaign X) - overall conversion
    conversion_rate = round((closed_won / total_leads) * 100, 1) if total_leads > 0 else 0.0

    # 19. Cost per Completed Visit (Total marketing spend ÷ number of completed site visits)
    cost_per_completed_visit = 0.0
    if completed_appts > 0 and total_marketing_cost > 0:
        cost_per_completed_visit = round(float(total_marketing_cost) / completed_appts, 2)

    # 20. Customer Acquisition Cost (Total sales + marketing cost ÷ verified customers acquired)
    cac = 0.0
    if closed_won > 0 and total_marketing_cost > 0:
        cac = round(float(total_marketing_cost) / closed_won, 2)

    # Additional secondary operational helpers
    active_stages = [
        PipelineStage.NEW, PipelineStage.ASSIGNED, PipelineStage.FIRST_CONTACT_PENDING,
        PipelineStage.CONTACT_ATTEMPTED, PipelineStage.CONNECTED, PipelineStage.QUALIFIED,
        PipelineStage.APPOINTMENT_SCHEDULED, PipelineStage.APPOINTMENT_CONFIRMED,
        PipelineStage.VISIT_COMPLETED, PipelineStage.PROPOSAL_PRESENTED, PipelineStage.NEGOTIATION,
        PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.NURTURE
    ]
    active_leads_count = sum(stage_map.get(s, 0) for s in active_stages)
    active_pipeline_val = active_leads_count * (avg_deal_size or 8600000.0)

    result_payload = {
        # 20 Architecture v2.0 Section D Metrics
        # NOTE: speed_to_lead / sla_compliance are added below only for
        # manager roles — executives must not see response-time analytics.
        "contact_rate": contact_rate,
        "qualification_rate": qualification_rate,
        "appointment_booking_rate": appointment_booking_rate,
        "confirmation_rate": confirmation_rate,
        "show_rate": show_rate,
        "visit_to_negotiation_rate": visit_to_negotiation_rate,
        "visit_to_reservation_rate": visit_to_reservation_rate,
        "reservation_to_sale_rate": reservation_to_sale_rate,
        "follow_up_compliance": follow_up_compliance,
        "lead_aging_summary": lead_aging_summary,
        "lead_aging_heatmap": {
            "1d": aging_1d,
            "3d": aging_3d,
            "7d": aging_7d,
            "14d": aging_14d,
            "30d_plus": aging_30d
        },
        "reactivation_rate": reactivation_rate,
        "closed_lost_rate": closed_lost_rate,
        "average_sales_cycle_days": avg_sales_cycle_days,
        "revenue_per_100_leads": rev_per_100_leads,
        "collection_rate": collection_rate,
        "source_conversion_rate": conversion_rate,
        "cost_per_completed_visit": cost_per_completed_visit,
        "customer_acquisition_cost": cac,
        "conversion_rate": conversion_rate,

        # Backwards compatible aliases
        "avg_deal_size": avg_deal_size,
        "cac": cac,
        "rev_per_100_leads": rev_per_100_leads,
        "active_pipeline_val": active_pipeline_val,
        "total_leads": total_leads,
        "completed_appts": completed_appts,
        "closed_won": closed_won
    }
    if is_manager_role:
        result_payload["speed_to_lead"] = speed_to_lead_min
        result_payload["sla_compliance"] = sla_compliance
    _set_cache(cache_key, result_payload)
    return jsonify(result_payload)

@reports_bp.route('/response-times', methods=['GET'])
@jwt_required()
def get_response_times():
    """Manager-only response-time analytics (client requirement 2).

    Response time for a lead = first CallLog.created_at minus the
    assignment start, where the start is Opportunity.assigned_date,
    falling back to the earliest SLAEvent.assigned_at for that lead,
    then Opportunity.created_at. Leads with no call yet report
    response_minutes=None and status "uncontacted".

    assigned_date / first_contact_date are exposed ONLY here — they are
    deliberately not added to Opportunity.to_dict(), which executives see.
    Roles MANAGER / GM / CEO / ADMIN only; everyone else gets 403.
    """
    claims = get_jwt()
    role = claims.get('role')
    if role not in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        return jsonify({"error": "Manager access required: response-time analytics are manager-only"}), 403

    assigned_to_filter = request.args.get('assigned_to_id') or request.args.get('executive_id')
    opps_q = Opportunity.query.filter(Opportunity.is_deleted == False)
    if assigned_to_filter:
        try:
            opps_q = opps_q.filter(Opportunity.assigned_to_id == int(assigned_to_filter))
        except ValueError:
            return jsonify({"error": "Invalid assigned_to_id"}), 400
    opps = opps_q.order_by(Opportunity.created_at.desc()).all()
    opp_ids = [o.id for o in opps]

    first_calls = {}
    if opp_ids:
        rows = db.session.query(
            CallLog.opportunity_id, func.min(CallLog.created_at).label('first_call_at')
        ).filter(CallLog.opportunity_id.in_(opp_ids)).group_by(CallLog.opportunity_id).all()
        first_calls = {r[0]: r[1] for r in rows}
    sla_by_opp = {}
    if opp_ids:
        for sla in SLAEvent.query.filter(SLAEvent.opportunity_id.in_(opp_ids)).order_by(SLAEvent.assigned_at.asc()).all():
            sla_by_opp.setdefault(sla.opportunity_id, sla)

    per_lead = []
    per_exec = {}
    for opp in opps:
        sla = sla_by_opp.get(opp.id)
        start = opp.assigned_date or (sla.assigned_at if sla else None) or opp.created_at
        first_call_at = first_calls.get(opp.id)
        response_minutes = None
        if first_call_at and start:
            diff = (first_call_at - start).total_seconds() / 60.0
            if diff >= 0:
                response_minutes = round(diff, 1)
        first_contact = opp.first_contact_date or first_call_at
        row = {
            "lead_id": opp.id,
            "contact_name": opp.contact.full_name if opp.contact else None,
            "assigned_to_id": opp.assigned_to_id,
            "assigned_to_name": opp.assigned_to.full_name if opp.assigned_to else None,
            "assigned_date": opp.assigned_date.isoformat() if opp.assigned_date else None,
            "first_contact_date": first_contact.isoformat() if first_contact else None,
            "first_call_at": first_call_at.isoformat() if first_call_at else None,
            "response_minutes": response_minutes,
            "status": "contacted" if first_call_at else "uncontacted",
            "sla_status": sla.status.value if sla and sla.status else None,
        }
        per_lead.append(row)
        key = opp.assigned_to_id
        bucket = per_exec.setdefault(key, {
            "assigned_to_id": key,
            "assigned_to_name": opp.assigned_to.full_name if opp.assigned_to else None,
            "total_leads": 0, "contacted_leads": 0, "uncontacted_leads": 0,
            "_minutes": [],
        })
        bucket["total_leads"] += 1
        if first_call_at:
            bucket["contacted_leads"] += 1
            if response_minutes is not None:
                bucket["_minutes"].append(response_minutes)
        else:
            bucket["uncontacted_leads"] += 1

    per_executive = []
    for bucket in per_exec.values():
        minutes = bucket.pop("_minutes")
        per_executive.append({
            **bucket,
            "avg_response_minutes": round(sum(minutes) / len(minutes), 1) if minutes else None,
        })
    per_executive.sort(key=lambda b: (b["avg_response_minutes"] is None, b["avg_response_minutes"] or 0))

    contacted = [r["response_minutes"] for r in per_lead if r["response_minutes"] is not None]
    return jsonify({
        "per_lead": per_lead,
        "per_executive": per_executive,
        "summary": {
            "total_leads": len(per_lead),
            "contacted_leads": len(contacted),
            "uncontacted_leads": len(per_lead) - len(contacted),
            "avg_response_minutes": round(sum(contacted) / len(contacted), 1) if contacted else None,
        },
    }), 200


@reports_bp.route('/charts', methods=['GET'])
@jwt_required()
def get_reports_charts():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    # Date range filters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Fast in-memory cache lookup
    cache_key = f"charts:{user_id}:{role}:{start_date_str}:{end_date_str}"
    cached = _get_cache(cache_key)
    if cached is not None:
        return jsonify(cached)

    start_dt = datetime.fromisoformat(start_date_str) if start_date_str else None
    end_dt = datetime.fromisoformat(end_date_str) if end_date_str else None

    # Base Opportunity query
    opps_q = Opportunity.query.filter_by(is_deleted=False)
    if not is_admin(role):
        opps_q = opps_q.filter_by(assigned_to_id=user_id)
    if start_dt:
        opps_q = opps_q.filter(Opportunity.created_at >= start_dt)
    if end_dt:
        opps_q = opps_q.filter(Opportunity.created_at <= end_dt)

    # 1. Lead Outcome Distribution (1 single GROUP BY query instead of 21 loops)
    outcome_counts = {}
    stage_counts_res = db.session.query(Opportunity.pipeline_stage, func.count(Opportunity.id))\
        .filter(Opportunity.is_deleted == False)
    if not is_admin(role):
        stage_counts_res = stage_counts_res.filter(Opportunity.assigned_to_id == user_id)
    if start_dt:
        stage_counts_res = stage_counts_res.filter(Opportunity.created_at >= start_dt)
    if end_dt:
        stage_counts_res = stage_counts_res.filter(Opportunity.created_at <= end_dt)
    for stage_val, cnt in stage_counts_res.group_by(Opportunity.pipeline_stage).all():
        if stage_val and cnt > 0:
            key = stage_val.value if hasattr(stage_val, 'value') else str(stage_val)
            outcome_counts[key] = cnt

    # 2. Objection Intelligence (1 single GROUP BY query instead of looping)
    obj_counts = {}
    obj_res = db.session.query(Objection.category, func.count(Objection.id))
    if not is_admin(role):
        obj_res = obj_res.filter(Objection.logged_by_id == user_id)
    for cat_val, cnt in obj_res.group_by(Objection.category).all():
        if cat_val and cnt > 0:
            key = cat_val.value if hasattr(cat_val, 'value') else str(cat_val)
            obj_counts[key] = cnt

    # 3. Monthly Revenue (Full Year) - Bookings and Collections
    bookings_monthly = [0]*12
    collections_monthly = [0]*12

    sales_q = db.session.query(Sale.created_at, Sale.total_sale_value)
    if not is_admin(role):
        sales_q = sales_q.filter(Sale.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    for created_at, val in sales_q.all():
        if created_at and val:
            m = created_at.month - 1
            if 0 <= m < 12:
                bookings_monthly[m] += float(val)

    invoices_q = db.session.query(Invoice.paid_date, Invoice.created_at, Invoice.amount).filter(Invoice.status == InvoiceStatus.PAID)
    if not is_admin(role):
        invoices_q = invoices_q.filter(Invoice.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    for paid_date, created_at, amt in invoices_q.all():
        t = paid_date or created_at
        if t and amt:
            m = t.month - 1
            if 0 <= m < 12:
                collections_monthly[m] += float(amt)

    # 4. CAC Trend (Last 6 Months Marketing Expense / Won Leads count)
    cac_trend_months = []
    cac_trend_values = []
    today = date.today()
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        m_start = target_date.replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year+1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month+1)

        m_name = m_start.strftime("%b")
        cac_trend_months.append(m_name)

        won_cnt = opps_q.filter(
            Opportunity.pipeline_stage == PipelineStage.SOLD,
            Opportunity.created_at >= datetime.combine(m_start, datetime.min.time()),
            Opportunity.created_at < datetime.combine(m_end, datetime.min.time())
        ).count()

        exp_q = db.session.query(func.sum(Expense.amount)).filter(
            Expense.category == ExpenseCategory.MARKETING,
            Expense.status == ExpenseStatus.APPROVED,
            Expense.created_at >= datetime.combine(m_start, datetime.min.time()),
            Expense.created_at < datetime.combine(m_end, datetime.min.time())
        )
        if not is_admin(role):
            exp_q = exp_q.filter(Expense.submitted_by_id == user_id)
        total_cost = exp_q.scalar() or 0.0

        val = 0.0
        if won_cnt > 0:
            val = float(total_cost) / won_cnt
        elif total_cost > 0:
            val = float(total_cost)
        cac_trend_values.append(round(val))

    # 5. Show Rate by Source (Single SQL JOIN - fixes N+1 query issue)
    show_rate_by_source = {}
    appt_sources = db.session.query(
        Contact.source,
        Contact.utm_source,
        Appointment.status,
        func.count(Appointment.id)
    ).join(Opportunity, Appointment.opportunity_id == Opportunity.id)\
     .outerjoin(Contact, Opportunity.contact_id == Contact.id)
    if not is_admin(role):
        appt_sources = appt_sources.filter(Appointment.scheduled_by_id == user_id)
    appt_sources = appt_sources.group_by(Contact.source, Contact.utm_source, Appointment.status).all()

    source_appts = {}
    for src_name, utm_src, status, cnt in appt_sources:
        src = src_name or utm_src or "Other"
        if src not in source_appts:
            source_appts[src] = {"total": 0, "shows": 0}
        source_appts[src]["total"] += cnt
        if status == AppointmentStatus.COMPLETED:
            source_appts[src]["shows"] += cnt

    for src, vals in source_appts.items():
        if vals["total"] > 0:
            show_rate_by_source[src] = round((vals["shows"] / vals["total"]) * 100)

    # 6. Revenue per 100 Leads Trend
    rev_per_100_trend = []
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        m_start = target_date.replace(day=1)
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year+1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month+1)

        leads_cnt = opps_q.filter(
            Opportunity.created_at >= datetime.combine(m_start, datetime.min.time()),
            Opportunity.created_at < datetime.combine(m_end, datetime.min.time())
        ).count()

        sales_sum_q = db.session.query(func.sum(Sale.total_sale_value)).filter(
            Sale.created_at >= datetime.combine(m_start, datetime.min.time()),
            Sale.created_at < datetime.combine(m_end, datetime.min.time())
        )
        if not is_admin(role):
            sales_sum_q = sales_sum_q.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = sales_sum_q.scalar() or 0.0

        val = 0.0
        if leads_cnt > 0:
            val = (float(total_val) / leads_cnt) * 100
        rev_per_100_trend.append(round(val))

    # 7. Speed-to-Lead vs SLA Compliance Trend (Last 6 weeks)
    weekly_labels = []
    weekly_speed = []
    weekly_sla = []
    for i in range(5, -1, -1):
        w_start = today - timedelta(weeks=i) - timedelta(days=today.weekday())
        w_end = w_start + timedelta(days=7)
        weekly_labels.append(f"Wk -{i}" if i > 0 else "This Wk")

        wk_calls = db.session.query(
            Opportunity.id,
            Opportunity.created_at,
            func.min(CallLog.created_at).label('first_call_at')
        ).join(CallLog, CallLog.opportunity_id == Opportunity.id)\
         .filter(
             Opportunity.is_deleted == False,
             Opportunity.created_at >= datetime.combine(w_start, datetime.min.time()),
             Opportunity.created_at < datetime.combine(w_end, datetime.min.time())
         )
        if not is_admin(role):
            wk_calls = wk_calls.filter(Opportunity.assigned_to_id == user_id)
        wk_calls = wk_calls.group_by(Opportunity.id).all()
        
        avg_s = 0.0
        if wk_calls:
            durations = [((f - c).total_seconds() / 60.0) for oid, c, f in wk_calls if f and c]
            if durations:
                avg_s = round(sum(durations) / len(durations), 1)
        weekly_speed.append(avg_s)

        sla_wk_q = SLAEvent.query.filter(
            SLAEvent.assigned_at >= datetime.combine(w_start, datetime.min.time()),
            SLAEvent.assigned_at < datetime.combine(w_end, datetime.min.time())
        )
        if not is_admin(role):
            sla_wk_q = sla_wk_q.filter(SLAEvent.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_sla = sla_wk_q.count()
        comp_rate = 100
        if total_sla > 0:
            clean_cnt = sla_wk_q.filter(~SLAEvent.status.in_([SLAStatus.ESCALATED, SLAStatus.MANAGER_ALERTED])).count()
            comp_rate = round((clean_cnt / total_sla) * 100)
        weekly_sla.append(comp_rate)

    charts_payload = {
        "lead_outcome": outcome_counts,
        "objection_intelligence": obj_counts,
        "revenue_monthly": {
            "bookings": bookings_monthly,
            "collections": collections_monthly
        },
        "cac_trend": {
            "months": cac_trend_months,
            "values": cac_trend_values
        },
        "show_rate_by_source": show_rate_by_source,
        "rev_per_100_leads_trend": rev_per_100_trend,
        "weekly_trends": {
            "labels": weekly_labels,
            # Response-time trend data is manager-only; non-managers get
            # empty series so no response-time analytics leak via /charts.
            "speed": weekly_speed if role in ('MANAGER', 'GM', 'CEO', 'ADMIN') else [],
            "sla": weekly_sla if role in ('MANAGER', 'GM', 'CEO', 'ADMIN') else []
        }
    }
    _set_cache(cache_key, charts_payload)
    return jsonify(charts_payload)


@reports_bp.route('/export/leads', methods=['GET'])
@jwt_required()
def export_leads_csv():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    # Only managers and admins can export
    if role not in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        return jsonify({"error": "Export permission required (Manager or higher)"}), 403

    query = db.session.query(Opportunity, Contact).outerjoin(
        Contact, Opportunity.contact_id == Contact.id
    ).filter(Opportunity.is_deleted == False)

    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    if start_date_str:
        query = query.filter(Opportunity.created_at >= datetime.fromisoformat(start_date_str))
    if end_date_str:
        query = query.filter(Opportunity.created_at <= datetime.fromisoformat(end_date_str))

    leads_data = query.order_by(Opportunity.created_at.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'Lead ID', 'Full Name', 'Phone', 'Email', 'Profession', 'Service Type', 'Source',
        'Pipeline Stage', 'Priority', 'Lead Temperature',
        'Assigned To', 'Created At'
    ])

    for opp, contact in leads_data:
        writer.writerow([
            opp.id,
            contact.full_name if contact else '',
            contact.phone_raw if contact else '',
            contact.email if contact else '',
            contact.profession if contact else '',
            opp.service_type or (contact.service_type if contact else ''),
            contact.source if contact else '',
            opp.pipeline_stage.value if opp.pipeline_stage else '',
            opp.priority.value if opp.priority else '',
            opp.lead_temperature if isinstance(opp.lead_temperature, str) else (opp.lead_temperature.value if opp.lead_temperature else ''),
            opp.assigned_to.full_name if opp.assigned_to else 'Unassigned',
            opp.created_at.isoformat() if opp.created_at else ''
        ])

    csv_data = output.getvalue()
    response = make_response(csv_data)
    response.headers['Content-Disposition'] = f'attachment; filename=leads_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response


# ---------------------------------------------------------------------------
# Sales Manager Command Center / Dashboard Summary
# ---------------------------------------------------------------------------

@reports_bp.route('/sales-manager-summary', methods=['GET'])
@jwt_required()
def get_sales_manager_summary():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    if role not in ('MANAGER', 'GM', 'CEO', 'ADMIN'):
        return jsonify({"error": "Manager role required"}), 403

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)

    terminal_stages = [
        PipelineStage.SOLD,
        PipelineStage.CLOSED_LOST,
        PipelineStage.INVALID,
        PipelineStage.BOUGHT_ELSEWHERE,
        PipelineStage.UNREACHABLE
    ]

    # 1. Team Members Workload & Metrics
    lead_owners = User.query.filter(
        User.role.in_([UserRole.LEAD_OWNER, UserRole.EXECUTIVE, UserRole.MANAGER]),
        User.is_active == True,
        User.is_deleted == False
    ).all()

    team_metrics = []
    for owner in lead_owners:
        total_assigned = Opportunity.query.filter_by(assigned_to_id=owner.id, is_deleted=False).count()
        active_leads = Opportunity.query.filter(
            Opportunity.assigned_to_id == owner.id,
            Opportunity.is_deleted == False,
            ~Opportunity.pipeline_stage.in_(terminal_stages)
        ).count()
        
        overdue_leads = Opportunity.query.filter(
            Opportunity.assigned_to_id == owner.id,
            Opportunity.is_deleted == False,
            ~Opportunity.pipeline_stage.in_(terminal_stages),
            Opportunity.next_action_deadline < now
        ).count()

        won_leads = Opportunity.query.filter(
            Opportunity.assigned_to_id == owner.id,
            Opportunity.is_deleted == False,
            Opportunity.pipeline_stage.in_([PipelineStage.SOLD, PipelineStage.RESERVATION_RECEIVED])
        ).count()

        calls_today = CallLog.query.filter(
            CallLog.logged_by_id == owner.id,
            CallLog.created_at >= today_start,
            CallLog.is_deleted == False
        ).count()

        max_cap = owner.max_lead_capacity or 30
        cap_pct = round((active_leads / max_cap) * 100) if max_cap > 0 else 0
        conv_rate = round((won_leads / total_assigned) * 100, 1) if total_assigned > 0 else 0.0

        team_metrics.append({
            "id": owner.id,
            "full_name": owner.full_name,
            "email": owner.email,
            "role": owner.role.value if owner.role else "LEAD_OWNER",
            "calendar_color": owner.calendar_color or "#6366f1",
            "avatar_url": owner.avatar_url or "/assets/img/default-avatar.png",
            "max_capacity": max_cap,
            "active_leads": active_leads,
            "capacity_pct": cap_pct,
            "overdue_leads": overdue_leads,
            "won_leads": won_leads,
            "calls_today": calls_today,
            "conversion_rate": conv_rate
        })

    # 2. Unassigned Leads Queue
    unassigned_opps = db.session.query(Opportunity, Contact).outerjoin(
        Contact, Opportunity.contact_id == Contact.id
    ).filter(
        Opportunity.assigned_to_id.is_(None),
        Opportunity.is_deleted == False,
        ~Opportunity.pipeline_stage.in_(terminal_stages)
    ).order_by(Opportunity.created_at.desc()).limit(15).all()

    unassigned_list = []
    for opp, contact in unassigned_opps:
        unassigned_list.append({
            "id": opp.id,
            "contact_name": contact.full_name if contact else "Valued Client",
            "phone": contact.phone_raw if contact else "N/A",
            "service_type": opp.service_type or (contact.service_type if contact else None),
            "profession": contact.profession if contact else None,
            "source": contact.source if contact else "Web",
            "created_at": opp.created_at.isoformat() if opp.created_at else None
        })

    # 3. Urgent / Overdue Action Items Queue
    urgent_opps = db.session.query(Opportunity, Contact, User).outerjoin(
        Contact, Opportunity.contact_id == Contact.id
    ).outerjoin(
        User, Opportunity.assigned_to_id == User.id
    ).filter(
        Opportunity.is_deleted == False,
        ~Opportunity.pipeline_stage.in_(terminal_stages),
        Opportunity.next_action_deadline < now
    ).order_by(Opportunity.next_action_deadline.asc()).limit(15).all()

    urgent_list = []
    for opp, contact, user in urgent_opps:
        deadline_iso = opp.next_action_deadline.isoformat() if opp.next_action_deadline else None
        urgent_list.append({
            "id": opp.id,
            "contact_name": contact.full_name if contact else "Valued Client",
            "phone": contact.phone_raw if contact else "N/A",
            "assigned_to": user.full_name if user else "Unassigned",
            "stage": opp.pipeline_stage.value if opp.pipeline_stage else "NEW",
            "deadline": deadline_iso,
            "priority": opp.priority.value if opp.priority else "HIGH"
        })

    # 4. Stage Breakdown
    stage_counts = db.session.query(Opportunity.pipeline_stage, func.count(Opportunity.id))\
        .filter(Opportunity.is_deleted == False)\
        .group_by(Opportunity.pipeline_stage).all()
    stage_map = {row[0].value if row[0] else "NEW": row[1] for row in stage_counts}

    total_pipeline_leads = sum(v for k, v in stage_map.items() if k not in ['SOLD', 'CLOSED_LOST', 'INVALID', 'BOUGHT_ELSEWHERE', 'UNREACHABLE'])

    return jsonify({
        "status": "success",
        "manager_id": user_id,
        "team": team_metrics,
        "team_metrics": {
            "total_agents": len(team_metrics),
            "unassigned_leads": len(unassigned_list),
            "total_overdue": sum(m["overdue_leads"] for m in team_metrics),
            "total_won": sum(m["won_leads"] for m in team_metrics),
            "total_active_pipeline_leads": total_pipeline_leads
        },
        "agent_workload": team_metrics,
        "unassigned_queue": unassigned_list,
        "urgent_queue": urgent_list,
        "urgent_sla_queue": urgent_list,
        "stage_breakdown": stage_map,
        "kpis": {
            "total_team_members": len(team_metrics),
            "total_active_pipeline_leads": total_pipeline_leads,
            "unassigned_count": len(unassigned_list),
            "total_overdue": sum(m["overdue_leads"] for m in team_metrics),
            "total_calls_today": sum(m["calls_today"] for m in team_metrics),
            "total_won": sum(m["won_leads"] for m in team_metrics)
        }
    }), 200

