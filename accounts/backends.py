from django.contrib.auth.backends import ModelBackend
from .models import CustomUser

class EmailOrPhoneOrUsernameBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username:
            return None
        try:
            # Try to fetch the user by username, email, or phone number
            user = CustomUser.objects.filter(
                username=username
            ).first() or CustomUser.objects.filter(
                email=username
            ).first() or CustomUser.objects.filter(
                phone_number=username
            ).first()
            
            if user and user.check_password(password):
                return user
        except CustomUser.DoesNotExist:
            return None
        return None
