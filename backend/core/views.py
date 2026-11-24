import hashlib,json
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import PermissionDenied,ValidationError
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse,HttpResponse
from django.shortcuts import render,get_object_or_404,redirect
from django.views.decorators.http import require_POST
from django.utils import timezone
from django import forms
from .models import *
from .forms import *
def scope(u):
 if u.role in ('admin','fiscalia'): return Regency.objects.all()
 if u.role=='regente': return Regency.objects.filter(owner=u)
 if u.role=='empresa': return Regency.objects.filter(members=u)
 return Regency.objects.none()
def sheets(u):
 q=Sheet.objects.filter(regency__in=scope(u))
 if u.role in ("admin","fiscalia"): return q.filter(closed=True)
 q=q.filter(Q(closed=True)|Q(regency__status="aprobada"))
 return q if u.role=='regente' else q.filter(closed=True)
def audit(u,action): Audit.objects.create(actor=u,action=action)
def owner(u,r):
 if u.role!='regente' or r.owner_id!=u.id or u.suspended or r.status!='aprobada': raise PermissionDenied
@login_required
def home(request):
 q=sheets(request.user); term=request.GET.get('q',''); q=q.filter(Q(title__icontains=term)|Q(tags__icontains=term)|Q(people__icontains=term)|Q(body__icontains=term))
 from .drafts import filter_sheets
 q=filter_sheets(q,request.GET)
 return render(request,'home.html',{'regencies':scope(request.user),'sheets':q,'tasks':Task.objects.filter(assignee=request.user,sheet__in=sheets(request.user))})
def formpage(request,form,title): return render(request,'form.html',{'form':form,'title':title})
# Regency workflow is implemented in regency.py.
from .regency import new_regency, approve, review_regency, revise_regency
@login_required
@transaction.atomic
def edit(request,rid,pk=None):
 from .restrictions import enforce
 User.objects.select_for_update().get(pk=request.user.pk)
 enforce(request.user,"edit" if pk else "create")
 r=get_object_or_404(scope(request.user).select_for_update(),pk=rid); owner(request.user,r)
 s=get_object_or_404(Sheet.objects.select_for_update(),pk=pk,regency=r,closed=False) if pk else Sheet(regency=r)
 f=SheetForm(request.POST or None,instance=s)
 if request.method=='POST' and f.is_valid():
  s=f.save(commit=False); s.revision=(s.revision or 0)+1; s.save(); audit(request.user,'Borrador '+str(s.pk)); return redirect('detail',pk=s.pk)
 return render(request,'sheet_form.html',{'form':f,'title':'Hoja de bitácora'})
@login_required
def detail(request,pk):
 s=get_object_or_404(sheets(request.user),pk=pk)
 from .comments import context
 from .tasks import context as task_context
 return render(request,'detail.html',{'s':s,**({**context(request,s),**task_context(request,s)} if s.closed else {}),'members':User.objects.filter(Q(pk=s.regency.owner_id)|Q(memberships=s.regency)|Q(role__in=['admin','fiscalia'])).distinct()})
@login_required
@require_POST
@transaction.atomic
def action(request,pk):
 User.objects.select_for_update().get(pk=request.user.pk)
 s=get_object_or_404(sheets(request.user).select_for_update(),pk=pk); u=request.user; a=request.POST.get('action'); body=request.POST.get('body','').strip()
 from .restrictions import enforce
 feature={'attach':'edit','remove_attachment':'edit','delete_draft':'edit','close':'close','comment':'comment','task':'task'}.get(a)
 if feature: enforce(u,feature)
 if len(body)>20000: return HttpResponse('Texto demasiado largo',status=400)
 if a in ('attach','close','remove_attachment','delete_draft'):
  owner(u,s.regency)
  if s.closed: raise PermissionDenied
  if a=='delete_draft':
   if s.attachments.exists(): return HttpResponse('Retire los adjuntos primero',status=409)
   s.delete(); audit(u,'Borrador eliminado '+str(pk)); return redirect('/')
  if a=='remove_attachment':
   attachment=get_object_or_404(s.attachments,pk=request.POST.get('attachment')); attachment.delete()
  elif a=='attach':
   from .drafts import validate_upload
   f=request.FILES.get('file')
   try: digest=validate_upload(f,s)
   except ValidationError as exc: return HttpResponse(exc.messages[0],status=400)
   Attachment.objects.create(sheet=s,file=f,digest=digest,original_name=f.name)
  else:
   if request.POST.get("confirm_close")!="yes": return HttpResponse("Confirme el cierre",status=400)
   from django.conf import settings
   if not settings.ALLOW_UNSIGNED_CLOSE: return HttpResponse('Firma certificada no configurada; cierre bloqueado',status=503)
   from .closure import close_sheet
   import subprocess
   try: close_sheet(s,u)
   except ValidationError as exc: return HttpResponse(exc.messages[0],status=409)
   except (OSError,subprocess.SubprocessError): return HttpResponse('Archivo o firma no disponible; cierre cancelado',status=503)
 elif not s.closed: raise PermissionDenied
 elif a=='comment':
  from .comments import publish
  return publish(request,s)
 elif a=='receipt' and u.role=='empresa': Receipt.objects.get_or_create(sheet=s,author=u)
 elif a=='task':
  from .tasks import assign
  return assign(request,s)
 elif a=='status':
  from .tasks import change
  return change(request,s)
 else: raise PermissionDenied
 audit(u,a+' hoja '+str(pk)); return redirect('detail',pk=pk)
@login_required
def download(request,pk):
 a=get_object_or_404(Attachment,sheet__in=sheets(request.user),pk=pk)
 if a.sheet.closed:
  from .closure import sha
  f=get_object_or_404(ArchivedFile,archive__sheet=a.sheet,source_id=a.pk)
  if sha(bytes(f.content))!=f.digest: return HttpResponse('Adjunto alterado',status=409)
  import io
  response=FileResponse(io.BytesIO(bytes(f.content)),as_attachment=True,filename=f.name or 'adjunto',content_type='application/octet-stream'); response['Cache-Control']='private, no-store'; return response
 response=FileResponse(a.file.open('rb'),as_attachment=True,filename=a.original_name or 'adjunto',content_type='application/octet-stream'); response['Cache-Control']='private, no-store'; return response
@login_required
def evaluation(request,pk):
 r=get_object_or_404(scope(request.user),pk=pk)
 if request.user.role=='empresa': raise PermissionDenied
 if not r.evaluation: return HttpResponse('Sin documento',status=404)
 response=FileResponse(r.evaluation.open('rb'),as_attachment=True,filename='evaluacion.pdf',content_type='application/octet-stream'); response['Cache-Control']='private, no-store'; return response
@login_required
def users(request):
 u=request.user
 if u.role not in ('admin','regente'): raise PermissionDenied
 class F(forms.Form):
  username=forms.CharField(); password=forms.CharField(widget=forms.PasswordInput); role=forms.ChoiceField(choices=[(x,x) for x in (['regente','admin','fiscalia','soporte'] if u.role=='admin' else ['empresa'])]); regency=forms.ModelChoiceField(queryset=scope(u),required=u.role=='regente')
 f=F(request.POST or None)
 if request.method=='POST' and f.is_valid():
  d=f.cleaned_data
  try:
   validate_password(d['password'], user=User(username=d['username']));
   if User.objects.filter(username=d['username']).exists(): raise ValidationError('Usuario existente')
   new=User.objects.create_user(username=d['username'],password=d['password'],role=d['role']);
   if u.role=='regente': d['regency'].members.add(new)
   audit(u,'Alta usuario '+new.username); return redirect('/')
  except ValidationError as e: f.add_error('password',e)
 return formpage(request,f,'Crear usuario')
@login_required
@require_POST
def suspend(request,pk):
 if request.user.role!='admin': raise PermissionDenied
 u=get_object_or_404(User,pk=pk,role='regente'); u.suspended=not u.suspended; u.save(); audit(request.user,'Suspensión '+u.username); return redirect('/')
@login_required
def api(request):
 from django.http import JsonResponse
 return JsonResponse({'hojas':list(sheets(request.user).values('id','title','date','closed','digest'))})
