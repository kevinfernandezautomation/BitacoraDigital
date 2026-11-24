from django.test import TestCase, override_settings
from django.core.exceptions import ValidationError
from .models import User,Regency,Sheet
@override_settings(ALLOW_UNSIGNED_CLOSE=True)
class Permissions(TestCase):
 def setUp(self):
  self.u=User.objects.create_user('r',role='regente'); self.e=User.objects.create_user('e',role='empresa'); self.r=Regency.objects.create(owner=self.u,company='Demo',hours=1,status='aprobada'); self.s=Sheet.objects.create(regency=self.r,date='2026-01-01',title='Visita',body='Demo')
 def test_isolation(self):
  self.client.force_login(self.e); self.assertEqual(self.client.get(f'/sheet/{self.s.pk}/').status_code,404)
 def test_close(self):
  self.client.force_login(self.u); self.client.post(f'/sheet/{self.s.pk}/action/',{'action':'close','confirm_close':'yes'}); self.s.refresh_from_db(); self.assertTrue(self.s.closed); self.s.body='Cambio'; self.assertRaises(ValidationError,self.s.save)
 def test_company_no_draft(self):
  self.r.members.add(self.e); self.client.force_login(self.e); self.assertEqual(self.client.get(f'/sheet/{self.s.pk}/').status_code,404)
