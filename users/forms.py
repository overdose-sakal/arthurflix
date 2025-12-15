# users/forms.py

from django import forms
from django.contrib.auth.models import User # Or your Custom User model

class LoginForm(forms.Form):
    """
    Standard form for username and password login.
    """
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
        label='Username'
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        label='Password'
    )

class MembershipKeyForm(forms.Form):
    """
    Form to submit the 32-character membership key.
    """
    key = forms.CharField(
        max_length=32,
        min_length=32,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '32-Character Key', 'autocapitalize': 'off', 'autocomplete': 'off'}),
        label='Membership Key'
    )

class RegistrationForm(forms.ModelForm):
    """
    Form for new user registration.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        label='Password'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        label='Repeat password'
    )

    class Meta:
        model = User # Use your actual User model if custom
        fields = ('username', 'email', 'first_name', 'last_name') # Adjust fields as necessary
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        cd = self.cleaned_data
        if cd['password'] != cd['password2']:
            raise forms.ValidationError('Passwords do not match.')
        return cd['password2']