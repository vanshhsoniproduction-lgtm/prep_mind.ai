from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser

@login_required
def setup_profile(request):
    if request.method == 'POST':
        user = request.user
        
        # Handle file upload safely
        if 'resume' in request.FILES:
            user.resume = request.FILES['resume']
            
        # Get target role and level
        user.target_role = request.POST.get('target_role', '')
        user.experience_level = request.POST.get('experience_level', '')
        
        user.save()
        return redirect('core:dashboard')  # We will build this later
        
    return render(request, 'accounts/setup_profile.html')

from django.contrib.auth import authenticate, login
from django.contrib import messages

def guest_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if not username or not password:
            messages.error(request, "Username and password are required.")
            return redirect('core:index')
            
        user = CustomUser.objects.filter(username=username).first()
        
        if user:
            # Try to login
            authenticated_user = authenticate(request, username=username, password=password)
            if authenticated_user:
                login(request, authenticated_user, backend='django.contrib.auth.backends.ModelBackend')
                return redirect('core:dashboard')
            else:
                messages.error(request, "Invalid password for this guest name. Please try another.")
                return redirect('core:index')
        else:
            # Create new guest user
            user = CustomUser.objects.create_user(username=username, password=password)
            user.save()
            login(request, user, backend='django.contrib.auth.backends.ModelBackend')
            messages.success(request, f"Welcome {username}! Your guest account has been created.")
            return redirect('core:dashboard')
            
    return redirect('core:index')
