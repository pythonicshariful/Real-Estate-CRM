import re

def validate_password(password: str) -> tuple[bool, str]:
    """
    Validates that a password meets complexity requirements:
    - At least 8 characters long
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one number
    - Contains at least one special character
    """
    if not password or len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return False, "Password must contain at least one number"
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character"
    
    # Check against a simple deny-list
    deny_list = ["password", "password123", "admin123", "qwertyuiop", "12345678"]
    if password.lower() in deny_list:
        return False, "This password is too common"
        
    return True, ""

def sanitize_input(text: str) -> str:
    """
    Basic sanitization to remove HTML tags and trim whitespace.
    """
    if text is None:
        return ""
    
    text = str(text)
    # Remove all HTML tags
    clean = re.sub(r'<[^>]*>', '', text)
    # Trim whitespace
    return clean.strip()
