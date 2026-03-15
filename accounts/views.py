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
