from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import User,Regency,Sheet,ClosedArchive
from .closure import verify_archive
@override_settings(ALLOW_UNSIGNED_CLOSE=True,SECURE_SSL_REDIRECT=False)
class ClosureTests(TestCase):
 def setUp(self):
  self.u=User.objects.create_user('reg',role='regente'); self.r=Regency.objects.create(owner=self.u,company='QA',hours=1,status='aprobada'); self.s=Sheet.objects.create(regency=self.r,date='2026-01-01',title='QA',body='Original'); self.client.force_login(self.u); self.url=f'/sheet/{self.s.pk}/'
 def close(self): return self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'})
 def test_archive(self):
  self.assertEqual(self.close().status_code,302); a=ClosedArchive.objects.get(sheet=self.s); self.assertTrue(verify_archive(a)); self.assertEqual(self.client.get(self.url+'archive/').status_code,200)
 def test_double_close(self):
  self.close(); self.assertEqual(self.close().status_code,403); self.assertEqual(ClosedArchive.objects.count(),1)
 def test_unauthorized(self):
  self.client.force_login(User.objects.create_user('other',role='regente')); self.assertEqual(self.close().status_code,404); self.assertFalse(ClosedArchive.objects.exists())
 @override_settings(ALLOW_UNSIGNED_CLOSE=False)
 def test_fail_closed(self):
  self.assertEqual(self.close().status_code,503); self.s.refresh_from_db(); self.assertFalse(self.s.closed)
