from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from parks.models import Borough

from .models import Profile, ProfileSkillLevel


COMMON_SPORTS = (
    'Basketball',
    'Soccer',
    'Running',
    'Tennis',
    'Pickleball',
    'Volleyball',
    'Handball',
    'Baseball',
    'Softball',
    'Football',
    'Cricket',
    'Cycling',
    'Swimming',
    'Yoga',
    'Ultimate frisbee',
)


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
        self.fields['username'].label = 'Username'
        self.fields['username'].help_text = 'This is the name other members will see.'
        self.fields['password1'].help_text = 'At least 8 characters, not too common or all numbers.'
        self.fields['password2'].label = 'Confirm password'

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class ProfileSetupForm(forms.ModelForm):
    first_name = forms.CharField(
        max_length=150,
        label='First name',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'John'}),
    )
    last_name = forms.CharField(
        max_length=150,
        label='Last name',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Doe'}),
    )
    favorite_sports = forms.MultipleChoiceField(
        choices=[(sport, sport) for sport in COMMON_SPORTS],
        label='Favorite sports',
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    custom_sport = forms.CharField(
        max_length=50,
        label='Add another sport',
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Type a sport'}),
    )

    class Meta:
        model = Profile
        fields = ('home_borough', 'favorite_sports', 'skill_level')
        labels = {
            'home_borough': 'Home borough',
            'skill_level': 'Overall skill level',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['home_borough'].required = False
        self.fields['home_borough'].choices = [('', 'Choose your borough'), *Borough.choices]
        self.fields['skill_level'].required = False
        self.fields['skill_level'].choices = [
            ('', 'Choose your skill level'),
            *ProfileSkillLevel.choices,
        ]
        submitted_sports = []
        if self.is_bound:
            submitted_sports = self.data.getlist(self.add_prefix('favorite_sports'))
            custom_sport = self.data.get(self.add_prefix('custom_sport'), '').strip()
            if custom_sport:
                submitted_sports.append(custom_sport)
        choices = list(COMMON_SPORTS)
        choices.extend(sport for sport in submitted_sports if sport not in choices)
        self.fields['favorite_sports'].choices = [(sport, sport) for sport in choices]

    def clean_favorite_sports(self):
        return self.normalize_sports(self.cleaned_data['favorite_sports'])

    def clean(self):
        cleaned_data = super().clean()
        if 'favorite_sports' in cleaned_data:
            sports = [
                *cleaned_data['favorite_sports'],
                cleaned_data.get('custom_sport', ''),
            ]
            cleaned_data['favorite_sports'] = self.normalize_sports(sports)
        return cleaned_data

    @staticmethod
    def normalize_sports(sports):
        normalized = []
        seen = set()
        for sport in sports:
            sport = sport.strip()
            if sport and sport.casefold() not in seen:
                if len(sport) > 50:
                    raise forms.ValidationError('Sports must be 50 characters or fewer.')
                normalized.append(sport)
                seen.add(sport.casefold())
        if len(normalized) > 20:
            raise forms.ValidationError('Choose no more than 20 favorite sports.')
        return normalized


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
