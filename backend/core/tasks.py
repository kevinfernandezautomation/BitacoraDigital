"""Independent task workflow; never writes to Sheet or ClosedArchive."""
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .models import User, Task, TaskEvent, Audit

STATES = ('Pendiente', 'En progreso', 'Realizada', 'Suspendida')
TRANSITIONS = {'Pendiente': ('En progreso','Realizada','Suspendida'), 'En progreso': ('Realizada','Suspendida'), 'Suspendida': ('Pendiente',), 'Realizada': ()}

def eligible(sheet):
    return User.objects.filter(is_active=True,suspended=False).filter(Q(pk=sheet.regency.owner_id,role='regente')|Q(memberships=sheet.regency,role='empresa')|Q(role__in=['admin','fiscalia'])).distinct().order_by('username')

def allowed(user,sheet):
    return sheet.closed and eligible(sheet).filter(pk=user.pk).exists()

class AssignmentForm(forms.Form):
    body=forms.CharField(label='Descripción de la tarea',max_length=4000,widget=forms.Textarea(attrs={'rows':4}))
    assignee=forms.ModelChoiceField(label='Responsable',queryset=User.objects.none())
    due=forms.DateField(label='Fecha límite',widget=forms.DateInput(attrs={'type':'date'}))
    def __init__(self,sheet,user,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['assignee'].queryset=eligible(sheet).exclude(pk=user.pk)
    def clean_due(self):
        due=self.cleaned_data['due']
        if due<timezone.localdate(): raise forms.ValidationError('La fecha no puede ser anterior a hoy.')
        return due

def context(request,sheet):
    return {'assignment_form':AssignmentForm(sheet,request.user) if allowed(request.user,sheet) else None,
            'sheet_tasks':Paginator(Task.objects.filter(sheet=sheet).select_related('assignee','creator').order_by('-pk'),25).get_page(request.GET.get('tasks_page'))}

def event(task,user,old,new):
    TaskEvent.objects.create(task=task,actor=user,previous=old,current=new)
    Audit.objects.create(actor=user,action=f'Tarea {task.pk}: {old} -> {new}')

@transaction.atomic
def assign(request,sheet):
    if not allowed(request.user,sheet): raise PermissionDenied
    form=AssignmentForm(sheet,request.user,request.POST)
    if not form.is_valid():
        from .comments import context as comments_context
        return render(request,'detail.html',{'s':sheet,**comments_context(request,sheet),**context(request,sheet),'assignment_form':form},status=400)
    task=Task.objects.create(sheet=sheet,creator=request.user,**form.cleaned_data)
    event(task,request.user,'','Pendiente')
    return redirect('detail',pk=sheet.pk)

@transaction.atomic
def change(request,sheet):
    if not allowed(request.user,sheet): raise PermissionDenied
    task_id=request.POST.get('task','')
    if not task_id.isdecimal() or len(task_id)>18: return HttpResponse('Identificador inválido',status=400)
    task=get_object_or_404(Task.objects.select_for_update(),sheet=sheet,pk=task_id)
    if request.user.pk not in (task.creator_id,task.assignee_id): raise PermissionDenied
    new=request.POST.get('status'); old=task.status
    if request.POST.get('previous')!=old or new not in TRANSITIONS.get(old,()): return HttpResponse('Transición inválida o desactualizada',status=409)
    task.status=new; task.save(update_fields=['status']); event(task,request.user,old,new)
    return redirect('detail',pk=sheet.pk)

@login_required
def dashboard(request):
    from .views import sheets
    q=Task.objects.filter(assignee=request.user,sheet__in=sheets(request.user),sheet__closed=True).select_related('sheet','creator','assignee')
    counts={s:q.filter(status=s).count() for s in STATES}
    overdue=q.filter(due__lt=timezone.localdate(),status__in=['Pendiente','En progreso']).count()
    status=request.GET.get('status','')
    if status in STATES: q=q.filter(status=status)
    if request.GET.get('overdue')=='1': q=q.filter(due__lt=timezone.localdate(),status__in=['Pendiente','En progreso'])
    return render(request,'tasks_dashboard.html',{'tasks_page':Paginator(q.order_by('due','pk'),25).get_page(request.GET.get('page')),'counts':counts,'overdue':overdue,'states':STATES,'status':status})
