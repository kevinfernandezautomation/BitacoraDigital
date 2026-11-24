from django.contrib.auth.views import PasswordChangeView
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET
from .models import Audit

@method_decorator(never_cache, name='dispatch')
class OwnPasswordChange(PasswordChangeView):
    template_name = 'form.html'
    success_url = '/security/'
    def form_valid(self, form):
        response = super().form_valid(form)
        Audit.objects.create(actor=self.request.user, action='Cambio de contraseña propia')
        return response

@login_required
@never_cache
@require_GET
def panel(request):
    return render(request, 'security.html', {'secure_transport': request.is_secure()})

class SecurityHeaders:
    def __init__(self, get_response):
        self.get_response = get_response
    def __call__(self, request):
        response = self.get_response(request)
        response['Content-Security-Policy'] = "default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; connect-src 'self'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'"
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if request.user.is_authenticated or request.path in ('/login/', '/password/'):
            response['Cache-Control'] = 'private, no-store'
        return response
