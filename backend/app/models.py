from datetime import datetime, timezone
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
    EXECUTIVE = "EXECUTIVE"
    LEAD_OWNER = "LEAD_OWNER"
    MANAGER = "MANAGER"
    GM = "GM"
    CEO = "CEO"
    ADMIN = "ADMIN"

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

class LeadPriority(PyEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"

class LeadTemperature(PyEnum):
    VERY_HOT = "VERY_HOT"
    HOT = "HOT"
    WARM = "WARM"
    COLD = "COLD"
    FROZEN = "FROZEN"

class AppointmentStatus(PyEnum):
    SCHEDULED = "SCHEDULED"
    CONFIRMATION_PENDING = "CONFIRMATION_PENDING"
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
    PRICE_TOO_HIGH = "PRICE_TOO_HIGH"
    LOCATION_DISTANCE = "LOCATION_DISTANCE"
    CONNECTIVITY_ROADS = "CONNECTIVITY_ROADS"
    DEVELOPMENT_TIMELINE = "DEVELOPMENT_TIMELINE"
    TITLE_LEGAL_CLARITY = "TITLE_LEGAL_CLARITY"
    COMPETITOR_PREFERENCE = "COMPETITOR_PREFERENCE"
    PAYMENT_TERMS_UNSUITABLE = "PAYMENT_TERMS_UNSUITABLE"
    SPOUSE_FAMILY_DISAPPROVAL = "SPOUSE_FAMILY_DISAPPROVAL"
    NOT_READY_FINANCIALLY = "NOT_READY_FINANCIALLY"
    NO_LONGER_INTERESTED = "NO_LONGER_INTERESTED"
    OTHER = "OTHER"
    # Legacy aliases
    PRICE = "PRICE_TOO_HIGH"
    DISTANCE = "LOCATION_DISTANCE"
    INFRASTRUCTURE = "CONNECTIVITY_ROADS"
    COMPETITOR = "COMPETITOR_PREFERENCE"
    TIMING = "DEVELOPMENT_TIMELINE"
    FINANCING = "PAYMENT_TERMS_UNSUITABLE"

class PaymentMethod(PyEnum):
    CASH = "CASH"
    CHEQUE = "CHEQUE"
    BANK_TRANSFER = "BANK_TRANSFER"
    MOBILE_BANKING = "MOBILE_BANKING"

class InstallmentStatus(PyEnum):
    PENDING = "PENDING"
    PAID = "PAID"
    OVERDUE = "OVERDUE"
    WAIVED = "WAIVED"

class CancellationStatus(PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"

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

class PlotStatus(PyEnum):
    AVAILABLE = "AVAILABLE"
    HOLD = "HOLD"
    RESERVED = "RESERVED"
    BOOKED = "BOOKED"
    SOLD = "SOLD"

class LeaveType(PyEnum):
    ANNUAL = "ANNUAL"
    SICK = "SICK"
    UNPAID = "UNPAID"

class LeaveStatus(PyEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SoftDeleteMixin:
    is_deleted = db.Column(db.Boolean, default=False, index=True)
    deleted_at = db.Column(db.DateTime)

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = datetime.now(timezone.utc)


class User(db.Model, SoftDeleteMixin):
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
    failed_login_attempts = db.Column(db.Integer, default=0)
    lockout_until = db.Column(db.DateTime, nullable=True)
    email_otp = db.Column(db.String(6), nullable=True)
    email_otp_expires_at = db.Column(db.DateTime, nullable=True)
    avatar_url = db.Column(db.String(255))
    calendar_color = db.Column(db.String(7), default="#6366f1")
    max_lead_capacity = db.Column(db.Integer, default=30)
    schedule_from_date = db.Column(db.Date, nullable=True)
    schedule_to_date = db.Column(db.Date, nullable=True)
    schedule_start_time = db.Column(db.Time, nullable=True)
    schedule_end_time = db.Column(db.Time, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)
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
            "avatar_url": self.avatar_url,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Contact(db.Model, SoftDeleteMixin):
    __tablename__ = 'contacts'
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(120))
    phone_raw = db.Column(db.String(50))
    phone_normalized = db.Column(db.String(20), unique=True)
    phone_hash = db.Column(db.String(64), index=True)
    gender = db.Column(db.String(10))
    job_title = db.Column(db.String(100))
    profession = db.Column(db.String(100))
    service_type = db.Column(db.String(100))
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    inquiries = db.relationship('Inquiry', backref='contact', lazy=True, cascade='all, delete-orphan')
    opportunities = db.relationship('Opportunity', backref='contact', lazy=True, cascade='all, delete-orphan')


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
    original_phone_raw = db.Column(db.String(50))
    budget_min = db.Column(db.Numeric(12, 2))
    budget_max = db.Column(db.Numeric(12, 2))
    submitted_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    phases = db.relationship('Phase', backref='project', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'description': self.description,
            'location': self.location,
            'total_units': self.total_units,
            'available_units': self.available_units,
            'price_per_sqft': float(self.price_per_sqft) if self.price_per_sqft else None,
            'status': self.status.value if self.status else 'ACTIVE',
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Phase(db.Model):
    __tablename__ = 'phases'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    blocks = db.relationship('Block', backref='phase', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Block(db.Model):
    __tablename__ = 'blocks'
    id = db.Column(db.Integer, primary_key=True)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    roads = db.relationship('Road', backref='block', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'phase_id': self.phase_id,
            'name': self.name,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Road(db.Model):
    __tablename__ = 'roads'
    id = db.Column(db.Integer, primary_key=True)
    block_id = db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=False)
    road_number = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    plots = db.relationship('Plot', backref='road', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'block_id': self.block_id,
            'road_number': self.road_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Plot(db.Model, SoftDeleteMixin):
    __tablename__ = 'plots'
    id = db.Column(db.Integer, primary_key=True)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    phase_id = db.Column(db.Integer, db.ForeignKey('phases.id'), nullable=True)
    block_id = db.Column(db.Integer, db.ForeignKey('blocks.id'), nullable=True)
    road_id = db.Column(db.Integer, db.ForeignKey('roads.id'), nullable=True)
    plot_number = db.Column(db.String(50), nullable=False)
    size_katha = db.Column(db.Numeric(6, 2), nullable=False) # Plot size in Katha
    facing = db.Column(db.String(50)) # North, South, East, West, Corner, etc.
    rate_per_katha = db.Column(db.Numeric(12, 2))
    total_price = db.Column(db.Numeric(15, 2))
    status = db.Column(db.Enum(PlotStatus), default=PlotStatus.AVAILABLE, nullable=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    project_rel = db.relationship('Project', foreign_keys=[project_id])

    def to_dict(self):
        return {
            'id': self.id,
            'project_id': self.project_id,
            'phase_id': self.phase_id,
            'block_id': self.block_id,
            'road_id': self.road_id,
            'plot_number': self.plot_number,
            'size_katha': float(self.size_katha) if self.size_katha else None,
            'facing': self.facing,
            'rate_per_katha': float(self.rate_per_katha) if self.rate_per_katha else None,
            'total_price': float(self.total_price) if self.total_price else None,
            'status': self.status.value if self.status else 'AVAILABLE',
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Opportunity(db.Model, SoftDeleteMixin):
    __tablename__ = 'opportunities'
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiries.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False, index=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    assigned_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    pipeline_stage = db.Column(db.Enum(PipelineStage), default=PipelineStage.NEW, index=True)
    last_activity_type = db.Column(db.Enum(ActivityType))
    last_activity_outcome = db.Column(db.Enum(ActivityOutcome))
    last_activity_at = db.Column(db.DateTime)
    next_action_type = db.Column(db.Enum(ActivityType))
    next_action_owner_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    next_action_deadline = db.Column(db.DateTime)
    appointment_status = db.Column(db.Enum(AppointmentStatus))
    lead_temperature = db.Column(db.Enum(LeadTemperature), default=LeadTemperature.COLD)
    priority = db.Column(db.Enum(LeadPriority), default=LeadPriority.MEDIUM)
    is_starred = db.Column(db.Boolean, default=False)
    manager_assessment = db.Column(db.Text)
    manager_label = db.Column(db.String(100))
    final_result = db.Column(db.Enum(FinalResult))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    total_deal_value = db.Column(db.Numeric(15, 2))
    service_type = db.Column(db.String(100))
    activity_label = db.Column(db.String(100))
    questionnaire_answers = db.Column(db.JSON, default=dict)

    # Stage milestone date tracking
    assigned_date = db.Column(db.DateTime)
    first_contact_date = db.Column(db.DateTime)
    last_contact_date = db.Column(db.DateTime)
    engaged_date = db.Column(db.DateTime)
    visit_date = db.Column(db.DateTime)
    negotiation_date = db.Column(db.DateTime)
    booking_date = db.Column(db.DateTime)
    sold_date = db.Column(db.DateTime)
    closed_lost_date = db.Column(db.DateTime)

    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    assigned_to = db.relationship('User', foreign_keys=[assigned_to_id])
    project = db.relationship('Project')
    call_logs = db.relationship('CallLog', backref='opportunity', lazy=True, cascade='all, delete-orphan')
    appointments = db.relationship('Appointment', backref='opportunity', lazy=True, cascade='all, delete-orphan')
    notes = db.relationship('Note', backref='opportunity', lazy=True, cascade='all, delete-orphan')
    reservations = db.relationship('Reservation', backref='opportunity', lazy=True, cascade='all, delete-orphan')

    @property
    def is_overdue(self):
        if self.next_action_deadline:
            deadline = self.next_action_deadline
            if deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            return deadline < datetime.now(timezone.utc)
        return False
        
    @property
    def lead_age_days(self):
        if self.created_at:
            created = self.created_at
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - created).days
        return 0

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
            "priority": self.priority.value if self.priority else "MEDIUM",
            "next_action_type": self.next_action_type.value if self.next_action_type else None,
            "next_action_deadline": self.next_action_deadline.isoformat() if self.next_action_deadline else None,
            "lead_age_days": self.lead_age_days,
            "is_starred": self.is_starred,
            "service_type": self.service_type,
            "activity_label": self.activity_label,
            "questionnaire_answers": self.questionnaire_answers or {},
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
    changed_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    activity_label = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        db.Index('idx_table_record', 'table_name', 'record_id'),
    )

    user = db.relationship('User', backref=db.backref('audit_logs_rel', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.full_name if self.user else 'System',
            'ip_address': self.ip_address,
            'table_name': self.table_name,
            'record_id': self.record_id,
            'action': self.action,
            'field_name': self.field_name,
            'old_value': self.old_value,
            'new_value': self.new_value,
            'activity_label': self.activity_label,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class CallLog(db.Model, SoftDeleteMixin):
    __tablename__ = 'call_logs'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False, index=True)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    call_type = db.Column(db.String(20)) # OUTBOUND, INBOUND
    connected = db.Column(db.Boolean, default=False)
    duration_band = db.Column(db.Enum(DurationBand))
    outcome = db.Column(db.Enum(ActivityOutcome))
    notes = db.Column(db.Text)
    next_action_type = db.Column(db.Enum(ActivityType))
    next_action_deadline = db.Column(db.DateTime)
    recording_filename = db.Column(db.String(255))
    recording_url_expires = db.Column(db.DateTime)
    activity_label = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Appointment(db.Model, SoftDeleteMixin):
    __tablename__ = 'appointments'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False, index=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    scheduled_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    appointment_datetime = db.Column(db.DateTime, nullable=False, index=True)
    location = db.Column(db.String(255))
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    status = db.Column(db.Enum(AppointmentStatus), default=AppointmentStatus.SCHEDULED)
    confirmed_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    debrief_submitted = db.Column(db.Boolean, default=False)
    debrief_notes = db.Column(db.Text)
    no_show_reason = db.Column(db.Text)
    rescheduled_from_id = db.Column(db.Integer, db.ForeignKey('appointments.id'), nullable=True)
    reminder_24h_sent = db.Column(db.Boolean, default=False)
    reminder_2h_sent = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'opportunity_id': self.opportunity_id,
            'contact_id': self.contact_id,
            'scheduled_by_id': self.scheduled_by_id,
            'appointment_datetime': self.appointment_datetime.isoformat() if self.appointment_datetime else None,
            'location': self.location,
            'project_id': self.project_id,
            'status': self.status.value if self.status else 'SCHEDULED',
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'debrief_submitted': self.debrief_submitted,
            'debrief_notes': self.debrief_notes,
            'no_show_reason': self.no_show_reason,
            'rescheduled_from_id': self.rescheduled_from_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Objection(db.Model):
    __tablename__ = 'objections'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    logged_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.Column(db.Enum(ObjectionCategory), nullable=False)
    specific_objection = db.Column(db.String(255), nullable=False)
    competitor_name = db.Column(db.String(100))
    intensity = db.Column(db.Integer, default=3) # 1 (mild) to 5 (dealbreaker)
    is_principal = db.Column(db.Boolean, default=True) # Primary objection blocker
    reactivation_eligible = db.Column(db.Boolean, default=False)
    handling_notes = db.Column(db.Text)
    executive_response = db.Column(db.Text)
    resolved = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Reservation(db.Model, SoftDeleteMixin):
    __tablename__ = 'reservations'
    id = db.Column(db.Integer, primary_key=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    plot_id = db.Column(db.Integer, db.ForeignKey('plots.id'), nullable=True)
    unit_reference = db.Column(db.String(100), nullable=False)
    booking_amount = db.Column(db.Numeric(12, 2), nullable=False)
    currency = db.Column(db.String(10), default='BDT')
    receipt_number = db.Column(db.String(100), unique=True, nullable=False)
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    approving_officer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_at = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    installments = db.relationship('Installment', backref='reservation', lazy=True, cascade='all, delete-orphan')
    cancellation_requests = db.relationship('CancellationRequest', backref='reservation', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'opportunity_id': self.opportunity_id,
            'contact_id': self.contact_id,
            'project_id': self.project_id,
            'plot_id': self.plot_id,
            'unit_reference': self.unit_reference,
            'booking_amount': float(self.booking_amount) if self.booking_amount else 0.0,
            'currency': self.currency,
            'receipt_number': self.receipt_number,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'approving_officer_id': self.approving_officer_id,
            'approved_at': self.approved_at.isoformat() if self.approved_at else None,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Installment(db.Model, SoftDeleteMixin):
    __tablename__ = 'installments'
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False, index=True)
    installment_number = db.Column(db.Integer, nullable=False)
    title = db.Column(db.String(100), nullable=False) # e.g., '1st Installment', 'Booking Downpayment'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(InstallmentStatus), default=InstallmentStatus.PENDING, nullable=False)
    paid_amount = db.Column(db.Numeric(12, 2), default=0.0)
    paid_at = db.Column(db.DateTime)
    payment_method = db.Column(db.Enum(PaymentMethod))
    receipt_number = db.Column(db.String(100))
    recorded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    recorded_by = db.relationship('User', foreign_keys=[recorded_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'reservation_id': self.reservation_id,
            'opportunity_id': self.opportunity_id,
            'installment_number': self.installment_number,
            'title': self.title,
            'amount': float(self.amount) if self.amount else 0.0,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'status': self.status.value if self.status else 'PENDING',
            'paid_amount': float(self.paid_amount) if self.paid_amount else 0.0,
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'payment_method': self.payment_method.value if self.payment_method else None,
            'receipt_number': self.receipt_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CancellationRequest(db.Model, SoftDeleteMixin):
    __tablename__ = 'cancellation_requests'
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), nullable=False, index=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=False, index=True)
    reason = db.Column(db.Text, nullable=False)
    refund_amount_requested = db.Column(db.Numeric(12, 2))
    refund_amount_approved = db.Column(db.Numeric(12, 2))
    status = db.Column(db.Enum(CancellationStatus), default=CancellationStatus.PENDING, nullable=False)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reviewed_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    reviewed_at = db.Column(db.DateTime)
    review_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    requested_by = db.relationship('User', foreign_keys=[requested_by_id])
    reviewed_by = db.relationship('User', foreign_keys=[reviewed_by_id])

    def to_dict(self):
        return {
            'id': self.id,
            'reservation_id': self.reservation_id,
            'opportunity_id': self.opportunity_id,
            'reason': self.reason,
            'refund_amount_requested': float(self.refund_amount_requested) if self.refund_amount_requested else None,
            'refund_amount_approved': float(self.refund_amount_approved) if self.refund_amount_approved else None,
            'status': self.status.value if self.status else 'PENDING',
            'requested_by_id': self.requested_by_id,
            'reviewed_by_id': self.reviewed_by_id,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'review_notes': self.review_notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Sale(db.Model, SoftDeleteMixin):
    __tablename__ = 'sales'
    id = db.Column(db.Integer, primary_key=True)
    reservation_id = db.Column(db.Integer, db.ForeignKey('reservations.id'), unique=True, nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), unique=True, nullable=False, index=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    total_sale_value = db.Column(db.Numeric(15, 2), nullable=False)
    verified_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    verified_at = db.Column(db.DateTime)
    commercial_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)


class Team(db.Model):
    __tablename__ = 'teams'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class TimeCard(db.Model):
    __tablename__ = 'time_cards'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    clock_in = db.Column(db.DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    clock_out = db.Column(db.DateTime)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Leave(db.Model):
    __tablename__ = 'leaves'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    leave_type = db.Column(db.Enum(LeaveType), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.Enum(LeaveStatus), default=LeaveStatus.PENDING)
    approved_by_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class Note(db.Model, SoftDeleteMixin):
    __tablename__ = 'notes'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'content': self.content,
            'is_private': self.is_private,
            'created_by_id': self.created_by_id,
            'created_by_name': self.created_by.full_name if self.created_by else None,
            'opportunity_id': self.opportunity_id,
            'contact_id': self.contact_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    event_type = db.Column(db.String(100))
    start_datetime = db.Column(db.DateTime, nullable=False)
    end_datetime = db.Column(db.DateTime, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.relationship('User', foreign_keys=[created_by_id])
    is_all_day = db.Column(db.Boolean, default=False)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "event_type": self.event_type,
            "start": self.start_datetime.isoformat(),
            "end": self.end_datetime.isoformat() if self.end_datetime else None,
            "created_by_id": self.created_by_id,
            "is_all_day": self.is_all_day,
            "color": self.created_by.calendar_color if self.created_by else "#6366f1"
        }


class RecordingDownloadLog(db.Model):
    __tablename__ = 'recording_download_logs'
    id = db.Column(db.Integer, primary_key=True)
    call_log_id = db.Column(db.Integer, db.ForeignKey('call_logs.id'), nullable=False)
    downloaded_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    downloaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

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
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

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
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

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


class TokenBlocklist(db.Model):
    __tablename__ = 'token_blocklist'
    id = db.Column(db.Integer, primary_key=True)
    jti = db.Column(db.String(36), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    @classmethod
    def is_jti_blacklisted(cls, jti):
        return cls.query.filter_by(jti=jti).first() is not None


# ---------------------------------------------------------------------------
# Prospects (Pre-sale Documentation)
# ---------------------------------------------------------------------------
class ProposalStatus(PyEnum):
    DRAFT = "DRAFT"
    SENT = "SENT"
    VIEWED = "VIEWED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"

class Proposal(db.Model):
    __tablename__ = 'proposals'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'))
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text)
    total_value = db.Column(db.Numeric(15, 2))
    status = db.Column(db.Enum(ProposalStatus), default=ProposalStatus.DRAFT)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'contact_id': self.contact_id,
            'opportunity_id': self.opportunity_id,
            'total_value': float(self.total_value) if self.total_value else 0.0,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Estimate(db.Model):
    __tablename__ = 'estimates'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    project_id = db.Column(db.Integer, db.ForeignKey('projects.id'))
    estimated_amount = db.Column(db.Numeric(15, 2))
    details = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'project_id': self.project_id,
            'estimated_amount': float(self.estimated_amount) if self.estimated_amount else 0.0,
            'details': self.details,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ---------------------------------------------------------------------------
# Help & Support (Knowledge Base)
# ---------------------------------------------------------------------------
class ArticleCategory(PyEnum):
    FAQ = "FAQ"
    GUIDE = "GUIDE"
    POLICY = "POLICY"
    TROUBLESHOOTING = "TROUBLESHOOTING"

class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.Enum(ArticleCategory), default=ArticleCategory.FAQ)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'category': self.category.value,
            'is_published': self.is_published,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# ---------------------------------------------------------------------------
# Sales Hub Extensions (Orders, Items, Contracts)
# ---------------------------------------------------------------------------
class ProductItem(db.Model):
    __tablename__ = 'product_items'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(12, 2), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': float(self.price),
            'is_active': self.is_active
        }

class OrderStatus(PyEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    total_amount = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'total_amount': float(self.total_amount),
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Contract(db.Model):
    __tablename__ = 'contracts'
    id = db.Column(db.Integer, primary_key=True)
    contact_id = db.Column(db.Integer, db.ForeignKey('contacts.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text)
    signed = db.Column(db.Boolean, default=False)
    signed_at = db.Column(db.DateTime)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'contact_id': self.contact_id,
            'title': self.title,
            'signed': self.signed,
            'signed_at': self.signed_at.isoformat() if self.signed_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CoachingLog(db.Model):
    __tablename__ = 'coaching_logs'
    id = db.Column(db.Integer, primary_key=True)
    manager_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    executive_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    call_log_id = db.Column(db.Integer, db.ForeignKey('call_logs.id'), nullable=True)
    opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id'), nullable=True)
    score = db.Column(db.Integer, nullable=True) # 1-10 rating
    strengths = db.Column(db.Text)
    areas_for_improvement = db.Column(db.Text)
    action_items = db.Column(db.Text)
    session_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    manager = db.relationship('User', foreign_keys=[manager_id])
    executive = db.relationship('User', foreign_keys=[executive_id])
    call_log = db.relationship('CallLog')
    opportunity = db.relationship('Opportunity')

    def to_dict(self):
        return {
            'id': self.id,
            'manager_id': self.manager_id,
            'manager_name': self.manager.full_name if self.manager else None,
            'executive_id': self.executive_id,
            'executive_name': self.executive.full_name if self.executive else None,
            'call_log_id': self.call_log_id,
            'opportunity_id': self.opportunity_id,
            'score': self.score,
            'strengths': self.strengths,
            'areas_for_improvement': self.areas_for_improvement,
            'action_items': self.action_items,
            'session_date': self.session_date.isoformat() if self.session_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class WebhookRetry(db.Model):
    __tablename__ = 'webhook_retries'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), default='meta')
    payload = db.Column(db.JSON, nullable=False)
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)
    max_retries = db.Column(db.Integer, default=5)
    next_retry_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    status = db.Column(db.String(20), default='PENDING') # PENDING, RETRYING, SUCCESS, FAILED
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'provider': self.provider,
            'retry_count': self.retry_count,
            'status': self.status,
            'error_message': self.error_message,
            'next_retry_at': self.next_retry_at.isoformat() if self.next_retry_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# ---------------------------------------------------------------------------
# Activity Labels & Custom Questionnaire
# ---------------------------------------------------------------------------

class ActivityLabel(db.Model):
    """Configurable labels for activity and call logs."""
    __tablename__ = 'activity_labels'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    color = db.Column(db.String(30), default='#6366f1')
    description = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color or '#6366f1',
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def seed_defaults(cls):
        defaults = [
            ("Follow-up", "#6366f1", "Standard client follow-up conversation"),
            ("Site Visit Discussion", "#10b981", "Discussing or confirming a project site visit"),
            ("Price Negotiation", "#f59e0b", "Active price and installment negotiations"),
            ("VIP Client", "#8b5cf6", "High net worth or strategic prospective buyer"),
            ("Documentation / Booking", "#0ea5e9", "Processing paperwork, token, or plot reservation"),
            ("Ready Buyer", "#f43f5e", "High urgency buyer ready to close immediately"),
            ("Cold / Re-engage", "#64748b", "Re-connecting with long term or inactive inquiries")
        ]
        created = False
        for name, color, desc in defaults:
            if not cls.query.filter_by(name=name).first():
                db.session.add(cls(name=name, color=color, description=desc))
                created = True
        if created:
            db.session.commit()


class LeadQuestionnaireQuestion(db.Model):
    """Questions dynamically answered on leads (Meta Lead Ads & manual entry)."""
    __tablename__ = 'lead_questionnaire_questions'
    id = db.Column(db.Integer, primary_key=True)
    question_key = db.Column(db.String(100), unique=True, nullable=False)
    question_text = db.Column(db.String(255), nullable=False)
    field_type = db.Column(db.String(50), default='text')
    options = db.Column(db.JSON, nullable=True)
    order_index = db.Column(db.Integer, default=0)
    is_required = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'question_key': self.question_key,
            'question_text': self.question_text,
            'field_type': self.field_type or 'text',
            'options': self.options or [],
            'order_index': self.order_index,
            'is_required': self.is_required,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def seed_defaults(cls):
        default_questions = [
            {
                "question_key": "profession",
                "question_text": "Profession / Occupation",
                "field_type": "select",
                "options": ["Govt Service", "Private Service", "Business Owner", "Doctor", "Engineer", "Defense Officer", "Expatriate / NRI", "Lawyer", "Retired", "Other"],
                "order_index": 1,
                "is_required": True
            },
            {
                "question_key": "service_type",
                "question_text": "Service / Property Type",
                "field_type": "select",
                "options": ["Residential Plot", "Commercial Plot", "Villa / Duplex Plot", "Commercial Space", "Long-term Land Investment"],
                "order_index": 2,
                "is_required": True
            },
            {
                "question_key": "plot_size",
                "question_text": "Preferred Plot Size",
                "field_type": "select",
                "options": ["3 Katha", "5 Katha", "7.5 Katha", "10 Katha", "20 Katha (1 Bigha)"],
                "order_index": 3,
                "is_required": False
            },
            {
                "question_key": "facing_preference",
                "question_text": "Facing Preference",
                "field_type": "select",
                "options": ["South Facing", "North Facing", "East Facing", "West Facing", "Corner Plot", "Lakeside / Park Facing"],
                "order_index": 4,
                "is_required": False
            },
            {
                "question_key": "project_interest",
                "question_text": "Preferred Project",
                "field_type": "select",
                "options": ["Green Valley City", "Lake View City", "Highway Heights", "South City Extension", "Any Suitable Project"],
                "order_index": 5,
                "is_required": False
            },
            {
                "question_key": "budget_range",
                "question_text": "Budget Range",
                "field_type": "select",
                "options": ["20 - 40 Lakhs", "40 - 70 Lakhs", "70 Lakhs - 1.2 Crore", "1.2 - 2 Crore", "2 Crore+"],
                "order_index": 6,
                "is_required": False
            },
            {
                "question_key": "purchase_timeline",
                "question_text": "Purchasing Timeline",
                "field_type": "select",
                "options": ["Immediate / Ready to Buy", "Within 1 - 3 Months", "Within 3 - 6 Months", "Exploring Options"],
                "order_index": 7,
                "is_required": False
            },
            {
                "question_key": "payment_preference",
                "question_text": "Payment Plan Preference",
                "field_type": "select",
                "options": ["Full One-Time Payment", "12 Months Installment", "24-36 Months Installment", "Long-Term 60 Months"],
                "order_index": 8,
                "is_required": False
            },
            {
                "question_key": "decision_maker",
                "question_text": "Primary Decision Maker",
                "field_type": "select",
                "options": ["Self", "Self & Spouse", "Joint Family", "Company / Business Partner"],
                "order_index": 9,
                "is_required": False
            },
            {
                "question_key": "living_status",
                "question_text": "Current Living Status",
                "field_type": "select",
                "options": ["Own House in Dhaka", "Rented Apartment in Dhaka", "Expatriate Living Abroad", "Living Outside Dhaka"],
                "order_index": 10,
                "is_required": False
            },
            {
                "question_key": "previous_visit",
                "question_text": "Have you visited our project sites before?",
                "field_type": "select",
                "options": ["Yes, visited already", "No, want to schedule a visit", "Planning this Friday", "Planning next week"],
                "order_index": 11,
                "is_required": False
            },
            {
                "question_key": "preferred_contact_time",
                "question_text": "Preferred Time for Call / Site Visit",
                "field_type": "select",
                "options": ["Morning (10 AM - 1 PM)", "Afternoon (2 PM - 5 PM)", "Evening (6 PM - 9 PM)", "Friday / Weekend Only"],
                "order_index": 12,
                "is_required": False
            }
        ]
        created = False
        for q in default_questions:
            existing = cls.query.filter_by(question_key=q["question_key"]).first()
            if not existing:
                db.session.add(cls(**q))
                created = True
        if created:
            db.session.commit()


