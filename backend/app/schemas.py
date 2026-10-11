from marshmallow import Schema, fields, validate, EXCLUDE

class LeadCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    phone = fields.Str(required=True, validate=validate.Length(min=5, max=50))
    email = fields.Email(load_default=None)
    source = fields.Str(load_default='Manual Entry')
    project_id = fields.Int(load_default=None)
    project_interest = fields.Str(load_default=None)
    notes = fields.Str(load_default=None)
    budget_min = fields.Decimal(load_default=None)
    budget_max = fields.Decimal(load_default=None)
