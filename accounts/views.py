from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import CustomUser

@login_required
def setup_profile(request):
    if request.method == 'POST':
        user = request.user
        
        if getattr(user, 'is_hr', False):
            user.company_name = request.POST.get('company_name', user.company_name)
            user.phone_number = request.POST.get('phone_number', user.phone_number)
        else:
            # Handle file upload safely
            if 'resume' in request.FILES:
                user.resume = request.FILES['resume']
            # Get target role and level
            user.target_role = request.POST.get('target_role', '')
            user.experience_level = request.POST.get('experience_level', '')
            
        user.save()
        if getattr(user, 'is_hr', False):
            return redirect('core:hr_dashboard')
        return redirect('core:dashboard')
        
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

def hr_login(request):
    if request.method == 'POST':
        login_cred = request.POST.get('login_cred')
        password = request.POST.get('password')
        
        user = authenticate(request, username=login_cred, password=password)
        if user and getattr(user, 'is_hr', False):
            login(request, user)
            return redirect('core:hr_dashboard')
        else:
            messages.error(request, "Invalid credentials or not an HR user.")
            
    return redirect('core:landing_page')

def hr_register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        company_name = request.POST.get('company_name')
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return redirect('core:landing_page')
            
        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password,
            phone_number=phone_number,
            company_name=company_name,
            is_hr=True
        )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('core:hr_dashboard')
        
    return redirect('core:landing_page')


# ============= HR CREDIT & INTERVIEW REQUEST APIs =============
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import HRUnlockedCandidate, HRInterviewRequest
import json

@login_required
@csrf_exempt
def hr_unlock_candidate(request, candidate_id):
    """Spend 1 HR credit to unlock a candidate's full interview data."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    if not getattr(request.user, 'is_hr', False):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    # Check if already unlocked
    already = HRUnlockedCandidate.objects.filter(hr_user=request.user, candidate_id=candidate_id).exists()
    if already:
        return JsonResponse({'success': True, 'already_unlocked': True, 'credits': request.user.hr_credits})
    
    # Check credits
    if request.user.hr_credits < 1:
        return JsonResponse({'success': False, 'error': 'no_credits', 'credits': request.user.hr_credits})
    
    # Deduct and unlock
    request.user.hr_credits -= 1
    request.user.save()
    HRUnlockedCandidate.objects.create(hr_user=request.user, candidate_id=candidate_id)
    
    return JsonResponse({'success': True, 'already_unlocked': False, 'credits': request.user.hr_credits})

@login_required
def hr_check_unlock(request, candidate_id):
    """Check if a candidate is already unlocked by this HR."""
    if not getattr(request.user, 'is_hr', False):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    unlocked = HRUnlockedCandidate.objects.filter(hr_user=request.user, candidate_id=candidate_id).exists()
    return JsonResponse({'success': True, 'unlocked': unlocked, 'credits': request.user.hr_credits})

@login_required
@csrf_exempt
def hr_send_request(request):
    """HR sends an interview request to a candidate."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'}, status=400)
    
    if not getattr(request.user, 'is_hr', False):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        candidate_id = data.get('candidate_id')
        scheduled_date = data.get('scheduled_date')
        scheduled_time = data.get('scheduled_time')
        note = data.get('note', '')
        
        req = HRInterviewRequest.objects.create(
            hr_user=request.user,
            candidate_id=candidate_id,
            scheduled_date=scheduled_date or None,
            scheduled_time=scheduled_time or None,
            note=note,
        )
        return JsonResponse({'success': True, 'request_id': req.id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@login_required
def hr_sent_requests(request):
    """Get all interview requests sent by this HR, with optional read/unread filter."""
    if not getattr(request.user, 'is_hr', False):
        return JsonResponse({'success': False, 'error': 'Not authorized'}, status=403)
    
    qs = HRInterviewRequest.objects.filter(hr_user=request.user).order_by('-created_at')
    
    read_filter = request.GET.get('filter')  # 'read', 'unread', or None (all)
    if read_filter == 'read':
        qs = qs.filter(is_read_by_candidate=True)
    elif read_filter == 'unread':
        qs = qs.filter(is_read_by_candidate=False)
    
    data = [{
        'id': r.id,
        'candidate_name': r.candidate.get_full_name() or r.candidate.username,
        'candidate_role': r.candidate.target_role or 'N/A',
        'scheduled_date': r.scheduled_date.strftime('%b %d, %Y') if r.scheduled_date else 'N/A',
        'scheduled_time': r.scheduled_time.strftime('%I:%M %p') if r.scheduled_time else 'N/A',
        'note': r.note or '',
        'is_read': r.is_read_by_candidate,
        'status': r.status,
        'created_at': r.created_at.strftime('%b %d, %Y %I:%M %p'),
    } for r in qs]
    
    return JsonResponse({'success': True, 'requests': data})

@login_required
def candidate_hr_requests(request):
    """Get all interview requests for the current candidate, with optional filter."""
    qs = HRInterviewRequest.objects.filter(candidate=request.user).order_by('-created_at')
    
    read_filter = request.GET.get('filter')
    if read_filter == 'read':
        qs = qs.filter(is_read_by_candidate=True)
    elif read_filter == 'unread':
        qs = qs.filter(is_read_by_candidate=False)
    
    data = [{
        'id': r.id,
        'hr_name': r.hr_user.get_full_name() or r.hr_user.username,
        'hr_email': r.hr_user.email or 'N/A',
        'hr_phone': r.hr_user.phone_number or 'N/A',
        'hr_company': r.hr_user.company_name or 'N/A',
        'scheduled_date': r.scheduled_date.strftime('%b %d, %Y') if r.scheduled_date else 'N/A',
        'scheduled_time': r.scheduled_time.strftime('%I:%M %p') if r.scheduled_time else 'N/A',
        'note': r.note or '',
        'is_read': r.is_read_by_candidate,
        'status': r.status,
        'created_at': r.created_at.strftime('%b %d, %Y %I:%M %p'),
    } for r in qs]
    
    unread_count = HRInterviewRequest.objects.filter(candidate=request.user, is_read_by_candidate=False).count()
    
    return JsonResponse({'success': True, 'requests': data, 'unread_count': unread_count})

@login_required
@csrf_exempt
def candidate_mark_read(request, request_id):
    """Candidate marks an HR request as read."""
    if request.method != 'POST':
        return JsonResponse({'success': False}, status=400)
    
    try:
        req = HRInterviewRequest.objects.get(id=request_id, candidate=request.user)
        req.is_read_by_candidate = True
        req.save()
        return JsonResponse({'success': True})
    except HRInterviewRequest.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)

