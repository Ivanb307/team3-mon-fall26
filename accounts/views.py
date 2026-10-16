from django.contrib import messages
from django.contrib.auth import login
from django.shortcuts import redirect
from django.views.generic import FormView

from .forms import RegisterForm


class RegisterView(FormView):
    template_name = 'registration/register.html'
    form_class = RegisterForm

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect('home')
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, form.save())
        messages.success(self.request, 'Account created. Welcome to NYC Active!')
        return redirect('home')
