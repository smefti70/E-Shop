import json
import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives, send_mail
from django.urls import reverse
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator


def generate_sslcommerz_payment(order, request):
    success_url = request.build_absolute_uri(
        reverse('shop:payment_success', kwargs={'order_id': order.id})
    )
    fail_url = request.build_absolute_uri(
        reverse('shop:payment_fail', kwargs={'order_id': order.id})
    )
    cancel_url = request.build_absolute_uri(
        reverse('shop:payment_cancel', kwargs={'order_id': order.id})
    )

    post_data = {
        'store_id': settings.SSLCOMMERZ_STORE_ID,
        'store_passwd': settings.SSLCOMMERZ_STORE_PASSWORD,
        'total_amount': float(order.get_total_cost()),
        'currency': 'BDT',
        'tran_id': str(order.id),
        'success_url': success_url,
        'fail_url': fail_url,
        'cancel_url': cancel_url,
        'cus_name': f"{order.user.first_name} {order.user.last_name}".strip(),
        'cus_email': order.user.email,
        'cus_add1': order.address,
        'cus_city': order.city,
        'cus_postcode': order.postal_code,
        'cus_country': 'Bangladesh',
        'shipping_method': 'NO',
        'product_name': f'Order #{order.id}',
        'product_category': 'General',
        'product_profile': 'general',
    }

    response = requests.post(settings.SSLCOMMERZ_PAYMENT_URL, data=post_data)
    return json.loads(response.text)


def send_order_confirmation_email(order):
    subject = f"Order Confirmation - Order #{order.id}"
    message = render_to_string('shop/email/order_confirmation.html', {
        'order': order,
    })
    to = order.user.email
    email = EmailMultiAlternatives(subject, '', to=[to])
    email.attach_alternative(message, "text/html")
    email.send()


def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('shop:verify_email', kwargs={'uidb64': uid, 'token': token})
    )
    subject = 'Verify Your Email Address'
    message = f'Hi {user.get_full_name()},\n\nPlease verify your email by clicking the link below:\n{verify_url}\n\nThank you!'
    send_mail(subject, message, 'no-reply@yourdomain.com', [user.email])
