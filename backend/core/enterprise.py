import csv, hashlib, io
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse, JsonResponse
from django.db.models import Count, Q
from django.views.decorators.http import require_safe
from django.shortcuts import get_object_or_404, render
from .views import scope, sheets
from .models import Audit, Regency, Sheet

from .reporting import reports

@login_required
@require_safe
def audit_log(request):
    if request.user.role!='admin': raise PermissionDenied
    return render(request,'audit.html',{'events':Audit.objects.select_related('actor').order_by('-created')[:500]})

@login_required
@require_safe
def integrity(request,pk):
    s=get_object_or_404(sheets(request.user),pk=pk,closed=True)
    from .closure import verify_archive
    a=getattr(s,'archive',None)
    valid=bool(a and verify_archive(a))
    return JsonResponse({'integrity':valid,'certified_signature':False,'archive_present':bool(a)},status=200 if valid else 409)

@login_required
@require_safe
def archive_download(request,pk):
    from .closure import verify_archive,package
    s=get_object_or_404(sheets(request.user),pk=pk,closed=True)
    a=getattr(s,'archive',None)
    if not a or not verify_archive(a): return HttpResponse('Archivo no verificable',status=409)
    response=HttpResponse(package(a),content_type='application/zip')
    response['Content-Disposition']=f'attachment; filename="hoja-{pk}.zip"'
    response['Cache-Control']='private, no-store'
    return response

@require_safe
def health(request):
    from django.db import connection
    with connection.cursor() as c: c.execute('SELECT 1')
    return JsonResponse({'status':'ok'})
