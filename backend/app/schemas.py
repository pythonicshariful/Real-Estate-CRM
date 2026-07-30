from marshmallow import Schema, fields, validate

class LeadCreateSchema(Schema):
    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    phone = fields.Str(required=True, validate=validate.Length(min=5, max=50))
    email = fields.Email(load_default=None)
    source = fields.Str(load_default='Manual Entry')
    project_id = fields.Int(load_default=None)
