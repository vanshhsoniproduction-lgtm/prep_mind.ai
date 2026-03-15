import re

with open("PrepMind_AI/settings.py", "r") as f:
    settings = f.read()

pattern = """        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }"""

replacement = """        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar.events',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file'
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
            'prompt': 'consent',
        }"""

if pattern in settings:
    settings = settings.replace(pattern, replacement)
    
    if "SOCIALACCOUNT_STORE_TOKENS" not in settings:
        settings += "\n\n# Added for Calendar/Docs API integration\nSOCIALACCOUNT_STORE_TOKENS = True\n"
        
    with open("PrepMind_AI/settings.py", "w") as f:
        f.write(settings)
    print("Settings updated successfully.")
else:
    print("Pattern not found in settings!")
