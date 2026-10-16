from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class RegisterForm(UserCreationForm):
    email = forms.EmailField()

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ('username', 'email')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        placeholders = {
            'username': 'Pick a username',
            'email': 'you@example.com',
            'password1': 'Password',
            'password2': 'Confirm password',
        }
        for name, text in placeholders.items():
            self.fields[name].widget.attrs['placeholder'] = text
            self.fields[name].help_text = ''
        self.fields['password1'].help_text = 'At least 8 characters, not too common or all numbers.'
        self.fields['password2'].label = 'Confirm password'

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class LoginForm(AuthenticationForm):
    # One message for a wrong password or an unknown account, so the form
    # doesn't reveal which emails are registered (#11).
    error_messages = {
        **AuthenticationForm.error_messages,
        'invalid_login': 'Invalid email or password',
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'Email or username'
        self.fields['username'].widget.attrs['placeholder'] = 'you@example.com'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'
