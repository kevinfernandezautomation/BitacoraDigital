from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from .models import User, FeatureRestriction
from .restrictions import active, enforce
from django.core.exceptions import PermissionDenied

class RestrictionTests(TestCase):
 def setUp(self):
  self.admin=User.objects.create_user('admin_r',role='admin')
  self.regent=User.objects.create_user('regent_r',role='regente')
 def test_granular(self):
  FeatureRestriction.objects.create(regent=self.regent,feature='create',reason='Morosidad',created_by=self.admin)
  with self.assertRaises(PermissionDenied): enforce(self.regent,'create')
  enforce(self.regent,'close')
 def test_expiration_and_revocation(self):
  r=FeatureRestriction.objects.create(regent=self.regent,feature='create',reason='QA',created_by=self.admin,ends=timezone.now()-timedelta(seconds=1))
  self.assertFalse(active(self.regent).exists())
  r.ends=None;r.revoked_at=timezone.now();r.save();self.assertFalse(active(self.regent).exists())
 def test_regent_cannot_create(self):
  self.client.force_login(self.regent)
  self.assertEqual(self.client.post('/restrictions/',{'regent':self.regent.pk,'feature':'create','reason':'QA'}).status_code,403)
 def test_admin_create(self):
  self.client.force_login(self.admin)
  self.assertEqual(self.client.post('/restrictions/',{'regent':self.regent.pk,'feature':'create','reason':'QA'}).status_code,302)
  self.assertTrue(active(self.regent).exists())
