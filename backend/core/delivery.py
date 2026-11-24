"""Explicit external disclosure of an immutable archive; no automatic retries."""
import uuid
from datetime import timedelta
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.mail import EmailMessage
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from .models import Sheet, User, Audit, Delivery
from .closure import verify_archive, package

class DeliveryForm(forms.Form):
    email = forms.EmailField(label='Correo destinatario', max_length=254)
    confirm_email = forms.EmailField(label='Repita el correo destinatario', max_length=254)
    consent = forms.BooleanField(label='Confirmo que el destinatario está autorizado para recibir el expediente completo y sus adjuntos')
    token = forms.UUIDField(widget=forms.HiddenInput)
    def clean(self):
        data = super().clean()
        if data.get('email') != data.get('confirm_email'):
            self.add_error('confirm_email', 'Los correos deben coincidir.')
        return data

@login_required
@require_http_methods(['GET','POST'])
def send_sheet(request, pk):
    u = request.user
    if u.role != 'regente' or u.suspended or not u.is_active:
        raise PermissionDenied
    from .restrictions import enforce
    enforce(u, "email")
    s = get_object_or_404(Sheet.objects.select_related('regency'), pk=pk, regency__owner=u, closed=True)
    form = DeliveryForm(request.POST if request.method == 'POST' else None, initial={'token':uuid.uuid4()})
    def page(status=200):
        response = render(request,'delivery.html',{'s':s,'form':form,'deliveries':Delivery.objects.filter(sheet=s,actor=u).order_by('-created')[:25]},status=status)
        response['Cache-Control']='private, no-store'
        return response
    if request.method == 'GET': return page()
    if not form.is_valid(): return page(400)
    if not settings.SHEET_EMAIL_ENABLED: return HttpResponse('Envío deshabilitado',status=503)
    archive = getattr(s,'archive',None)
    if not archive or not verify_archive(archive): return HttpResponse('Expediente no verificable',status=409)
    if not settings.DEBUG and 'qa-self-signed' in archive.manifest: return HttpResponse('Firma de QA no autorizada para producción',status=409)
    data = package(archive)
    if len(data)>settings.SHEET_EMAIL_MAX_BYTES: return HttpResponse('Expediente supera el límite de correo; utilice descarga autorizada',status=413)
    with transaction.atomic():
        actor=User.objects.select_for_update().get(pk=u.pk)
        enforce(u, "email")
        if not actor.is_active or actor.suspended or actor.role!='regente': raise PermissionDenied
        if not Sheet.objects.filter(pk=pk,closed=True,regency__owner=actor).exists(): raise PermissionDenied
        token=form.cleaned_data['token']
        if Delivery.objects.filter(pk=token).exists(): return HttpResponse('Solicitud ya registrada; consulte el historial',status=409)
        if Delivery.objects.filter(actor=actor,created__gte=timezone.now()-timedelta(hours=1)).count()>=settings.SHEET_EMAIL_HOURLY_LIMIT:
            return HttpResponse('Límite de envíos alcanzado',status=429)
        delivery=Delivery.objects.create(id=token,sheet=s,actor=actor,recipient=form.cleaned_data['email'],digest=archive.digest)
        Audit.objects.create(actor=actor,action=f'Correo solicitado {delivery.pk} hoja {pk}')
    # Outside the transaction: SMTP cannot participate in database atomicity.
    message=EmailMessage(f'CIQPA | Hoja cerrada {pk}',f'Se adjunta el expediente histórico de la hoja {pk}.\nSHA-256: {archive.digest}\nInformación confidencial. Si no es el destinatario previsto, comuníquese con el remitente.',to=[delivery.recipient],headers={'Message-ID':f'<{delivery.pk}@{settings.SHEET_EMAIL_MESSAGE_DOMAIN}>'})
    message.attach(f'hoja-{pk}.zip',data,'application/zip')
    try:
        result=message.send(fail_silently=False)
        outcome=('aceptado' if settings.EMAIL_BACKEND=='django.core.mail.backends.smtp.EmailBackend' else 'simulado') if result==1 else 'incierto'
    except Exception:
        # Timeout/disconnect may occur after SMTP accepted the message.
        outcome='incierto'
    with transaction.atomic():
        Delivery.objects.filter(pk=delivery.pk).update(status=outcome,finished=timezone.now())
        Audit.objects.create(actor=actor,action=f'Correo {outcome} {delivery.pk}')
    return redirect('sheet-email',pk=pk)
