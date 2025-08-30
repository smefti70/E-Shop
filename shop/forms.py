from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import Rating, Order, CustomUser
from django.contrib.auth import get_user_model

User = get_user_model()

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Email already exists.")
        return email

# class UserRegistrationForm(UserCreationForm):
#     username = forms.CharField(max_length=150, required=True)
#     email = forms.EmailField(required=True)
#     first_name = forms.CharField(max_length=30, required=False)
#     last_name = forms.CharField(max_length=30, required=False)

#     class Meta:
#         model = CustomUser
#         fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

class RatingForm(forms.ModelForm):
    class Meta:
        model = Rating
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(choices = [(i, i) for i in range(1, 6)]),
            'comment': forms.Textarea(attrs={'rows': 4, 'cols': 40}),
        }

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address', 'city', 'postal_code', 'note']
        widgets = {
            'note': forms.Textarea(attrs={'rows': 3})
        }

class ProfileUpdateForm(UserChangeForm):
    full_name = forms.CharField(required=True)
    email = forms.EmailField(required=True)
    profile_picture = forms.ImageField(required=False)  # allow empty upload

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'profile_picture')  # first_name, last_name handled via full_name

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['full_name'].initial = f"{self.instance.first_name} {self.instance.last_name}".strip()

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data['full_name']
        parts = full_name.split()
        user.first_name = parts[0] if parts else ''
        user.last_name = ' '.join(parts[1:]) if len(parts) > 1 else ''

        if commit:
            user.save()
        return user