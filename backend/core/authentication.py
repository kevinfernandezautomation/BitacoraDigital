import hashlib, hmac
from datetime import timedelta
from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.http import require_http_methods
from django.utils.http import url_has_allowed_host_and_scheme
from .models import LoginBucket, LoginEvent

def digest(value):
    return hmac.new(settings.SECRET_KEY.encode(), value.encode(), hashlib.sha256).hexdigest()

@transaction.atomic
def reserve_attempt(ip, username):
    now = timezone.now()
    keys = sorted([(digest('ip:'+ip), settings.LOGIN_IP_LIMIT), (digest('pair:'+ip+':'+username), settings.LOGIN_PAIR_LIMIT)])
    rows = []
    for key, limit in keys:
        row, _ = LoginBucket.objects.select_for_update().get_or_create(key=key, defaults={'window':now})
        if now-row.window >= timedelta(seconds=settings.LOGIN_WINDOW):
            row.window, row.count = now, 0
        rows.append((row, limit))
    if any(row.count >= limit for row, limit in rows):
        return False
    for row, _ in rows:
        row.count += 1
        row.save(update_fields=['window','count'])
    return True

@never_cache
@csrf_protect
@require_http_methods(['GET','POST'])
def sign_in(request):
    if request.user.is_authenticated:
        return redirect('/')
    target = request.POST.get('next', request.GET.get('next',''))
    if not url_has_allowed_host_and_scheme(target, {request.get_host()}, require_https=request.is_secure()):
        target = '/'
    form = AuthenticationForm(request)
    error = ''
    status = 200
    if request.method == 'POST':
        username = request.POST.get('username','')[:150].casefold().strip()
        identifier = digest(username)
        # REMOTE_ADDR only; do not trust arbitrary forwarded headers.
        ip = request.META.get('REMOTE_ADDR','unknown')
        if settings.SECURE_PROXY_SSL_HEADER:
            ip = request.META.get('HTTP_X_REAL_IP', ip)
        if not reserve_attempt(ip, username):
            error = 'Demasiados intentos. Intente nuevamente más tarde.'
            status = 429
        else:
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                login(request, form.get_user())
                request.session.set_expiry(settings.SESSION_COOKIE_AGE)
                LoginEvent.objects.create(identifier=identifier,outcome='success')
                return redirect(target or '/')
            LoginEvent.objects.create(identifier=identifier,outcome='failure')
            error = 'Usuario o contraseña incorrectos.'
    response = render(request,'login.html',{'form':form,'error':error,'next':target},status=status)
    if status == 429: response['Retry-After'] = str(settings.LOGIN_WINDOW)
    return response

class IdleSessionMiddleware:
    def __init__(self, get_response): self.get_response = get_response
    def __call__(self, request):
        if request.user.is_authenticated:
            now = int(timezone.now().timestamp())
            last = request.session.get('last_activity', now)
            if now-last >= settings.SESSION_COOKIE_AGE:
                logout(request)
                return redirect('/login/')
            request.session['last_activity'] = now
        return self.get_response(request)
