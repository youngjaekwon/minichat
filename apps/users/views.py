from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView as DjangoLoginView
from django.contrib.auth.views import LogoutView as DjangoLogoutView
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import FormView

from apps.users.forms import LoginForm, SignupForm
from apps.users.models import User


class SignupView(FormView):
    """회원가입 뷰."""

    form_class = SignupForm
    template_name = "users/signup.html"
    success_url = "/"

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        if request.user.is_authenticated:
            return redirect("/")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form: SignupForm) -> HttpResponse:
        form.save()
        user = User.authenticate_user(
            email=form.cleaned_data["email"],
            password=form.cleaned_data["password"],
        )
        if user:
            login(self.request, user)
        messages.success(self.request, "회원가입이 완료되었습니다.")
        return super().form_valid(form)


class LoginView(DjangoLoginView):
    """로그인 뷰."""

    form_class = LoginForm
    template_name = "users/login.html"
    redirect_authenticated_user = True


class LogoutView(LoginRequiredMixin, DjangoLogoutView):
    """로그아웃 뷰."""

    http_method_names = ["post"]
    next_page = reverse_lazy("users:login")

    def dispatch(self, request: HttpRequest, *args, **kwargs) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        messages.success(request, "로그아웃되었습니다.")
        return response
