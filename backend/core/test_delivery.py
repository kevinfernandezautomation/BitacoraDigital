import uuid, io, zipfile
from unittest.mock import patch
from django.test import override_settings, Client
from django.core import mail
from . import test_closure
from .models import Delivery, User
@override_settings(SHEET_EMAIL_ENABLED=True,EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',DEBUG=True)
class DeliveryTests(test_closure.ClosureTests):
 def payload(self): return {'email':'external@example.org','confirm_email':'external@example.org','consent':'on','token':str(uuid.uuid4())}
 def test_delivery(self):
  self.close(); self.s.refresh_from_db(); before=self.s.digest; p=self.payload()
  self.assertEqual(self.client.post(self.url+'email/',p).status_code,302)
  self.assertEqual(Delivery.objects.get().status,'simulado'); self.assertEqual(mail.outbox[0].to,['external@example.org'])
  with zipfile.ZipFile(io.BytesIO(mail.outbox[0].attachments[0][1])) as z: self.assertIn('signature.p7s',z.namelist())
  self.s.refresh_from_db(); self.assertEqual(self.s.digest,before)
  self.assertEqual(self.client.post(self.url+'email/',p).status_code,409); self.assertEqual(len(mail.outbox),1)
 def test_draft(self): self.assertEqual(self.client.post(self.url+'email/',self.payload()).status_code,404)
 def test_roles(self):
  self.close()
  for role in ['admin','fiscalia','empresa','soporte','regente']:
   self.client.force_login(User.objects.create_user('other_'+role,role=role)); self.assertIn(self.client.post(self.url+'email/',self.payload()).status_code,[403,404])
 def test_invalid(self):
  self.close(); p=self.payload(); p['confirm_email']='different@example.org'; self.assertEqual(self.client.post(self.url+'email/',p).status_code,400)
  p=self.payload();p.pop('consent');self.assertEqual(self.client.post(self.url+'email/',p).status_code,400)
 def test_csrf(self):
  self.close(); c=Client(enforce_csrf_checks=True);c.force_login(self.u);self.assertEqual(c.post(self.url+'email/',self.payload()).status_code,403)
 def test_uncertain(self):
  self.close()
  with patch('core.delivery.EmailMessage.send',side_effect=TimeoutError): self.assertEqual(self.client.post(self.url+'email/',self.payload()).status_code,302)
  self.assertEqual(Delivery.objects.get().status,'incierto')
 @override_settings(SHEET_EMAIL_MAX_BYTES=1)
 def test_size(self):
  self.close();self.assertEqual(self.client.post(self.url+'email/',self.payload()).status_code,413)
 @override_settings(SHEET_EMAIL_HOURLY_LIMIT=1)
 def test_limit(self):
  self.close();self.client.post(self.url+'email/',self.payload());self.assertEqual(self.client.post(self.url+'email/',self.payload()).status_code,429)
 def test_legacy_route(self):
  self.close();self.assertEqual(self.client.post(self.url+'action/',{'action':'email','email':'external@example.org'}).status_code,403)
