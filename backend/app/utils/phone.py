import phonenumbers

def normalize_phone(raw: str, default_region='BD') -> str:
    """Normalize phone number to E.164 format."""
    try:
        # Handle cases where leading 0 is present for BD but country code might be missing
        if raw.startswith('01') and len(raw) == 11 and default_region == 'BD':
            raw = '+88' + raw
            
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return None
