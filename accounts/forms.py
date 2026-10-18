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
            self.fields[name].widget.attrs['autocomplete'] = 'off'
        self.fields['username'].label = 'Login username'
        self.fields['username'].help_text = 'This login username is only used to login. Other members see your profile username.'
        self.fields['password1'].help_text = 'At least 8 characters, not too common or all numbers.'
        self.fields['password2'].label = 'Confirm password'
        self.fields['password1'].widget.attrs['autocomplete'] = 'new-password'
        self.fields['password2'].widget.attrs['autocomplete'] = 'new-password'

    def clean_email(self):
        email = self.cleaned_data['email']
        if get_user_model().objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account with this email already exists.')
        return email


class ProfileSetupForm(forms.ModelForm):
    display_username = forms.CharField(
        max_length=150,
        label='Username',
        required=False,
        help_text='This is the name other members see. It does not change your login username.',
    )
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
        fields = ('display_username', 'home_borough', 'favorite_sports', 'skill_level')
        labels = {
            'home_borough': 'Home borough',
            'skill_level': 'Overall skill level',
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields['display_username'].widget.attrs['placeholder'] = user.username
            if not self.is_bound:
                if not self.initial.get('display_username'):
                    self.initial['display_username'] = user.username
                self.initial.setdefault('first_name', user.first_name)
                self.initial.setdefault('last_name', user.last_name)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs['autocomplete'] = 'off'
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
        if self.instance and self.instance.pk:
            choices.extend(
                sport for sport in self.instance.favorite_sports
                if sport not in choices
            )
        choices.extend(sport for sport in submitted_sports if sport not in choices)
        self.fields['favorite_sports'].choices = [(sport, sport) for sport in choices]

    def clean_display_username(self):
        display_username = self.cleaned_data['display_username'].strip()
        if display_username and Profile.objects.filter(
            display_username__iexact=display_username
        ).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('That profile username is already in use.')
        return display_username

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
        self.fields['username'].widget.attrs['autocomplete'] = 'off'
        self.fields['password'].widget.attrs['placeholder'] = 'Password'
        self.fields['password'].widget.attrs['autocomplete'] = 'current-password'
