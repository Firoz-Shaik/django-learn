import requests
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import RegistrationForm, UserForm, UserProfileForm, ChangePasswordForm
from .models import Account, UserProfile
from orders.models import Order
from django.contrib import auth, messages
from django.contrib.sites.shortcuts import get_current_site
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from ecommerce.mail import send_templated_email
from carts.views import merge_guest_cart

# Create your views here.

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            email = form.cleaned_data['email']
            phone_number = form.cleaned_data['phone_number']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = Account.objects.create_user(first_name=first_name, last_name=last_name, email=email, username=username, phone_number=phone_number, password=password)
            user.save()

            #Add user to User Profile
            profile = UserProfile()
            profile.user = user
            profile.profile_picture = 'default/default-user.png'
            profile.save()
            # User activation
            current_site = get_current_site(request)
            send_templated_email(
                'Please activate your account',
                'accounts/account_verification_mail.html',
                {
                    'user': user,
                    'domain': current_site,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                },
                email,
            )

            return redirect('/accounts/login/?command=verification&email=' + email)
    else:
        form = RegistrationForm()

    context = {
        'form': form
    }
    return render(request, 'accounts/register.html', context)

def login(request):
    if request.method=='POST':
        email = request.POST['email']
        password = request.POST['password']

        user = auth.authenticate(email=email, password=password)

        if user is not None:
            merge_guest_cart(request, user)
            auth.login(request, user)
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    nextPage = params['next']
                    return redirect(nextPage)
            except:
                return redirect('index')
        else:
            messages.error(request, 'Invalid login credentials')
            return redirect('login')    
    return render(request, "accounts/login.html")

@login_required(login_url='login')
def logout(request):
    auth.logout(request)
    messages.success(request, 'You are logged out.')
    return redirect('login')

def activate(request, uidb64, token):
    try:
        uid = urlsafe_base64_decode(uidb64).decode()
        user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None
    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, 'Your account is activated. Please Log In to use your account.')
        return redirect('login')
    else:
        messages.error(request, 'Invalid registration url (or) Registration url expired.')
        return redirect('register')

def forgot_password(request):
    if request.method=='POST':
        email = request.POST['email']
        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__iexact=email)
            current_site = get_current_site(request)
            send_templated_email(
                'Reset your password',
                'accounts/reset_password_mail.html',
                {
                    'user': user,
                    'domain': current_site,
                    'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                    'token': default_token_generator.make_token(user),
                },
                email,
            )
            messages.success(request, 'Password reset link has been sent to your email address.')
            return redirect('login')
        else:
            messages.error(request, 'Account does not exist')
            return redirect('forgot_password')
    return render(request, "accounts/forgot_password.html")
def reset_password_validate(request, uidb64, token):
    try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = Account._default_manager.get(pk=uid)
    except(TypeError, ValueError, OverflowError, Account.DoesNotExist):
            user = None
    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid
        messages.success(request, 'Please reset your password')
        return redirect('reset_password')
    else:
        messages.error(request, 'This link has been expired')
        return redirect('login')

def reset_password(request):
    if request.method=='POST':
        password = request.POST['password']
        confirm_password = request.POST['confirm_password']
        if password == confirm_password:
            uid = request.session.get('uid')
            user = Account.objects.get(pk=uid)
            user.set_password(password)
            user.save()
            messages.success(request, 'Password reset successful')
            return redirect('login')
        else:
            messages.error(request, 'Password does not match')
            return redirect('reset_password')
    else:
        return render(request, "accounts/reset_password.html")
@login_required(login_url='login')
def dashboard(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True)
    orders_count = orders.count()
    userprofile = get_object_or_404(UserProfile, user=request.user)
    context = {
        'orders_count': orders_count,
        'userprofile': userprofile
    }
    return render(request, "accounts/dashboard.html", context)


@login_required(login_url='login')
def edit_profile(request):
    userprofile = get_object_or_404(UserProfile, user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('edit_profile')
        else:
            messages.error(request, 'Please correct the errors.')
            return render(request, "accounts/edit_profile.html", {
                'user_form': user_form,
                'profile_form': profile_form,
                'userprofile': userprofile,
            })
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)
        context = {
            'user_form': user_form,
            'profile_form': profile_form,
            'userprofile': userprofile
        }
        return render(request, "accounts/edit_profile.html", context)
@login_required(login_url='login')
def change_password(request):
    form = ChangePasswordForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            if not request.user.check_password(form.cleaned_data['current_password']):
                form.add_error('current_password', 'The current password is incorrect.')
            else:
                request.user.set_password(form.cleaned_data['new_password'])
                request.user.save(update_fields=['password'])
                messages.success(request, 'Password updated successfully.')
                return redirect('login')
    return render(request, "accounts/change_password.html", {'form': form})