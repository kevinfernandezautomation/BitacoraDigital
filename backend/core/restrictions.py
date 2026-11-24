from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.http import require_http_methods
from .models import User, FeatureRestriction, Audit

FEATURES = [('create','Crear borradores'),('edit','Editar borradores y adjuntos'),('close','Cerrar hojas'),('email','Enviar hojas por correo'),('comment','Publicar comentarios'),('task','Asignar tareas')]

def active(user):
    now=timezone.now()
    return FeatureRestriction.objects.filter(regent=user, revoked_at__isnull=True, starts__lte=now).filter(Q(ends__isnull=True)|Q(ends__gt=now))

def enforce(user, feature):
    if user.role == 'regente' and active(user).filter(feature=feature).exists():
        raise PermissionDenied('Funcionalidad temporalmente suspendida. Consulte al CIQPA.')

class RestrictionForm(forms.Form):
    regent=forms.ModelChoiceField(queryset=User.objects.filter(role='regente',is_active=True).order_by('username'),label='Regente')
    feature=forms.ChoiceField(choices=FEATURES,label='Funcionalidad')
    reason=forms.CharField(max_length=500,label='Motivo',widget=forms.Textarea)
    ends=forms.DateTimeField(required=False,label='Fin de vigencia (opcional)',widget=forms.DateTimeInput(attrs={'type':'datetime-local'}))
    def clean_ends(self):
        value=self.cleaned_data['ends']
        if value and value<=timezone.now(): raise forms.ValidationError('Debe ser una fecha futura.')
        return value

@login_required
@require_http_methods(['GET','POST'])
@transaction.atomic
def panel(request):
    u=request.user
    if u.role not in ('admin','regente'): raise PermissionDenied
    form=RestrictionForm(request.POST or None) if u.role=='admin' else None
    if request.method=='POST':
        if u.role!='admin': raise PermissionDenied
        if request.POST.get('revoke'):
            item=get_object_or_404(FeatureRestriction,pk=request.POST['revoke'])
            User.objects.select_for_update().get(pk=item.regent_id)
            item.refresh_from_db()
            if item.revoked_at is None:
                item.revoked_at=timezone.now(); item.revoked_by=u; item.save(update_fields=['revoked_at','revoked_by'])
                Audit.objects.create(actor=u,action=f'Restricción {item.pk} levantada')
            return redirect('restrictions')
        if form.is_valid():
            data=form.cleaned_data
            User.objects.select_for_update().get(pk=data['regent'].pk)
            item=FeatureRestriction.objects.create(**data,created_by=u)
            Audit.objects.create(actor=u,action=f'Restricción {item.pk} creada')
            return redirect('restrictions')
    from django.core.paginator import Paginator
    rows=FeatureRestriction.objects.all() if u.role=='admin' else FeatureRestriction.objects.filter(regent=u)
    response=render(request,'restrictions.html',{'form':form,'rows':Paginator(rows.select_related('regent','created_by').order_by('-pk'),25).get_page(request.GET.get('page')),'now':timezone.now()},status=400 if request.method=='POST' else 200)
    response['Cache-Control']='private, no-store'
    return response
