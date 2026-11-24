import hashlib
from pathlib import Path
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.dateparse import parse_date
from django.core.paginator import Paginator
LIMIT=25*1024*1024

def validate_upload(f,sheet):
    if not f or not f.size or f.size>LIMIT: raise ValidationError('Archivo vacío o superior a 25 MiB')
    total=sum(a.file.size for a in sheet.attachments.all())
    if total+f.size>LIMIT: raise ValidationError('Máximo acumulado de 25 MiB por hoja')
    ext=Path(f.name).suffix.lower(); head=f.read(16); f.seek(0)
    valid=(ext=='.pdf' and head.startswith(b'%PDF-')) or (ext in ('.jpg','.jpeg') and head.startswith(b'\xff\xd8\xff')) or (ext=='.png' and head.startswith(b'\x89PNG\r\n\x1a\n'))
    if not valid: raise ValidationError('Formato permitido: PDF, JPEG o PNG con cabecera válida')
    h=hashlib.sha256()
    for chunk in f.chunks(): h.update(chunk)
    f.seek(0); return h.hexdigest()

def verify_files(sheet):
    try:
        for a in sheet.attachments.all():
            with a.file.open('rb') as f:
                if hashlib.file_digest(f,'sha256').hexdigest()!=a.digest: return False
        return True
    except OSError: return False

def filter_sheets(q,params):
    for field,lookup in [('people','people__icontains'),('tags','tags__icontains')]:
        if params.get(field): q=q.filter(**{lookup:params[field][:250]})
    for field,lookup in [('from','date__gte'),('to','date__lte')]:
        try: value=parse_date(params.get(field,''))
        except ValueError: value=None
        if value: q=q.filter(**{lookup:value})
    if params.get('state') in ('draft','closed'): q=q.filter(closed=params['state']=='closed')
    order={'old':'date','title':'title'}.get(params.get('order'),'-date')
    return Paginator(q.select_related('regency').order_by(order,'pk'),25).get_page(params.get('page'))
