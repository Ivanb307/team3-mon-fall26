from django.contrib.auth import authenticate, get_user_model
from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import Profile

User = get_user_model()
PASSWORD = 'Hudson-River-Run-77'


class RegisterTests(TestCase):
    def post_register(self, **overrides):
        data = {
            'display_username': 'parkfan',
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
            'display_username': 'ParkFan42',
            'bio': 'I love pickup soccer and discovering new parks.',
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
        self.assertIn('<form method="post" class="auth-form" autocomplete="off">', response.content.decode())
        self.assertContains(response, 'name="display_username"')
        self.assertContains(response, 'autocomplete="off"')

    def test_profile_setup_requires_login(self):
        self.assertRedirects(self.client.get(reverse('register_profile')), reverse('register'))

    def test_valid_signup_creates_account_and_empty_profile_then_redirects_to_profile(self):
        response = self.post_register()
        self.assertRedirects(response, reverse('register_profile'))
        user = User.objects.get(email='parkfan@nyu.edu')
        self.assertEqual(user.email, 'parkfan@nyu.edu')
        self.assertEqual(user.username, 'parkfan')
        self.assertNotEqual(user.password, PASSWORD)
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.display_username, 'parkfan')
        self.assertEqual(profile.bio, '')
        self.assertEqual(profile.home_borough, '')
        self.assertEqual(profile.favorite_sports, [])
        self.assertEqual(profile.skill_level, '')

    def test_profile_details_are_optional_and_can_be_saved(self):
        self.post_register()
        response = self.client.get(reverse('register_profile'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/profile_setup.html')
        self.assertContains(response, '<h1 class="auth-title">Complete your profile</h1>', html=True)
        self.assertContains(response, 'name="display_username"')
        self.assertContains(response, 'value="parkfan"')
        self.assertContains(response, 'name="bio"')
        self.assertContains(response, 'Share a little bit about yourself or some fun facts.')
        self.assertContains(response, 'Skip for now')
        self.assertContains(response, 'placeholder="John"')
        self.assertContains(response, 'placeholder="Doe"')
        self.assertIn('<form method="post" class="auth-form" autocomplete="off">', response.content.decode())
        self.assertContains(response, 'autocomplete="off"')
        self.assertNotContains(response, 'Search sports')
        self.assertContains(response, '<details class="profile-sport-dropdown"', html=False)
        self.assertContains(response, 'name="favorite_sports"')
        self.assertContains(response, 'Add sport')
        self.assertNotContains(response, 'Already have an account?')
        self.assertNotContains(response, 'Separate multiple sports with commas.')

        response = self.post_profile(
            display_username='parkfan',
            bio='',
            first_name='',
            last_name='',
            home_borough='',
            favorite_sports='',
            skill_level='',
        )
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(email='parkfan@nyu.edu')
        self.assertEqual(user.first_name, '')
        self.assertEqual(user.last_name, '')
        profile = Profile.objects.get(user=user)
        self.assertEqual(profile.home_borough, '')
        self.assertEqual(profile.display_username, 'parkfan')
        self.assertEqual(profile.bio, '')
        self.assertEqual(profile.favorite_sports, [])
        self.assertEqual(profile.skill_level, '')

    def test_profile_details_can_be_updated_later(self):
        self.post_register()
        self.client.post(reverse('register_profile'), {
            'display_username': 'ParkFan42',
            'bio': 'I love pickup soccer and discovering new parks.',
            'first_name': 'Park',
            'last_name': 'Fan',
            'home_borough': 'M',
            'favorite_sports': ['Basketball', 'Running', 'basketball'],
            'skill_level': 'beginner',
        })
        self.assertEqual(self.client.get(reverse('register_profile')).status_code, 200)
        self.post_profile(first_name='Park', last_name='Fan', favorite_sports=['Tennis'], skill_level='competitive')
        profile = Profile.objects.get(user__email='parkfan@nyu.edu')
        self.assertEqual(profile.home_borough, 'M')
        self.assertEqual(profile.display_username, 'ParkFan42')
        self.assertEqual(profile.bio, 'I love pickup soccer and discovering new parks.')
        self.assertEqual(profile.favorite_sports, ['Tennis'])
        self.assertEqual(profile.skill_level, 'competitive')
        user = User.objects.get(email='parkfan@nyu.edu')
        self.assertEqual((user.first_name, user.last_name), ('Park', 'Fan'))
        self.assertEqual(user.username, 'ParkFan42')

    def test_edit_profile_prefills_existing_information_without_skip_link(self):
        user = User.objects.create_user(
            'loginname', 'login@nyu.edu', PASSWORD, first_name='Taylor', last_name='Runner'
        )
        profile = Profile.objects.create(
            user=user,
            display_username='TrackStar',
            bio='I run a weekly neighborhood game.',
            home_borough='Q',
            favorite_sports=['Soccer'],
            skill_level='intermediate',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('edit_profile'))

        self.assertContains(response, '<h1 class="auth-title">Edit your profile</h1>', html=True)
        self.assertContains(response, 'value="TrackStar"')
        self.assertContains(response, 'value="Taylor"')
        self.assertContains(response, 'value="Runner"')
        self.assertContains(response, 'value="Soccer"')
        self.assertContains(response, 'I run a weekly neighborhood game.')
        self.assertNotContains(response, 'Skip for now')
        self.assertEqual(response.context['form'].instance, profile)

    def test_editing_public_username_updates_account_username(self):
        user = User.objects.create_user('loginname', 'login@nyu.edu', PASSWORD)
        Profile.objects.create(user=user)
        self.client.force_login(user)

        response = self.client.post(reverse('edit_profile'), {
            'display_username': 'NewPublicName',
            'bio': 'I like basketball.',
            'first_name': 'Jordan',
            'last_name': 'Player',
            'home_borough': '',
            'favorite_sports': ['Basketball'],
            'skill_level': 'beginner',
        })

        self.assertRedirects(response, reverse('home'))
        user.refresh_from_db()
        self.assertEqual(user.username, 'NewPublicName')
        self.assertEqual(user.first_name, 'Jordan')
        self.assertEqual(user.profile.display_username, 'NewPublicName')
        self.assertEqual(user.profile.bio, 'I like basketball.')

    def test_profile_display_username_must_be_unique_case_insensitively(self):
        User.objects.create_user('first', 'first@nyu.edu', PASSWORD)
        Profile.objects.create(user=User.objects.get(username='first'), display_username='ParkRunner')
        second_user = User.objects.create_user('second', 'second@nyu.edu', PASSWORD)
        Profile.objects.create(user=second_user)
        self.client.force_login(second_user)

        response = self.client.post(reverse('edit_profile'), {
            'display_username': 'parkrunner',
            'bio': '',
            'first_name': '',
            'last_name': '',
            'home_borough': '',
            'favorite_sports': [],
            'skill_level': '',
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn('display_username', response.context['form'].errors)

    def test_profile_username_database_constraint_is_case_insensitive(self):
        first = User.objects.create_user('first', 'first@nyu.edu', PASSWORD)
        second = User.objects.create_user('second', 'second@nyu.edu', PASSWORD)
        Profile.objects.create(user=first, display_username='ParkRunner')
        profile = Profile(user=second, display_username='parkrunner')

        with self.assertRaises(IntegrityError):
            profile.save()

    def test_saved_custom_sports_remain_available_on_profile_edit_page(self):
        self.post_register()
        self.post_profile(favorite_sports=['Basketball', 'Running', 'Rock climbing'])

        response = self.client.get(reverse('register_profile'))

        self.assertIn('Rock climbing', response.context['form']['favorite_sports'].value())

    def test_profile_favorite_sports_accepts_custom_sports_without_commas(self):
        self.post_register()
        self.post_profile(
            favorite_sports=['Basketball'],
            custom_sport='Rock climbing',
        )
        profile = Profile.objects.get(user__email='parkfan@nyu.edu')
        self.assertEqual(profile.favorite_sports, ['Basketball', 'Rock climbing'])

    def test_profile_setup_can_be_skipped_without_losing_account(self):
        response = self.post_register()
        user = User.objects.get(email='parkfan@nyu.edu')
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

    def test_signup_username_cannot_duplicate_an_existing_profile_username(self):
        existing_user = User.objects.create_user('existing', 'existing@nyu.edu', PASSWORD)
        Profile.objects.create(user=existing_user, display_username='ParkRunner')

        response = self.post_register(display_username='parkrunner')

        self.assertContains(response, 'That username is already in use.')
        self.assertEqual(User.objects.count(), 1)

    def test_login_usernames_can_match_when_emails_differ(self):
        first = self.post_register(display_username='ParkFan')
        self.assertRedirects(first, reverse('register_profile'))

        self.client.post(reverse('logout'))
        second = self.post_register(
            display_username='ParkFan2',
            email='other@nyu.edu',
        )
        self.assertRedirects(second, reverse('register_profile'))

        users = User.objects.filter(email__in=['parkfan@nyu.edu', 'other@nyu.edu'])
        self.assertEqual(users.count(), 2)
        self.assertEqual(users.values_list('username', flat=True).distinct().count(), 2)

    def test_weak_password_is_rejected_without_creating_a_user(self):
        response = self.post_register(password1='12345678', password2='12345678')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['form'].errors)
        self.assertFalse(User.objects.exists())

    def test_logged_in_users_are_sent_home(self):
        User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD)
        self.client.force_login(User.objects.get(email='parkfan@nyu.edu'))
        self.assertRedirects(self.client.get(reverse('register')), reverse('home'))


class LoginTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD)

    def test_page_renders(self):
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/login.html')
        self.assertIn('<form method="post" class="auth-form" autocomplete="off">', response.content.decode())
        self.assertContains(response, 'autocomplete="off"')

    def test_login_rejects_internal_username(self):
        response = self.client.post(reverse('login'), {'username': 'parkfan', 'password': PASSWORD})
        self.assertContains(response, 'Invalid email or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_rejects_public_username(self):
        Profile.objects.create(user=self.user, display_username='ParkFan')
        response = self.client.post(reverse('login'), {'username': 'ParkFan', 'password': PASSWORD})
        self.assertContains(response, 'Invalid email or password')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_login_with_email_ignores_case(self):
        response = self.client.post(reverse('login'), {'username': 'ParkFan@NYU.edu', 'password': PASSWORD})
        self.assertRedirects(response, reverse('home'))

    def test_login_uses_email_not_internal_usernames(self):
        user = User.objects.create_user('another-internal-name', 'other@nyu.edu', PASSWORD)
        self.client.post(reverse('login'), {
            'username': 'parkfan@nyu.edu',
            'password': 'incorrect-password',
        })
        response = self.client.post(reverse('login'), {
            'username': 'other@nyu.edu',
            'password': PASSWORD,
        })
        self.assertRedirects(response, reverse('home'))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_username_authentication_is_only_available_to_staff(self):
        self.assertIsNone(authenticate(username=self.user.username, password=PASSWORD))

        admin = User.objects.create_user(
            'siteadmin',
            'admin@nyu.edu',
            PASSWORD,
            is_staff=True,
        )
        self.assertEqual(authenticate(username=admin.username, password=PASSWORD), admin)

    def test_admin_login_accepts_staff_username(self):
        admin = User.objects.create_user(
            'siteadmin',
            'admin@nyu.edu',
            PASSWORD,
            is_staff=True,
        )

        response = self.client.post(reverse('admin:login'), {
            'username': admin.username,
            'password': PASSWORD,
            'next': reverse('admin:index'),
        })

        self.assertRedirects(response, reverse('admin:index'))
        self.assertEqual(int(self.client.session['_auth_user_id']), admin.pk)

    def test_wrong_password_and_unknown_account_show_the_same_generic_error(self):
        for username in ('parkfan@nyu.edu', 'nobody@nyu.edu'):
            response = self.client.post(reverse('login'), {'username': username, 'password': 'wrong-pass'})
            self.assertContains(response, 'Invalid email or password')
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_requires_post_and_ends_the_session(self):
        self.client.force_login(self.user)
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('home'))
        self.assertNotIn('_auth_user_id', self.client.session)


class LandingLinksTests(TestCase):
    def test_landing_links_to_the_real_auth_pages(self):
        response = self.client.get(reverse('home'))
        self.assertContains(response, f'href="{reverse("login")}"')
        self.assertContains(response, f'href="{reverse("register")}"')

    def test_authenticated_navigation_and_account_footer_link_to_profile_edit(self):
        user = User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD)
        self.client.force_login(user)

        response = self.client.get(reverse('home'))

        self.assertContains(response, f'href="{reverse("edit_profile")}"')
        self.assertContains(response, '>View profile</a>')
        self.assertContains(response, '>Edit profile</a>')

    def test_profile_saved_message_has_two_second_dismissal(self):
        self.client.force_login(User.objects.create_user('parkfan', 'parkfan@nyu.edu', PASSWORD))

        response = self.client.post(reverse('register_profile'), {
            'display_username': 'parkfan',
            'first_name': 'Park',
            'last_name': 'Fan',
            'home_borough': 'M',
            'favorite_sports': ['Basketball'],
            'skill_level': 'beginner',
        }, follow=True)

        self.assertContains(response, 'Profile details saved.')
        self.assertContains(response, 'data-auto-dismiss="2000"')

    def test_signup_message_shows_on_the_landing_page(self):
        response = self.client.post(reverse('register'), {
            'display_username': 'parkfan', 'email': 'parkfan@nyu.edu',
            'password1': PASSWORD, 'password2': PASSWORD,
        }, follow=True)
        self.assertContains(response, 'Account created. Welcome to NYC Active!')
