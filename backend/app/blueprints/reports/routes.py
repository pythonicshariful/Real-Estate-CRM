from flask import jsonify, request
from app.blueprints.reports import reports_bp
from app.models import Opportunity, Contact, PipelineStage, User, CallLog, Appointment, AppointmentStatus, Objection, ObjectionCategory, Sale, Expense, ExpenseCategory, ExpenseStatus, Invoice, InvoiceStatus, SLAEvent, SLAStatus, ActivityOutcome, PipelineHistory, db
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from datetime import datetime, timedelta, date
from sqlalchemy import func
from decimal import Decimal

def _is_admin(role):
    return role == "ADMIN"

@reports_bp.route('/kpis', methods=['GET'])
@jwt_required()
def get_reports_kpis():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    # Filter base queries by role if not admin
    def filter_by_role(q, user_id_col):
        if not _is_admin(role):
            return q.filter(user_id_col == user_id)
        return q

    # Base counts/sums
    opps_q = Opportunity.query.filter_by(is_deleted=False)
    if not _is_admin(role):
        opps_q = opps_q.filter_by(assigned_to_id=user_id)
    total_leads = opps_q.count()

    # 1. Speed-to-lead (Avg minutes from lead created_at to first CallLog created_at)
    speed_to_lead_min = 0.0
    first_calls = db.session.query(
        Opportunity.id,
        Opportunity.created_at,
        func.min(CallLog.created_at).label('first_call_at')
    ).join(CallLog, CallLog.opportunity_id == Opportunity.id)\
     .filter(Opportunity.is_deleted == False)

    if not _is_admin(role):
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
    if not _is_admin(role):
        calls_q = calls_q.filter_by(logged_by_id=user_id)
    total_calls = calls_q.count()
    if total_calls > 0:
        connected_calls = calls_q.filter_by(connected=True).count()
        contact_rate = round((connected_calls / total_calls) * 100)

    # 3. Show Rate (COMPLETED appointments / (COMPLETED + NO_SHOW))
    show_rate = 0
    appts_q = Appointment.query
    if not _is_admin(role):
        appts_q = appts_q.filter_by(scheduled_by_id=user_id)
    
    completed_appts = appts_q.filter(Appointment.status == AppointmentStatus.COMPLETED).count()
    no_show_appts = appts_q.filter(Appointment.status == AppointmentStatus.NO_SHOW).count()
    total_show_denom = completed_appts + no_show_appts
    if total_show_denom > 0:
        show_rate = round((completed_appts / total_show_denom) * 100)

    # 4. Conversion Rate (% of sold leads out of total leads)
    conversion_rate = 0.0
    closed_won = opps_q.filter(Opportunity.pipeline_stage == PipelineStage.SOLD).count()
    if total_leads > 0:
        conversion_rate = round((closed_won / total_leads) * 100, 1)

    # 5. Avg Deal Size (total sale value / count of sales)
    avg_deal_size = 0.0
    sales_q = Sale.query
    if not _is_admin(role):
        sales_q = sales_q.filter(Sale.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    total_sales_count = sales_q.count()
    if total_sales_count > 0:
        sum_sales = db.session.query(func.sum(Sale.total_sale_value))
        if not _is_admin(role):
            sum_sales = sum_sales.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = sum_sales.scalar() or 0.0
        avg_deal_size = float(total_val) / total_sales_count

    # 6. CAC (Total Marketing Expense / count of closed won sales)
    cac = 0.0
    marketing_expense_q = Expense.query.filter_by(category=ExpenseCategory.MARKETING, status=ExpenseStatus.APPROVED)
    if not _is_admin(role):
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
        if not _is_admin(role):
            sum_sales = sum_sales.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = sum_sales.scalar() or 0.0
        rev_per_100_leads = (float(total_val) / total_leads) * 100

    # 8. Lead-to-Visit (% of leads that reached VISIT_COMPLETED stage or higher)
    lead_to_visit = 0.0
    visit_or_further = [
        PipelineStage.VISIT_COMPLETED, PipelineStage.PROPOSAL_PRESENTED,
        PipelineStage.NEGOTIATION, PipelineStage.RESERVATION_RECEIVED,
        PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.SOLD
    ]
    visits_count = opps_q.filter(Opportunity.pipeline_stage.in_(visit_or_further)).count()
    if total_leads > 0:
        lead_to_visit = round((visits_count / total_leads) * 100, 1)

    # 9. Visit-to-Proposal (% of visits that went to proposal stage or higher)
    visit_to_proposal = 0.0
    proposal_or_further = [
        PipelineStage.PROPOSAL_PRESENTED, PipelineStage.NEGOTIATION,
        PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS,
        PipelineStage.SOLD
    ]
    proposal_count = opps_q.filter(Opportunity.pipeline_stage.in_(proposal_or_further)).count()
    if visits_count > 0:
        visit_to_proposal = round((proposal_count / visits_count) * 100, 1)

    # 10. Proposal-to-Close (% of proposals that closed won)
    proposal_to_close = 0.0
    if proposal_count > 0:
        proposal_to_close = round((closed_won / proposal_count) * 100, 1)

    # 11. SLA Compliance (% of SLAEvents not escalated/alerted)
    sla_compliance = 100
    sla_q = SLAEvent.query
    if not _is_admin(role):
        sla_q = sla_q.filter(SLAEvent.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    total_sla = sla_q.count()
    if total_sla > 0:
        clean_sla = sla_q.filter(~SLAEvent.status.in_([SLAStatus.ESCALATED, SLAStatus.MANAGER_ALERTED])).count()
        sla_compliance = round((clean_sla / total_sla) * 100)

    # 12. Avg Call Duration (Duration Band approximation)
    avg_call_duration = 0.0
    calls_list = filter_by_role(CallLog.query, CallLog.logged_by_id).all()
    if calls_list:
        band_mapping = {
            "UNDER_1MIN": 0.5,
            "ONE_TO_3MIN": 2.0,
            "THREE_TO_10MIN": 6.5,
            "OVER_10MIN": 12.0
        }
        vals = []
        for call in calls_list:
            if call.duration_band and call.duration_band.value in band_mapping:
                vals.append(band_mapping[call.duration_band.value])
        if vals:
            avg_call_duration = round(sum(vals) / len(vals), 1)

    # 13. First Call Resolve
    # Approximation: % of leads marked resolved or interested after exactly 1 call
    first_call_resolve = 0
    # Simplification: % of call logs with outcome INTERESTED
    interested_calls = calls_q.filter(CallLog.outcome == ActivityOutcome.INTERESTED).count()
    if total_calls > 0:
        first_call_resolve = round((interested_calls / total_calls) * 100)

    # 14. Objections/Lead
    objections_q = Objection.query
    if not _is_admin(role):
        objections_q = objections_q.filter_by(logged_by_id=user_id)
    total_objections = objections_q.count()
    objections_per_lead = 0.0
    if total_leads > 0:
        objections_per_lead = round(total_objections / total_leads, 1)

    # 15. Price Objection %
    price_objection_percent = 0
    if total_objections > 0:
        price_objs = objections_q.filter(Objection.category == ObjectionCategory.PRICE).count()
        price_objection_percent = round((price_objs / total_objections) * 100)

    # 16. Appt. No-Show rate
    appt_no_show = 0
    total_appts = appts_q.count()
    if total_appts > 0:
        no_shows = appts_q.filter(Appointment.status == AppointmentStatus.NO_SHOW).count()
        appt_no_show = round((no_shows / total_appts) * 100)

    # 17. Reassigned Leads %
    reassigned_leads = 0
    # Count opportunities with any pipeline stage change history
    history_q = PipelineHistory.query
    if not _is_admin(role):
        history_q = history_q.filter(PipelineHistory.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    changed_leads = db.session.query(func.count(func.distinct(PipelineHistory.opportunity_id))).filter(
        PipelineHistory.id.in_(db.session.query(history_q.subquery().c.id))
    ).scalar() or 0
    if total_leads > 0:
        reassigned_leads = round((changed_leads / total_leads) * 100)

    # 18. Collection Rate
    collection_rate = 0
    invoices_q = Invoice.query
    if not _is_admin(role):
        invoices_q = invoices_q.filter(Invoice.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    total_invoiced = db.session.query(func.sum(Invoice.amount)).filter(
        Invoice.id.in_(db.session.query(invoices_q.subquery().c.id)),
        Invoice.status.in_([InvoiceStatus.SENT, InvoiceStatus.PAID, InvoiceStatus.OVERDUE])
    ).scalar() or Decimal('0.00')
    total_paid = db.session.query(func.sum(Invoice.amount)).filter(
        Invoice.id.in_(db.session.query(invoices_q.subquery().c.id)),
        Invoice.status == InvoiceStatus.PAID
    ).scalar() or Decimal('0.00')

    if total_invoiced > 0:
        collection_rate = round((total_paid / total_invoiced) * 100)

    # 19. Active Pipeline (Value of non-won, non-lost opportunities)
    active_pipeline_val = 0.0
    active_stages = [
        PipelineStage.NEW, PipelineStage.ASSIGNED, PipelineStage.FIRST_CONTACT_PENDING,
        PipelineStage.CONTACT_ATTEMPTED, PipelineStage.CONNECTED, PipelineStage.QUALIFIED,
        PipelineStage.APPOINTMENT_SCHEDULED, PipelineStage.APPOINTMENT_CONFIRMED,
        PipelineStage.VISIT_COMPLETED, PipelineStage.PROPOSAL_PRESENTED, PipelineStage.NEGOTIATION,
        PipelineStage.RESERVATION_RECEIVED, PipelineStage.DOCUMENTATION_IN_PROCESS, PipelineStage.NURTURE
    ]
    # Sum estimated opportunity values
    active_opps_q = opps_q.filter(Opportunity.pipeline_stage.in_(active_stages))
    # We will approximate based on sales values or project price per sqft if available
    # Or just count of active leads * avg deal size (fallback if no direct value)
    active_pipeline_val = active_opps_q.count() * (avg_deal_size or 8600000.0)

    # 20. MoM Growth (dummy 0 for real database if no past month data)
    mom_growth = 0
    # Count leads created this month vs last month
    start_of_this_month = date.today().replace(day=1)
    start_of_last_month = (start_of_this_month - timedelta(days=1)).replace(day=1)
    
    leads_this_month = opps_q.filter(Opportunity.created_at >= start_of_this_month).count()
    leads_last_month = opps_q.filter(
        Opportunity.created_at >= start_of_last_month,
        Opportunity.created_at < start_of_this_month
    ).count()

    if leads_last_month > 0:
        mom_growth = round(((leads_this_month - leads_last_month) / leads_last_month) * 100)
    elif leads_this_month > 0:
        mom_growth = 100

    return jsonify({
        "speed_to_lead": speed_to_lead_min,
        "contact_rate": contact_rate,
        "show_rate": show_rate,
        "conversion_rate": conversion_rate,
        "avg_deal_size": avg_deal_size,
        "cac": cac,
        "rev_per_100_leads": rev_per_100_leads,
        "lead_to_visit": lead_to_visit,
        "visit_to_proposal": visit_to_proposal,
        "proposal_to_close": proposal_to_close,
        "sla_compliance": sla_compliance,
        "avg_call_duration": avg_call_duration,
        "first_call_resolve": first_call_resolve,
        "objections_per_lead": objections_per_lead,
        "price_objection_percent": price_objection_percent,
        "appt_no_show": appt_no_show,
        "reassigned_leads": reassigned_leads,
        "collection_rate": collection_rate,
        "active_pipeline_val": active_pipeline_val,
        "mom_growth": mom_growth
    })

@reports_bp.route('/charts', methods=['GET'])
@jwt_required()
def get_reports_charts():
    claims = get_jwt()
    role = claims.get('role')
    user_id = int(get_jwt_identity())

    # Filters
    opps_q = Opportunity.query.filter_by(is_deleted=False)
    if not _is_admin(role):
        opps_q = opps_q.filter_by(assigned_to_id=user_id)

    # 1. Lead Outcome Distribution
    outcome_counts = {}
    for stage in PipelineStage:
        cnt = opps_q.filter_by(pipeline_stage=stage).count()
        if cnt > 0:
            outcome_counts[stage.value] = cnt

    # 2. Objection Intelligence (Objections by Category)
    objections_q = Objection.query
    if not _is_admin(role):
        objections_q = objections_q.filter_by(logged_by_id=user_id)
    
    obj_counts = {}
    for cat in ObjectionCategory:
        cnt = objections_q.filter_by(category=cat).count()
        if cnt > 0:
            obj_counts[cat.value] = cnt

    # 3. Monthly Revenue (Full Year) - Bookings and Collections
    bookings_monthly = [0]*12
    collections_monthly = [0]*12

    sales_q = Sale.query
    if not _is_admin(role):
        sales_q = sales_q.filter(Sale.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    sales = sales_q.all()
    for s in sales:
        if s.created_at:
            m = s.created_at.month - 1
            bookings_monthly[m] += float(s.total_sale_value)

    invoices_q = Invoice.query.filter_by(status=InvoiceStatus.PAID)
    if not _is_admin(role):
        invoices_q = invoices_q.filter(Invoice.opportunity_id.in_(
            db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
        ))
    paid_invoices = invoices_q.all()
    for inv in paid_invoices:
        if inv.paid_date:
            m = inv.paid_date.month - 1
            collections_monthly[m] += float(inv.amount)
        elif inv.created_at:
            m = inv.created_at.month - 1
            collections_monthly[m] += float(inv.amount)

    # 4. CAC Trend (Last 6 Months Marketing Expense / Won Leads count)
    cac_trend_months = []
    cac_trend_values = []
    today = date.today()
    for i in range(5, -1, -1):
        target_date = today - timedelta(days=i*30)
        m_start = target_date.replace(day=1)
        # Next month start
        if m_start.month == 12:
            m_end = m_start.replace(year=m_start.year+1, month=1)
        else:
            m_end = m_start.replace(month=m_start.month+1)

        m_name = m_start.strftime("%b")
        cac_trend_months.append(m_name)

        # Won leads in month
        won_cnt = opps_q.filter(
            Opportunity.pipeline_stage == PipelineStage.SOLD,
            Opportunity.created_at >= datetime.combine(m_start, datetime.min.time()),
            Opportunity.created_at < datetime.combine(m_end, datetime.min.time())
        ).count()

        # Marketing expenses in month
        marketing_exp = Expense.query.filter(
            Expense.category == ExpenseCategory.MARKETING,
            Expense.status == ExpenseStatus.APPROVED,
            Expense.created_at >= datetime.combine(m_start, datetime.min.time()),
            Expense.created_at < datetime.combine(m_end, datetime.min.time())
        )
        if not _is_admin(role):
            marketing_exp = marketing_exp.filter_by(submitted_by_id=user_id)
        total_cost = db.session.query(func.sum(Expense.amount)).filter(
            Expense.id.in_(db.session.query(marketing_exp.subquery().c.id))
        ).scalar() or 0.0

        val = 0.0
        if won_cnt > 0:
            val = float(total_cost) / won_cnt
        elif total_cost > 0:
            val = float(total_cost)
        cac_trend_values.append(round(val))

    # 5. Show Rate by Source
    # Group appointments by opportunity -> lead_source
    show_rate_by_source = {}
    appts_q = Appointment.query
    if not _is_admin(role):
        appts_q = appts_q.filter_by(scheduled_by_id=user_id)
    
    appts = appts_q.all()
    source_appts = {}
    for a in appts:
        opp = Opportunity.query.get(a.opportunity_id)
        if opp:
            src = (opp.contact.source or opp.contact.utm_source) if opp.contact else "Other"
            if src not in source_appts:
                source_appts[src] = {"total": 0, "shows": 0}
            source_appts[src]["total"] += 1
            if a.status == AppointmentStatus.COMPLETED:
                source_appts[src]["shows"] += 1

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

        sales_in_month = Sale.query.filter(
            Sale.created_at >= datetime.combine(m_start, datetime.min.time()),
            Sale.created_at < datetime.combine(m_end, datetime.min.time())
        )
        if not _is_admin(role):
            sales_in_month = sales_in_month.filter(Sale.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_val = db.session.query(func.sum(Sale.total_sale_value)).filter(
            Sale.id.in_(db.session.query(sales_in_month.subquery().c.id))
        ).scalar() or 0.0

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

        # Avg Speed to lead in week
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
        if not _is_admin(role):
            wk_calls = wk_calls.filter(Opportunity.assigned_to_id == user_id)
        wk_calls = wk_calls.group_by(Opportunity.id).all()
        
        avg_s = 0.0
        if wk_calls:
            durations = [((f - c).total_seconds() / 60.0) for oid, c, f in wk_calls if f and c]
            if durations:
                avg_s = round(sum(durations) / len(durations), 1)
        weekly_speed.append(avg_s)

        # SLA Compliance in week
        sla_wk_q = SLAEvent.query.filter(
            SLAEvent.assigned_at >= datetime.combine(w_start, datetime.min.time()),
            SLAEvent.assigned_at < datetime.combine(w_end, datetime.min.time())
        )
        if not _is_admin(role):
            sla_wk_q = sla_wk_q.filter(SLAEvent.opportunity_id.in_(
                db.session.query(Opportunity.id).filter(Opportunity.assigned_to_id == user_id)
            ))
        total_sla = sla_wk_q.count()
        comp_rate = 100
        if total_sla > 0:
            clean_cnt = sla_wk_q.filter(~SLAEvent.status.in_([SLAStatus.ESCALATED, SLAStatus.MANAGER_ALERTED])).count()
            comp_rate = round((clean_cnt / total_sla) * 100)
        weekly_sla.append(comp_rate)

    return jsonify({
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
            "speed": weekly_speed,
            "sla": weekly_sla
        }
    })
