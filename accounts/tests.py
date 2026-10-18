from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()
PASSWORD = 'Hudson-River-Run-77'


class RegisterTests(TestCase):
    def post_register(self, **overrides):
        data = {
            'username': 'parkfan',
            'email': 'parkfan@nyu.edu',
            'password1': PASSWORD,
            'password2': PASSWORD,
            **overrides,
        }
        return self.client.post(reverse('register'), data)

    def post_profile(self, **overrides):
        data = {
            'first_name': 'Park',
            'last_name': 'Fan',
            'home_borough': 'M',
            'favorite_sports': ['Basketball', 'Running', 'basketball'],
            'skill_level': 'beginner',
            **overrides,
        }
        return self.client.post(reverse('register_profile'), data)

    def test_page_renders(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_profile_setup_requires_login(self):
        self.assertRedirects(self.client.get(reverse('register_profile')), reverse('register'))

    def test_valid_signup_creates_account_and_empty_profile_then_redirects_to_profile(self):
        response = self.post_register()
        self.assertRedirects(response, reverse('register_profile'))
        user = User.objects.get(username='parkfan')
        self.assertEqual(user.email, 'parkfan@nyu.edu')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.home_borough, '')
        self.assertEqual(profile.favorite_sports, [])
        self.assertEqual(profile.skill_level, '')

    def test_profile_details_are_optional_and_can_be_saved(self):
        self.post_register()
        response = self.client.get(reverse('register_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/profile_setup.html')
        self.assertContains(response, 'placeholder="John"')
        self.assertContains(response, 'placeholder="Doe"')
        self.assertNotContains(response, 'Search sports')
        self.assertContains(response, '<details class="profile-sport-dropdown"', html=False)
        self.assertContains(response, 'name="favorite_sports"')
        self.assertContains(response, 'Add sport')
        self.assertNotContains(response, 'Already have an account?')
        self.assertNotContains(response, 'Separate multiple sports with commas.')

        response = self.post_profile(
            first_name='',
            last_name='',
            home_borough='',
            favorite_sports='',
            skill_level='',
        )
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='parkfan')
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.home_borough, '')
        self.assertEqual(profile.favorite_sports, [])
        self.assertEqual(profile.skill_level, '')

    def test_profile_details_can_be_updated_later(self):
        self.post_register()
        self.client.post(reverse('register_profile'), {
            'first_name': 'Park',
            'last_name': 'Fan',
            'home_borough': 'M',
            'favorite_sports': ['Basketball', 'Running', 'basketball'],
            'skill_level': 'beginner',
        })
        self.assertEqual(self.client.get(reverse('register_profile')).status_code, 200)
        self.post_profile(first_name='Park', last_name='Fan', favorite_sports=['Tennis'], skill_level='competitive')
        profile = Profile.objects.get(user__username='parkfan')
        self.assertEqual(profile.home_borough, 'M')
        self.assertEqual(profile.favorite_sports, ['Tennis'])
        self.assertEqual(profile.skill_level, 'competitive')
        user = User.objects.get(username='parkfan')
        self.assertEqual((user.first_name, user.last_name), ('Park', 'Fan'))

    def test_profile_favorite_sports_accepts_custom_sports_without_commas(self):
        self.post_register()
        self.post_profile(
            favorite_sports=['Basketball'],
            custom_sport='Rock climbing',
        )
        profile = Profile.objects.get(user__username='parkfan')
        self.assertEqual(profile.favorite_sports, ['Basketball', 'Rock climbing'])

    def test_profile_setup_can_be_skipped_without_losing_account(self):
        response = self.post_register()
        user = User.objects.get(username='parkfan')
        self.assertRedirects(response, reverse('register_profile'))
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.assertTrue(User.objects.filter(pk=user.pk).exists())
        self.assertTrue(Profile.objects.filter(user=user).exists())

    def test_signup_page_copy_and_button_are_unchanged(self):
        response = self.client.get(reverse('register'))
        self.assertContains(response, '<h1 class="auth-title">Create your account</h1>', html=True)
        self.assertContains(response, 'Join pickup games and park meetups across NYC.')
        self.assertContains(response, '>Create account</button>')

    def test_duplicate_email_is_rejected_without_creating_a_user(self):
        User.objects.create_user('runner', 'runner@nyu.edu', PASSWORD)
        response = self.post_register(email='Runner@nyu.edu')
        self.assertContains(response, 'An account with this email already exists.')
        self.assertEqual(User.objects.count(), 1)

    def test_weak_password_is_rejected_without_creating_a_user(self):
        response = self.post_register(password1='12345678', password2='12345678')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_logged_in_users_are_sent_home(self):
        User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD)
        self.client.login(username='parkfan', password=PASSWORD)
        self.assertRedirects(self.client.get(reverse('register')), reverse('home'))


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD)

    def test_page_renders(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')

    def test_login_with_username(self):
        response = self.client.post(reverse('login'), {'username': 'parkfan', 'password': PASSWORD})
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), self.user.pk)

    def test_login_with_email_ignores_case(self):
        response = self.client.post(reverse('login'), {'username': 'ParkFan@NYU.edu', 'password': PASSWORD})
        self.assertRedirects(response, reverse('home'))

    def test_wrong_password_and_unknown_account_show_the_same_generic_error(self):
        for username in ('parkfan', 'nobody@nyu.edu'):
            response = self.client.post(reverse('login'), {'username': username, 'password': 'wrong-pass'})
            self.assertContains(response, 'Invalid email or password')
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_post_and_ends_the_session(self):
        self.client.login(username='parkfan', password=PASSWORD)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class LandingLinksTests(TestCase):
    def test_landing_links_to_the_real_auth_pages(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, f'href="{reverse("register")}"')

    def test_signup_message_shows_on_the_landing_page(self):
        response = self.client.post(reverse('register'), {
            'username': 'parkfan', 'email': 'parkfan@nyu.edu', 'password1': PASSWORD, 'password2': PASSWORD,
        }, follow=True)
        self.assertContains(response, 'Account created. Welcome to NYC Active!')
