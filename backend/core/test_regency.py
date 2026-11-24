import tempfile
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import User, Regency, Audit

@override_settings(SECURE_SSL_REDIRECT=False)
class RegencyWorkflow(TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
  settings=override_settings(MEDIA_ROOT=self.tmp.name); settings.enable(); self.addCleanup(settings.disable)
  self.regent=User.objects.create_user('regent',role='regente'); self.admin=User.objects.create_user('admin',role='admin'); self.other=User.objects.create_user('other',role='regente')
  self.client.force_login(self.regent)
 def data(self,**kwargs):
  return dict(company='Empresa ficticia',company_id='TEST-1',establishment='Planta',address='San José',contact='Contacto',contact_email='qa@example.invalid',contact_phone='12345678',kind='Industrial',hours=10,evaluation=SimpleUploadedFile('test.pdf',b'%PDF-1.4\n%%EOF'),**kwargs)
 def create(self):
  self.assertEqual(self.client.post('/regency/new/',self.data()).status_code,302); return Regency.objects.get()
 def decision(self,r,**data): return self.client.post(f'/regency/{r.pk}/approve/',data)
 def test_flow(self):
  r=self.create(); self.assertEqual(self.client.get(f'/regency/{r.pk}/new/').status_code,403)
  self.client.force_login(self.admin); self.assertEqual(self.decision(r,decision='aprobada',verified='yes').status_code,302)
  r.refresh_from_db(); self.assertEqual(r.status,'aprobada'); self.assertEqual(r.reviewer,self.admin)
  self.assertEqual(self.decision(r,decision='aprobada',verified='yes').status_code,409)
  self.client.force_login(self.regent); self.assertEqual(self.client.get(f'/regency/{r.pk}/new/').status_code,200)
  self.assertEqual(Audit.objects.count(),2)
 def test_isolation(self):
  r=self.create(); self.client.force_login(self.other)
  for suffix in ['', 'evaluation/', 'new/']: self.assertEqual(self.client.get(f'/regency/{r.pk}/{suffix}').status_code,404)
  self.assertEqual(self.decision(r,decision='aprobada',verified='yes').status_code,403)
 def test_invalid(self):
  for field,value in [('hours',0),('hours',169),('contact_email','bad'),('company_id',''),('evaluation',SimpleUploadedFile('bad.pdf',b'not a pdf'))]:
   d=self.data(); d[field]=value; self.assertEqual(self.client.post('/regency/new/',d).status_code,200); self.assertFalse(Regency.objects.exists())
 def test_review_confirmation(self):
  r=self.create(); self.client.force_login(self.admin); self.assertEqual(self.decision(r,decision='aprobada').status_code,400)
 def test_observation(self):
  r=self.create(); self.client.force_login(self.admin); self.assertEqual(self.decision(r,decision='observada',note='Corregir').status_code,302)
  self.client.force_login(self.regent); self.assertEqual(self.client.post(f'/regency/{r.pk}/revise/',self.data()).status_code,302); r.refresh_from_db(); self.assertEqual(r.status,'solicitada')
