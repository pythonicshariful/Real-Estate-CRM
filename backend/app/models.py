from datetime import datetime
from enum import Enum as PyEnum
from app.extensions import db
import bcrypt
import pyotp

class PipelineStage(PyEnum):
    NEW = "NEW"
    ASSIGNED = "ASSIGNED"
    FIRST_CONTACT_PENDING = "FIRST_CONTACT_PENDING"
    CONTACT_ATTEMPTED = "CONTACT_ATTEMPTED"
    CONNECTED = "CONNECTED"
    QUALIFIED = "QUALIFIED"
    DISQUALIFIED = "DISQUALIFIED"
    APPOINTMENT_SCHEDULED = "APPOINTMENT_SCHEDULED"
    APPOINTMENT_CONFIRMED = "APPOINTMENT_CONFIRMED"
    VISIT_COMPLETED = "VISIT_COMPLETED"
    PROPOSAL_PRESENTED = "PROPOSAL_PRESENTED"
    NEGOTIATION = "NEGOTIATION"
    RESERVATION_RECEIVED = "RESERVATION_RECEIVED"
    DOCUMENTATION_IN_PROCESS = "DOCUMENTATION_IN_PROCESS"
    SOLD = "SOLD"
    NURTURE = "NURTURE"
    CLOSED_LOST = "CLOSED_LOST"
    INVALID = "INVALID"
    BOUGHT_ELSEWHERE = "BOUGHT_ELSEWHERE"
    UNREACHABLE = "UNREACHABLE"

class UserRole(PyEnum):
    ADMIN = "ADMIN"
    LEAD_OWNER = "LEAD_OWNER"

class ActivityType(PyEnum):
    CALL = "CALL"
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"
    VISIT = "VISIT"
    MEETING = "MEETING"
    NOTE = "NOTE"

class ActivityOutcome(PyEnum):
    CONNECTED = "CONNECTED"
    NOT_CONNECTED = "NOT_CONNECTED"
    VOICEMAIL = "VOICEMAIL"
    BUSY = "BUSY"
    WRONG_NUMBER = "WRONG_NUMBER"
    INTERESTED = "INTERESTED"
    NOT_INTERESTED = "NOT_INTERESTED"
    CALLBACK_REQUESTED = "CALLBACK_REQUESTED"

class LeadTemperature(PyEnum):
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    FROZEN = "FROZEN"

class AppointmentStatus(PyEnum):
    SCHEDULED = "SCHEDULED"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"

class FinalResult(PyEnum):
    SOLD = "SOLD"
    CLOSED_LOST = "CLOSED_LOST"
    NURTURE = "NURTURE"
    INVALID = "INVALID"
    BOUGHT_ELSEWHERE = "BOUGHT_ELSEWHERE"
    UNREACHABLE = "UNREACHABLE"

class DurationBand(PyEnum):
    UNDER_1MIN = "UNDER_1MIN"
    ONE_TO_3MIN = "ONE_TO_3MIN"
    THREE_TO_10MIN = "THREE_TO_10MIN"
    OVER_10MIN = "OVER_10MIN"

class SLAStatus(PyEnum):
    PENDING = "PENDING"
    NOTIFIED = "NOTIFIED"
    REMINDED = "REMINDED"
    MANAGER_ALERTED = "MANAGER_ALERTED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"

class ObjectionCategory(PyEnum):
    PRICE = "PRICE"
    DISTANCE = "DISTANCE"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    COMPETITOR = "COMPETITOR"
    TIMING = "TIMING"
    FINANCING = "FINANCING"
    OTHER = "OTHER"

class PaymentMethod(PyEnum):
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    BANK_TRANSFER = "BANK_TRANSFER"
    MOBILE_BANKING = "MOBILE_BANKING"

class TaskPriority(PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class TaskStatus(PyEnum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class ProjectStatus(PyEnum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ON_HOLD = "ON_HOLD"

class LeaveType(PyEnum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    UNPAID = "UNPAID"

class LeaveStatus(PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.LEAD_OWNER)
    is_active = db.Column(db.Boolean, default=True)
    is_mfa_enabled = db.Column(db.Boolean, default=False)
    mfa_secret = db.Column(db.String(32))
    mfa_verified = db.Column(db.Boolean, default=False)
    avatar_url = db.Column(db.String(255))
    calendar_color = db.Column(db.String(7), default="#6366f1")
    max_lead_capacity = db.Column(db.Integer, default=30)
    schedule_from_date = db.Column(db.Date, nullable=True)
    schedule_to_date = db.Column(db.Date, nullable=True)
    schedule_start_time = db.Column(db.Time, nullable=True)
    schedule_end_time = db.Column(db.Time, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    deactivated_at = db.Column(db.DateTime)
    deactivated_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    def set_password(self, password):
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
        
    def get_totp_uri(self):
        if not self.mfa_secret:
            self.mfa_secret = pyotp.random_base32()
            db.session.commit()
        return pyotp.totp.TOTP(self.mfa_secret).provisioning_uri(name=self.email, issuer_name="CRMForSouth")
        
    def verify_totp(self, token):
        if not self.mfa_secret: return False
        totp = pyotp.TOTP(self.mfa_secret)
        return totp.verify(token)

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "full_name": self.full_name,
            "phone": self.phone,
            "role": self.role.value if self.role else None,
            "is_active": self.is_active,
            "max_lead_capacity": self.max_lead_capacity,
            "calendar_color": self.calendar_color,
            "schedule_from_date": self.schedule_from_date.isoformat() if self.schedule_from_date else None,
            "schedule_to_date": self.schedule_to_date.isoformat() if self.schedule_to_date else None,
            "schedule_start_time": self.schedule_start_time.strftime('%H:%M') if self.schedule_start_time else None,
            "schedule_end_time": self.schedule_end_time.strftime('%H:%M') if self.schedule_end_time else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Contact(db.Model):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    phone_raw = db.Column(db.String(50))
    phone_normalized = db.Column(db.String(20), unique=True)
    phone_hash = db.Column(db.String(64), index=True)
    gender = db.Column(db.String(10))
    address = db.Column(db.Text)
    district = db.Column(db.String(100))
    city = db.Column(db.String(100))
    source = db.Column(db.String(100))
    utm_source = db.Column(db.String(100))
    utm_medium = db.Column(db.String(100))
    utm_campaign = db.Column(db.String(100))
    facebook_lead_id = db.Column(db.String(100), unique=True)
    is_duplicate = db.Column(db.Boolean, default=False)
    duplicate_of_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    consent_given = db.Column(db.Boolean, default=False)
    consent_date = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)
    
    inquiries = db.relationship('Inquiry', backref='contact', lazy=True)
    opportunities = db.relationship('Opportunity', backref='contact', lazy=True)


class Inquiry(db.Model):
    __tablename__ = 'inquiries'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    campaign_id = db.Column(db.String(100))
    adset_id = db.Column(db.String(100))
    ad_id = db.Column(db.String(100))
    form_id = db.Column(db.String(100))
    utm_source = db.Column(db.String(100))
    utm_medium = db.Column(db.String(100))
    utm_campaign = db.Column(db.String(100))
    utm_content = db.Column(db.String(100))
    utm_term = db.Column(db.String(100))
    raw_payload = db.Column(db.JSON)
    project_interest = db.Column(db.String(100))
    budget_min = db.Column(db.Numeric(12, 2))
    budget_max = db.Column(db.Numeric(12, 2))
    submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    opportunities = db.relationship('Opportunity', backref='inquiry', lazy=True)


class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    code = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.Text)
    location = db.Column(db.String(255))
    total_units = db.Column(db.Integer)
    available_units = db.Column(db.Integer)
    price_per_sqft = db.Column(db.Numeric(12, 2))
    status = db.Column(db.Enum(ProjectStatus), default=ProjectStatus.ACTIVE)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Opportunity(db.Model):
    __tablename__ = 'opportunities'
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiries.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pipeline_stage = db.Column(db.Enum(PipelineStage), default=PipelineStage.NEW)
    last_activity_type = db.Column(db.Enum(ActivityType))
    last_activity_outcome = db.Column(db.Enum(ActivityOutcome))
    last_activity_at = db.Column(db.DateTime)
    next_action_type = db.Column(db.Enum(ActivityType))
    next_action_owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    next_action_deadline = db.Column(db.DateTime)
    appointment_status = db.Column(db.Enum(AppointmentStatus))
    lead_temperature = db.Column(db.Enum(LeadTemperature), default=LeadTemperature.COLD)
    is_starred = db.Column(db.Boolean, default=False)
    manager_assessment = db.Column(db.Text)
    manager_label = db.Column(db.String(100))
    final_result = db.Column(db.Enum(FinalResult))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    total_deal_value = db.Column(db.Numeric(15, 2))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_deleted = db.Column(db.Boolean, default=False)
    deleted_at = db.Column(db.DateTime)

    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])
    project = db.relationship('Project')

    @property
    def is_overdue(self):
        if self.next_action_deadline:
            return self.next_action_deadline < datetime.utcnow()
        return False
        
    def to_dict(self):
        owner = self.assigned_to
        return {
            "id": self.id,
            "contact_id": self.contact_id,
            "assigned_to_id": self.assigned_to_id,
            "assigned_to_name": owner.full_name if owner else None,
            "assigned_to_color": owner.calendar_color if owner else "#6366f1",
            "project_name": self.project.name if self.project else None,
            "pipeline_stage": self.pipeline_stage.value if self.pipeline_stage else None,
            "lead_temperature": self.lead_temperature.value if self.lead_temperature else None,
            "is_starred": self.is_starred,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_overdue": self.is_overdue
        }


class PipelineHistory(db.Model):
    __tablename__ = 'pipeline_history'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    from_stage = db.Column(db.Enum(PipelineStage))
    to_stage = db.Column(db.Enum(PipelineStage), nullable=False)
    changed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    changed_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)


class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    ip_address = db.Column(db.String(45))
    table_name = db.Column(db.String(100), nullable=False)
    record_id = db.Column(db.Integer, nullable=False)
    action = db.Column(db.String(10), nullable=False) # INSERT/UPDATE/DELETE
    field_name = db.Column(db.String(100))
    old_value = db.Column(db.Text)
    new_value = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index('idx_table_record', 'table_name', 'record_id'),
    )


class SLAEvent(db.Model):
    __tablename__ = 'sla_events'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, nullable=False)
    notified_at = db.Column(db.DateTime)
    reminded_at = db.Column(db.DateTime)
    manager_alerted_at = db.Column(db.DateTime)
    escalated_at = db.Column(db.DateTime)
    resolved_at = db.Column(db.DateTime)
    status = db.Column(db.Enum(SLAStatus), default=SLAStatus.PENDING)
    escalated_to_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class CallLog(db.Model):
    __tablename__ = 'call_logs'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    call_type = db.Column(db.String(20)) # OUTBOUND, INBOUND
    connected = db.Column(db.Boolean, default=False)
    duration_band = db.Column(db.Enum(DurationBand))
    outcome = db.Column(db.Enum(ActivityOutcome))
    notes = db.Column(db.Text)
    next_action_type = db.Column(db.Enum(ActivityType))
    next_action_deadline = db.Column(db.DateTime)
    recording_filename = db.Column(db.String(255))
    recording_url_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Appointment(db.Model):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    scheduled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    appointment_datetime = db.Column(db.DateTime, nullable=False)
    location = db.Column(db.String(255))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    confirmed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    debrief_submitted = db.Column(db.Boolean, default=False)
    debrief_notes = db.Column(db.Text)
    no_show_reason = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Objection(db.Model):
    __tablename__ = 'objections'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.Enum(ObjectionCategory), nullable=False)
    specific_objection = db.Column(db.String(255), nullable=False)
    competitor_name = db.Column(db.String(100))
    handling_notes = db.Column(db.Text)
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Reservation(db.Model):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    unit_reference = db.Column(db.String(100), nullable=False)
    booking_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='BDT')
    receipt_number = db.Column(db.String(100), unique=True, nullable=False)
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    approving_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Sale(db.Model):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), unique=True, nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), unique=True, nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    total_sale_value = db.Column(db.Numeric(15, 2), nullable=False)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    commercial_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Task(db.Model):
    __tablename__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    due_date = db.Column(db.DateTime, nullable=False)
    priority = db.Column(db.Enum(TaskPriority), default=TaskPriority.MEDIUM)
    status = db.Column(db.Enum(TaskStatus), default=TaskStatus.PENDING)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class TimeCard(db.Model):
    __tablename__ = 'time_cards'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    clock_out = db.Column(db.DateTime)
    notes = db.Column(db.Text)


class Leave(db.Model):
    __tablename__ = 'leaves'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.Enum(LeaveType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))


class Note(db.Model):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(100))
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_all_day = db.Column(db.Boolean, default=False)

    def to_dict(self):
        user = User.query.get(self.created_by_id)
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "start": self.start_datetime.isoformat(),
            "end": self.end_datetime.isoformat() if self.end_datetime else None,
            "created_by_id": self.created_by_id,
            "is_all_day": self.is_all_day,
            "color": user.calendar_color if user else "#6366f1"
        }


class RecordingDownloadLog(db.Model):
    __tablename__ = 'recording_download_logs'
    id = db.Column(db.Integer, primary_key=True)
    call_log_id = db.Column(db.Integer, db.ForeignKey('call_logs.id'), nullable=False)
    downloaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(45))


# ---------------------------------------------------------------------------
# Internal Messaging
# ---------------------------------------------------------------------------

class Message(db.Model):
    """Module 11: Internal team messaging."""
    __tablename__ = 'messages'
    id = db.Column(db.Integer, primary_key=True)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    subject = db.Column(db.String(255), default='')
    body = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    read_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')
    recipient = db.relationship('User', foreign_keys=[recipient_id], backref='received_messages')

    def to_dict(self):
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'recipient_id': self.recipient_id,
            'subject': self.subject,
            'body': self.body,
            'is_read': self.is_read,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Support Tickets
# ---------------------------------------------------------------------------

class TicketPriority(PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class TicketStatus(PyEnum):
    OPEN = "OPEN"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class Ticket(db.Model):
    """Module 13: Customer support ticket tracking."""
    __tablename__ = 'tickets'
    id = db.Column(db.Integer, primary_key=True)
    subject = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    priority = db.Column(db.Enum(TicketPriority), default=TicketPriority.MEDIUM)
    status = db.Column(db.Enum(TicketStatus), default=TicketStatus.OPEN)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    resolution_notes = db.Column(db.Text, nullable=True)
    resolved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_by = db.relationship('User', foreign_keys=[created_by_id])
    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])

    def to_dict(self):
        return {
            'id': self.id,
            'subject': self.subject,
            'description': self.description,
            'priority': self.priority.value if self.priority else None,
            'status': self.status.value if self.status else None,
            'created_by_id': self.created_by_id,
            'assigned_to_id': self.assigned_to_id,
            'contact_id': self.contact_id,
            'opportunity_id': self.opportunity_id,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Expenses
# ---------------------------------------------------------------------------

class ExpenseCategory(PyEnum):
    TRAVEL = "TRAVEL"
    MARKETING = "MARKETING"
    ENTERTAINMENT = "ENTERTAINMENT"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    COMMUNICATION = "COMMUNICATION"
    SITE_VISIT = "SITE_VISIT"
    OTHER = "OTHER"


class ExpenseStatus(PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Expense(db.Model):
    """Module 14: Financial outflow / expense tracking."""
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='BDT')
    category = db.Column(db.Enum(ExpenseCategory), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    expense_date = db.Column(db.Date, nullable=False)
    submitted_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    receipt_filename = db.Column(db.String(255), nullable=True)
    status = db.Column(db.Enum(ExpenseStatus), default=ExpenseStatus.PENDING)
    approval_notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    submitted_by = db.relationship('User', foreign_keys=[submitted_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'category': self.category.value if self.category else None,
            'description': self.description,
            'expense_date': self.expense_date.isoformat() if self.expense_date else None,
            'submitted_by_id': self.submitted_by_id,
            'opportunity_id': self.opportunity_id,
            'status': self.status.value if self.status else None,
            'approval_notes': self.approval_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# Finance Module (Sales Hub)
# ---------------------------------------------------------------------------

class InvoiceStatus(PyEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    CANCELLED = "CANCELLED"


class Invoice(db.Model):
    """Module 08: Sales Hub - Invoice tracking."""
    __tablename__ = 'invoices'
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    currency = db.Column(db.String(10), default='BDT')
    status = db.Column(db.Enum(InvoiceStatus), default=InvoiceStatus.DRAFT)
    issued_date = db.Column(db.Date, nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date, nullable=True)
    notes = db.Column(db.Text, nullable=True)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'contact_id': self.contact_id,
            'amount': float(self.amount) if self.amount else None,
            'currency': self.currency,
            'status': self.status.value if self.status else None,
            'issued_date': self.issued_date.isoformat() if self.issued_date else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'paid_date': self.paid_date.isoformat() if self.paid_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


# ---------------------------------------------------------------------------
# System Settings
# ---------------------------------------------------------------------------

class SystemSetting(db.Model):
    """System-wide configuration settings stored in DB."""
    __tablename__ = 'system_settings'
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

    @classmethod
    def get(cls, key, default=None):
        setting = cls.query.filter_by(key=key).first()
        return setting.value if setting and setting.value is not None else default

    @classmethod
    def set(cls, key, value, description=None):
        setting = cls.query.filter_by(key=key).first()
        if not setting:
            setting = cls(key=key, value=str(value) if value is not None else '', description=description)
            db.session.add(setting)
        else:
            setting.value = str(value) if value is not None else ''
            if description:
                setting.description = description
        db.session.commit()
        return setting


