import phonenumbers
import re

def normalize_phone(raw: str, default_region='BD') -> str:
    """Normalize phone number to E.164 format (supports BD and international)."""
    if not raw:
        return None
    raw_str = str(raw).strip()
    digits = ''.join(c for c in raw_str if c.isdigit())
    if not digits:
        return None

    # Handle Bangladesh mobile numbering formats
    # Bangladesh mobile numbers are 11 digits starting with 01[3-9]
    if len(digits) == 11 and digits.startswith('01'):
        raw_to_parse = '+88' + digits
    elif len(digits) == 13 and digits.startswith('8801'):
        raw_to_parse = '+' + digits
    elif len(digits) == 10 and digits.startswith('1'):
        # Missing leading 0 e.g. 17XXXXXXXX
        raw_to_parse = '+880' + digits
    elif raw_str.startswith('+'):
        raw_to_parse = raw_str
    else:
        raw_to_parse = '+' + digits if digits.startswith('880') else raw_str

    try:
        parsed = phonenumbers.parse(raw_to_parse, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass

    # Safe fallback for Bangladesh numbers
    if len(digits) == 11 and digits.startswith('01'):
        return f"+88{digits}"
    elif len(digits) == 13 and digits.startswith('8801'):
        return f"+{digits}"
    elif len(digits) == 10 and digits.startswith('1'):
        return f"+880{digits}"

    return None


def extract_core_phone_digits(phone: str) -> str:
    """Extract last 10 significant digits of a phone number for flexible matching."""
    if not phone:
        return ""
    digits = ''.join(c for c in str(phone) if c.isdigit())
    if len(digits) >= 10:
        return digits[-10:]
    return digits


def find_existing_contact(phone: str = None, email: str = None):
    """
    Finds a Contact by phone (normalized E.164, raw, or core 10 digits) or email.
    Guarantees matching regardless of formatting (+88, 880, 017..., spaces, dashes).
    """
    from app.models import Contact
    from sqlalchemy import or_

    contact = None
    if phone:
        phone_str = str(phone).strip()
        phone_norm = normalize_phone(phone_str)
        core_digits = extract_core_phone_digits(phone_str)

        filters = []
        if phone_norm:
            filters.append(Contact.phone_normalized == phone_norm)
            filters.append(Contact.phone_raw == phone_norm)
        if phone_str:
            filters.append(Contact.phone_raw == phone_str)
            filters.append(Contact.phone_normalized == phone_str)
        if core_digits and len(core_digits) >= 9:
            filters.append(Contact.phone_normalized.like(f"%{core_digits}"))
            filters.append(Contact.phone_raw.like(f"%{core_digits}"))

        if filters:
            contact = Contact.query.filter(or_(*filters)).first()

    if not contact and email:
        clean_email = str(email).strip().lower()
        if clean_email:
            contact = Contact.query.filter(Contact.email.ilike(clean_email)).first()

    return contact
