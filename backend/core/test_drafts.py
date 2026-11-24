from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from .models import User, Regency, Sheet

@override_settings(ALLOW_UNSIGNED_CLOSE=True,SECURE_SSL_REDIRECT=False)
class DraftTests(TestCase):
 def setUp(self):
  self.u=User.objects.create_user('owner',role='regente'); self.e=User.objects.create_user('company',role='empresa'); self.r=Regency.objects.create(owner=self.u,company='QA',hours=2,status='aprobada'); self.r.members.add(self.e)
  self.s=Sheet.objects.create(regency=self.r,date='2026-01-01',title='QA',body='Original'); self.url=f'/sheet/{self.s.pk}/action/'; self.client.force_login(self.u)
 def post(self,action,**data): return self.client.post(self.url,{'action':action,**data})
 def test_confirmation(self): self.assertEqual(self.post('close').status_code,400)
 def test_closed_mutations(self):
  self.assertEqual(self.post('close',confirm_close='yes').status_code,302)
  for action in ('delete_draft','attach','remove_attachment','close'): self.assertEqual(self.post(action).status_code,403)
 def test_company_comment_only_closed(self):
  self.client.force_login(self.e); self.assertEqual(self.post('comment',body='Nota').status_code,404)
  self.client.force_login(self.u); self.post('close',confirm_close='yes'); self.client.force_login(self.e); self.assertEqual(self.post('comment',body='Nota').status_code,302); self.assertEqual(self.post('task',body='No').status_code,400)
 def test_invalid_attachment(self): self.assertEqual(self.post('attach',file=SimpleUploadedFile('fake.pdf',b'bad')).status_code,400)
 def test_stale_revision(self):
  self.s.revision=2; self.s.save(); response=self.client.post(f'/regency/{self.r.pk}/edit/{self.s.pk}/',{'date':'2026-01-01','title':'Changed','body':'Changed','revision':1}); self.assertContains(response,'El borrador cambió'); self.s.refresh_from_db(); self.assertEqual(self.s.body,'Original')
