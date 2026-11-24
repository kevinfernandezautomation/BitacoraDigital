import csv
from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncMonth
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_safe
from django.views.decorators.cache import never_cache
from .models import Regency, Sheet

class Filters(forms.Form):
    start = forms.DateField(label='Desde', required=False, widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    end = forms.DateField(label='Hasta', required=False, widget=forms.DateInput(attrs={'type':'date'},format='%Y-%m-%d'))
    company = forms.CharField(label='Empresa',required=False,max_length=200)
    regent = forms.CharField(label='Regente (usuario)',required=False,max_length=150)
    status = forms.ChoiceField(label='Estado de regencia',required=False,choices=[('','Todos')]+list(Regency._meta.get_field('status').choices))
    def clean(self):
        d=super().clean()
        if d.get('start') and d.get('end') and d['start']>d['end']:
            raise forms.ValidationError('La fecha inicial debe ser anterior o igual a la final.')
        return d

class Echo:
    def write(self,value): return value

def safe_cell(value):
    text=str(value or '')
    return "'"+text if text.lstrip().startswith(('=','+','-','@')) or text.startswith(('\t','\r','\n')) else text

@login_required
@require_safe
@never_cache
def reports(request):
    if request.user.role not in ('admin','fiscalia'): raise PermissionDenied
    f=Filters(request.GET)
    if not f.is_valid(): return render(request,'reports.html',{'form':f},status=400)
    d=f.cleaned_data
    reg=Regency.objects.all()
    if d['company']: reg=reg.filter(company__icontains=d['company'])
    if d['regent']: reg=reg.filter(owner__username__icontains=d['regent'])
    if d['status']: reg=reg.filter(status=d['status'])
    criteria=Q(sheet__closed=True)
    closed=Sheet.objects.filter(closed=True,regency__in=reg)
    for field,lookup in [('start','gte'),('end','lte')]:
        if d[field]:
            criteria &= Q(**{'sheet__date__'+lookup:d[field]})
            closed=closed.filter(**{'date__'+lookup:d[field]})
    rows=reg.select_related('owner').annotate(visits=Count('sheet__date',filter=criteria,distinct=True),leaves=Count('sheet',filter=criteria),last_visit=Max('sheet__date',filter=criteria)).order_by('company','pk')
    if request.GET.get('format')=='csv':
        if rows.count()>100000: return HttpResponse('Acote los filtros para exportar.',status=400)
        writer=csv.writer(Echo())
        def stream():
            yield '\ufeff'+writer.writerow(['Regencia','Empresa','Regente','Estado','Días con visita','Hojas cerradas','Última fecha'])
            for r in rows.iterator(chunk_size=1000):
                yield writer.writerow([r.pk,safe_cell(r.company),safe_cell(r.owner.username),r.status,r.visits,r.leaves,r.last_visit or ''])
        response=StreamingHttpResponse(stream(),content_type='text/csv; charset=utf-8')
        response['Content-Disposition']='attachment; filename="fiscalizacion.csv"'
        return response
    months=list(closed.annotate(month=TruncMonth('date')).values('month').annotate(total=Count('pk')).order_by('-month')[:24]); months.reverse()
    params=request.GET.copy(); params.pop('page',None); params.pop('sheet_page',None); params.pop('format',None)
    return render(request,'reports.html',{'form':f,'rows':Paginator(rows,25).get_page(request.GET.get('page')),'closed':Paginator(closed.select_related('regency','regency__owner').defer('body','snapshot','commitments').order_by('-date','-pk'),25).get_page(request.GET.get('sheet_page')),'total':reg.count(),'approved':reg.filter(status='aprobada').count(),'no_visits':rows.filter(visits=0).count(),'leaves':closed.count(),'months':months,'query':params.urlencode()})
