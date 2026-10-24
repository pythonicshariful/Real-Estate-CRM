from marshmallow import Schema, fields, validate, EXCLUDE, pre_load

class LeadCreateSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    @pre_load
    def blank_strings_to_none(self, data, **kwargs):
        """
        HTML forms submit "" for every optional input the user left untouched
        (email, profession, service_type, ...). fields.Email() rejects "" as
        invalid, so creating a lead without an email address used to fail with
        HTTP 400 "Not a valid email address". Treat blank optional values as
        missing instead.
        """
        if isinstance(data, dict):
            required = {'full_name', 'phone'}
            for key, value in list(data.items()):
                if key in required:
                    continue
                if isinstance(value, str) and value.strip() == '':
                    data[key] = None
        return data

    full_name = fields.Str(required=True, validate=validate.Length(min=1, max=150))
    phone = fields.Str(required=True, validate=validate.Length(min=5, max=50))
    email = fields.Email(load_default=None)
    source = fields.Str(load_default='Manual Entry')
    project_id = fields.Int(load_default=None)
    project_interest = fields.Str(load_default=None)
    notes = fields.Str(load_default=None)
    budget_min = fields.Decimal(load_default=None)
    budget_max = fields.Decimal(load_default=None)
    profession = fields.Str(load_default=None)
    service_type = fields.Str(load_default=None)
    activity_label = fields.Str(load_default=None)
    questionnaire_answers = fields.Dict(load_default=None)
    force_create = fields.Bool(load_default=False)
