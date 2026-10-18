from django.contrib.auth import views as auth_views
from django.urls import path

from .forms import LoginForm
from .views import ProfileSetupView, RegisterView

urlpatterns = [
    path('login/', auth_views.LoginView.as_view(authentication_form=LoginForm, redirect_authenticated_user=True), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('register/', RegisterView.as_view(), name='register'),
    path('register/profile/', ProfileSetupView.as_view(), name='register_profile'),
    path('profile/edit/', ProfileSetupView.as_view(), name='edit_profile'),
]
