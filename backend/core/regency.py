import hashlib
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST, require_http_methods, require_safe
from .models import Regency, Audit
from .forms import RegencyForm


def allowed(user):
    if user.role != 'regente' or user.suspended: raise PermissionDenied


def submit(request, instance=None):
    allowed(request.user)
    form=RegencyForm(request.POST if request.method=='POST' else None,request.FILES if request.method=='POST' else None,instance=instance)
    if request.method=='POST' and form.is_valid():
        r=form.save(commit=False)
        r.owner=request.user
        r.status='solicitada'
        r.submitted_at=timezone.now()
        r.reviewed_at=None
        r.reviewer=None
        r.review_note=''
        r.evaluation.open('rb')
        r.evaluation_digest=hashlib.file_digest(r.evaluation,'sha256').hexdigest()
        r.evaluation.seek(0)
        r.save()
        Audit.objects.create(actor=request.user,action=f'Solicitud regencia {r.pk}')
        return redirect('regency-review',pk=r.pk)
    return render(request,'regency_form.html',{'form':form})

@login_required
@require_http_methods(['GET','POST'])
@transaction.atomic
def new_regency(request):
    return submit(request)

@login_required
@require_http_methods(['GET','POST'])
@transaction.atomic
def revise_regency(request,pk):
    allowed(request.user)
    r=get_object_or_404(Regency.objects.select_for_update(),pk=pk,owner=request.user,status='observada')
    return submit(request,r)

@login_required
@require_safe
def review_regency(request,pk):
    u=request.user
    if u.role not in ('regente','admin','fiscalia'): raise PermissionDenied
    q=Regency.objects.select_related('owner','reviewer')
    if u.role=='regente': q=q.filter(owner=u)
    return render(request,'regency_review.html',{'r':get_object_or_404(q,pk=pk)})

@login_required
@require_POST
@transaction.atomic
def approve(request,pk):
    if request.user.role!='admin' or request.user.suspended: raise PermissionDenied
    r=get_object_or_404(Regency.objects.select_for_update(),pk=pk)
    if r.status!='solicitada': return HttpResponse('Estado incompatible',status=409)
    decision=request.POST.get('decision','')
    note=request.POST.get('note','').strip()
    if decision not in ('aprobada','rechazada','observada') or len(note)>2000 or (decision!='aprobada' and not note): return HttpResponse('Decisión u observación inválida',status=400)
    if decision=='aprobada':
        if request.POST.get('verified')!='yes': return HttpResponse('Confirme revisión de requisitos',status=400)
        if not all([r.company,r.company_id,r.establishment,r.address,r.contact,r.contact_email,r.contact_phone,r.kind,r.evaluation,r.evaluation_digest]) or not 1<=r.hours<=168: return HttpResponse('Solicitud incompleta',status=400)
        try:
            with r.evaluation.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=r.evaluation_digest: return HttpResponse('Integridad de evaluación inválida',status=409)
        except OSError: return HttpResponse('Evaluación no disponible',status=409)
    r.status=decision; r.review_note=note; r.reviewer=request.user; r.reviewed_at=timezone.now()
    r.save(update_fields=['status','review_note','reviewer','reviewed_at'])
    Audit.objects.create(actor=request.user,action=f'Regencia {r.pk}: {decision}')
    return redirect('regency-review',pk=pk)
