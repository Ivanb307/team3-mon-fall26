from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

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

    def test_page_renders(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'registration/register.html')

    def test_valid_signup_creates_user_logs_in_and_redirects_home(self):
        response = self.post_register()
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='parkfan')
        self.assertEqual(user.email, 'parkfan@nyu.edu')
        self.assertNotEqual(user.password, PASSWORD)  # stored hashed
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

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
