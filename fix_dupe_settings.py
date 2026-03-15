# Replace settings file directly just like we read it
import os

filepath = "PrepMind_AI/settings.py"
print(f"Reading {filepath}")
with open(filepath, "r") as f:
    lines = f.readlines()

new_lines = []
skip = False
for line in lines:
    if line.startswith("# Provider specific settings"):
        # We start skipping here
        skip = True
        break
    new_lines.append(line)

new_content = "".join(new_lines)

# Append the final fixed provider
new_content += """# Provider specific settings
SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'APP': {
            'client_id': GOOGLE_CLIENT_ID,
            'secret': GOOGLE_CLIENT_SECRET,
            'key': ''
        },
        'SCOPE': [
            'profile',
            'email',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/calendar.events',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file'
        ],
        'AUTH_PARAMS': {
            'access_type': 'offline',
            'prompt': 'consent',
        },
        'OAUTH_PKCE_ENABLED': True,
    }
}
SITE_ID = 1
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Added for Calendar/Docs API integration
SOCIALACCOUNT_STORE_TOKENS = True
"""

with open(filepath, "w") as f:
    f.write(new_content)
    
print("Cleaned up duplicated SOCIALACCOUNT_PROVIDERS.")
