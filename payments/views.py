import json
import razorpay
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Payment
from django.contrib import messages

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

@login_required
def pricing_page(request):
    context = {
        'razorpay_key_id': settings.RAZORPAY_KEY_ID,
        'interview_price': settings.INTERVIEW_PRICE_INR,
        'user_credits': request.user.interview_credits,
    }
    return render(request, 'payments/pricing.html', context)

@login_required
@csrf_exempt
def create_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            pack_type = data.get('pack', 'single')
        except:
            pack_type = 'single'

        if pack_type == 'bundle':
            amount_in_inr = 259
            credits_to_add = 10
        else:
            amount_in_inr = settings.INTERVIEW_PRICE_INR
            credits_to_add = 1
            
        amount_in_paise = int(amount_in_inr * 100)
        currency = 'INR'
        
        # Create Razorpay Order
        razorpay_order = client.order.create({
            'amount': amount_in_paise,
            'currency': currency,
            'payment_capture': '1'
        })
        
        # Save order to DB
        Payment.objects.create(
            user=request.user,
            razorpay_order_id=razorpay_order['id'],
            amount=amount_in_inr,
            credits_count=credits_to_add,
            status='PENDING'
        )
        
        return JsonResponse(razorpay_order)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@csrf_exempt
def verify_payment(request):
    if request.method == 'POST':
        data = request.POST
        
        params_dict = {
            'razorpay_order_id': data.get('razorpay_order_id'),
            'razorpay_payment_id': data.get('razorpay_payment_id'),
            'razorpay_signature': data.get('razorpay_signature')
        }
        
        try:
            client.utility.verify_payment_signature(params_dict)
            
            payment = Payment.objects.get(razorpay_order_id=data.get('razorpay_order_id'))
            payment.razorpay_payment_id = data.get('razorpay_payment_id')
            payment.razorpay_signature = data.get('razorpay_signature')
            payment.status = 'COMPLETED'
            payment.save()
            
            user = request.user
            user.interview_credits += payment.credits_count
            user.save()
            
            messages.success(request, f"Payment successful! {payment.credits_count} Interview credits added.")
            return JsonResponse({'status': 'success'})
        except Exception as e:
            payment = Payment.objects.filter(razorpay_order_id=data.get('razorpay_order_id')).first()
            if payment:
                payment.status = 'FAILED'
                payment.save()
            return JsonResponse({'status': 'failed', 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid request'}, status=400)
