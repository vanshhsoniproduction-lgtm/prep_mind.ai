import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'PrepMind_AI.settings')
django.setup()

from django.contrib.auth import get_user_model
from allauth.socialaccount.models import SocialToken

User = get_user_model()
for u in User.objects.all():
    tokens = SocialToken.objects.filter(account__user=u)
    print(f"User: {u.username}, Tokens: {tokens}")
