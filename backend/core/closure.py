"""Transactional archive and detached CMS signature (development certificate only)."""
import hashlib, json, io, zipfile, subprocess, tempfile
from pathlib import Path
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import ClosedArchive, ArchivedFile

def sha(data): return hashlib.sha256(data).hexdigest()

def cms(data, signature=None):
    # A server certificate is NOT the regent's certified personal signature.
    with tempfile.TemporaryDirectory() as directory:
        p=Path(directory); (p/'manifest').write_bytes(data)
        if signature is None:
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(p/'key'),'-out',str(p/'cert'),'-days','1','-subj','/CN=CIQPA QA ONLY'],check=True,capture_output=True,timeout=15)
            subprocess.run(['openssl','cms','-sign','-binary','-in',str(p/'manifest'),'-signer',str(p/'cert'),'-inkey',str(p/'key'),'-outform','DER','-out',str(p/'sig'),'-md','sha256'],check=True,capture_output=True,timeout=15)
            return (p/'sig').read_bytes()
        (p/'sig').write_bytes(signature)
        return subprocess.run(['openssl','cms','-verify','-binary','-inform','DER','-in',str(p/'sig'),'-content',str(p/'manifest'),'-noverify','-out',str(p/'verified')],capture_output=True,timeout=15).returncode==0

@transaction.atomic
def close_sheet(s,user):
    if not settings.ALLOW_UNSIGNED_CLOSE: raise ValidationError('Firma personal certificada no integrada; cierre bloqueado')
    now=timezone.now(); files=[]; total=0
    for a in s.attachments.order_by('pk'):
        with a.file.open('rb') as f: data=f.read(25*1024*1024+1)
        total+=len(data)
        if total>25*1024*1024 or sha(data)!=a.digest: raise ValidationError('Integridad o tamaño de adjuntos incorrecto')
        files.append((a,data))
    manifest={'version':1,'id':s.pk,'regency':s.regency_id,'date':str(s.date),'title':s.title,'body':s.body,'commitments':s.commitments,'reference':s.reference_id,'people':s.people,'tags':s.tags,'revision':s.revision,'closed_at':now.isoformat(),'regent_id':user.pk,'signature_mode':'qa-self-signed','attachments':[{'id':a.pk,'name':a.original_name,'size':len(data),'sha256':sha(data)} for a,data in files]}
    raw=json.dumps(manifest,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    sig=cms(raw)
    if not cms(raw,sig): raise ValidationError('Firma de prueba inválida')
    archive=ClosedArchive.objects.create(sheet=s,manifest=raw.decode(),digest=sha(raw),signature=sig)
    for a,data in files: ArchivedFile.objects.create(archive=archive,source_id=a.pk,name=a.original_name,digest=sha(data),content=data)
    s.snapshot=raw.decode(); s.digest=sha(raw); s.closed=True; s.closed_at=now; s.save()

def verify_archive(a):
    try:
        raw=a.manifest.encode(); manifest=json.loads(raw)
        actual=[{'id':f.source_id,'name':f.name,'size':len(f.content),'sha256':sha(bytes(f.content))} for f in a.files.order_by('source_id')]
        return sha(raw)==a.digest==a.sheet.digest and a.manifest==a.sheet.snapshot and actual==manifest['attachments'] and cms(raw,bytes(a.signature))
    except (ValueError,OSError,KeyError,subprocess.SubprocessError): return False

def package(a):
    out=io.BytesIO()
    with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
        z.writestr('manifest.json',a.manifest); z.writestr('signature.p7s',bytes(a.signature))
        for f in a.files.all(): z.writestr(f'attachments/{f.source_id}.bin',bytes(f.content))
        z.writestr('README.txt','Firma CMS autofirmada de QA; no certificada. Nombres originales en manifest.json.')
    return out.getvalue()
