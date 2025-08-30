from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout, get_user_model
from django.contrib import messages
from django.utils.http import urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Min, Max, Avg, Q

from .models import Category, Product, Rating, Cart, CartItem, Order, OrderItem
from .forms import UserRegistrationForm, RatingForm, CheckoutForm, ProfileUpdateForm
from .utils import generate_sslcommerz_payment, send_order_confirmation_email
from .utils import send_verification_email

User = get_user_model()

def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, email=email, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful')
            return redirect('shop:home')
        else:
            messages.error(request, 'Invalid credentials')
            return render(request, 'shop/login.html')
    return render(request, 'shop/login.html')


def register_view(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.is_verified = False  # Ensure user is unverified initially
            user.save()

            send_verification_email(request, user)

            messages.success(request, 'Registration successful. Please check your email to verify your account.')
            return redirect('shop:email_verification_sent')
        else:
            messages.error(request, 'Registration failed. Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    return render(request, 'shop/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out.')
    return redirect('shop:login')


def home(request):
    featured_products = Product.objects.filter(available=True).order_by('-created')[:6]
    categories = Category.objects.all()
    context = {
        'featured_products': featured_products,
        'categories': categories,
    }
    return render(request, 'shop/home.html', context)


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    min_price = products.aggregate(Min('new_price'))['new_price__min']
    max_price = products.aggregate(Max('new_price'))['new_price__max']

    if request.GET.get('min_price'):
        products = products.filter(new_price__gte=request.GET.get('min_price'))

    if request.GET.get('max_price'):
        products = products.filter(new_price__lte=request.GET.get('max_price'))

    if request.GET.get('rating'):
        try:
            min_rating = float(request.GET.get('rating'))
            products = products.annotate(avg_rating=Avg('ratings__rating')).filter(avg_rating__gte=min_rating)
        except ValueError:
            pass

    if request.GET.get('search'):
        search_query = request.GET.get('search')
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )

    context = {
        'category': category,
        'categories': categories,
        'products': products,
        'min_price': min_price,
        'max_price': max_price,
    }
    return render(request, 'shop/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(Product, slug=slug, available=True)
    related_products = Product.objects.filter(category=product.category).exclude(id=product.id)

    user_rating = None
    rating_form = None

    if request.user.is_authenticated:
        try:
            user_rating = Rating.objects.get(user=request.user, product=product)
        except Rating.DoesNotExist:
            user_rating = None
        rating_form = RatingForm(instance=user_rating)

    context = {
        'product': product,
        'related_products': related_products,
        'user_rating': user_rating,
        'rating_form': rating_form,
    }
    return render(request, 'shop/product_detail.html', context)


@login_required
def cart_detail(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    context = {'cart': cart}
    return render(request, 'shop/cart.html', context)


# @login_required
# def add_to_cart(request, product_id):
#     product = get_object_or_404(Product, id=product_id, available=True)
#     cart, created = Cart.objects.get_or_create(user=request.user)

#     cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)
#     cart_item.quantity += 1
#     cart_item.save()

#     messages.success(request, f'{product.name} has been added to your cart.')
#     return redirect('shop:product_detail', slug=product.slug)

@login_required
def add_to_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id, available=True)
    cart, created = Cart.objects.get_or_create(user=request.user)

    quantity_to_add = int(request.POST.get('quantity', 1))  # get quantity from form or default 1

    cart_item, created = CartItem.objects.get_or_create(cart=cart, product=product)

    if created:
        cart_item.quantity = quantity_to_add
    else:
        cart_item.quantity += quantity_to_add

    cart_item.save()

    messages.success(request, f'{quantity_to_add} x {product.name} added to your cart.')
    return redirect('shop:product_detail', slug=product.slug)


@login_required
def remove_from_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)
    cart_item.delete()

    messages.success(request, f'{product.name} has been removed from your cart.')
    return redirect('shop:cart_detail')


@login_required
def update_cart(request, product_id):
    cart = get_object_or_404(Cart, user=request.user)
    product = get_object_or_404(Product, id=product_id)
    cart_item = get_object_or_404(CartItem, cart=cart, product=product)

    quantity = int(request.POST.get('quantity', 1))

    if quantity <= 0:
        cart_item.delete()
        messages.success(request, f'{product.name} has been removed from your cart.')
    else:
        cart_item.quantity = quantity
        cart_item.save()
        messages.success(request, 'Cart updated successfully.')

    return redirect('shop:cart_detail')


@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)

    if not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('shop:cart_detail')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.user = request.user
            order.save()
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.new_price,
                )
            cart.items.all().delete()
            cart.checked_out = True
            cart.save()
            messages.success(request, 'Your order has been placed successfully.')
            request.session['order_id'] = order.id
            return redirect('shop:payment_process')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        initial_data = {
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
        }
        form = CheckoutForm(initial=initial_data)

    context = {'form': form, 'cart': cart}
    return render(request, 'shop/checkout.html', context)


@csrf_exempt
@login_required
def payment_process(request):
    order_id = request.session.get('order_id')
    if not order_id:
        messages.error(request, 'No order found.')
        return redirect('shop:home')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    payment_data = generate_sslcommerz_payment(order, request)
    if payment_data.get('status') == 'SUCCESS':
        return redirect(payment_data['GatewayPageURL'])
    else:
        messages.error(request, 'Payment initiation failed. Please try again.')
        return redirect('shop:checkout')


@csrf_exempt
@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.paid = True
    order.status = 'processing'
    order.transaction_id = str(order.id)
    order.save()

    for item in order.items.all():
        product = item.product
        product.stock = max(product.stock - item.quantity, 0)
        product.save()

    send_order_confirmation_email(order)
    messages.success(request, 'Payment successful. Your order is being processed.')
    return redirect('shop:profile')


@csrf_exempt
@login_required
def payment_fail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'canceled'
    order.save()

    messages.error(request, 'Payment failed. Please try again.')
    return redirect('shop:checkout')


@csrf_exempt
@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'canceled'
    order.save()
    messages.info(request, 'Your order has been canceled.')
    return redirect('shop:cart_detail')


@login_required
def profile(request):
    tab = request.GET.get('tab')
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    completed_orders_count = orders.filter(status='delivered').count()
    total_spent = sum(order.get_total_cost() for order in orders if order.paid)
    order_history_active = (tab == 'orders')

    context = {
        'user': request.user,
        'orders': orders,
        'order_history_active': order_history_active,
        'completed_orders': completed_orders_count,
        'total_spent': total_spent,
    }
    return render(request, 'shop/profile.html', context)


@login_required
def rate_product(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    order_items = OrderItem.objects.filter(
        order__user=request.user,
        product=product,
        order__paid=True
    )

    if not order_items.exists():
        messages.error(request, 'You can only rate products you have purchased.')
        return redirect('shop:product_detail', slug=product.slug)

    try:
        rating = Rating.objects.get(user=request.user, product=product)
    except Rating.DoesNotExist:
        rating = None

    if request.method == 'POST':
        form = RatingForm(request.POST, instance=rating)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.user = request.user
            rating.product = product
            rating.save()
            messages.success(request, 'Your review has been submitted.')
            return redirect('shop:product_detail', slug=product.slug)
    else:
        form = RatingForm(instance=rating)

    context = {
        'form': form,
        'product': product,
    }
    return render(request, 'shop/rate_product.html', context)


@login_required
def profile_update(request):
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
            return redirect('shop:profile')
    else:
        form = ProfileUpdateForm(instance=request.user)

    return render(request, 'shop/profile_update.html', {'form': form})

def verify_email(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user and default_token_generator.check_token(user, token):
        user.is_verified = True
        user.save()
        messages.success(request, 'Email verified successfully! You can now log in.')
        return redirect('shop:login')
    else:
        messages.error(request, 'Verification link is invalid or expired.')
        return redirect('shop:login')

def email_verification_sent(request):
    return render(request, 'shop/email_verification_sent.html')