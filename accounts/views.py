from django.contrib import messages
from django.contrib.auth import login
from django.db import IntegrityError, transaction
from django.shortcuts import redirect
from django.views.generic import FormView

from .forms import ProfileSetupForm, RegisterForm
from .models import Profile


class RegisterView(FormView):
    template_name = 'registration/register.html'
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        user = form.save(commit=False)
        user.username = form.cleaned_data['display_username']
        try:
            with transaction.atomic():
                user.save()
                Profile.objects.create(
                    user=user,
                    display_username=form.cleaned_data['display_username'],
                )
        except IntegrityError:
            form.add_error(None, 'That username or email is no longer available. Please choose another.')
            return self.form_invalid(form)

        login(self.request, user)
        messages.success(self.request, 'Account created. Welcome to NYC Active!')
        return redirect('register_profile')


class ProfileSetupView(FormView):
    template_name = 'registration/profile_setup.html'
    form_class = ProfileSetupForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('register')
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['instance'], _ = Profile.objects.get_or_create(user=self.request.user)
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['is_edit'] = self.request.resolver_match.url_name == 'edit_profile'
        return context

    def form_valid(self, form):
        user = self.request.user
        user.username = form.cleaned_data['display_username']
        user.first_name = form.cleaned_data['first_name']
        user.last_name = form.cleaned_data['last_name']
        try:
            with transaction.atomic():
                user.save(update_fields=['username', 'first_name', 'last_name'])
                form.save()
        except IntegrityError:
            form.add_error('display_username', 'That username is no longer available. Please choose another username.')
            return self.form_invalid(form)
        messages.success(self.request, 'Profile details saved.')
        return redirect('home')
