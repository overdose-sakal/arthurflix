# users/forms.py

from django import forms
from django.contrib.auth import get_user_model
# Ensure all necessary models are imported
from .models import Avatar, UserProfile, MembershipKey 

User = get_user_model()


class LoginForm(forms.Form):
    """Standard form for username and password login."""
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
    Key submission is now case-sensitive (allows mixed case).
    """
    key = forms.CharField(
        max_length=32,
        min_length=32,
        # FIX: Removed oninput JS to prevent forced uppercase conversion
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '32-Character Key', 'autocapitalize': 'off', 'autocomplete': 'off'}),
        label='Membership Key'
    )


class RegistrationForm(forms.ModelForm):
    """
    Form for new user registration, including avatar selection.
    """
    # CRITICAL: Hidden field for avatar selection (set by JS in template)
    avatar_id = forms.ModelChoiceField(
        queryset=Avatar.objects.all().order_by('id'),
        empty_label=None, 
        widget=forms.HiddenInput(),
        required=True,
        label="Select Profile Avatar"
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        label='Password'
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control'}), 
        label='Repeat password'
    )

    class Meta:
        model = User 
        fields = ('username', 'email', 'first_name', 'last_name') 
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_password2(self):
        """Ensures passwords match."""
        cd = self.cleaned_data
        if cd.get('password') and cd.get('password2'):
            if cd['password'] != cd['password2']:
                raise forms.ValidationError('Passwords do not match.')
        return cd['password2']
    
    def save(self, commit=True):
        """Creates the User, sets the password, and creates the UserProfile with the avatar."""
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        
        if commit:
            user.save()
            selected_avatar = self.cleaned_data.get('avatar_id')
            
            UserProfile.objects.create(
                user=user,
                avatar=selected_avatar
            )
             
        return user