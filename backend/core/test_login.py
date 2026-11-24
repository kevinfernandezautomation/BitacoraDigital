from django.test import TestCase, Client, override_settings
from django.contrib.auth import get_user_model
from .models import LoginEvent
@override_settings(SECURE_SSL_REDIRECT=False, SESSION_COOKIE_SECURE=False, CSRF_COOKIE_SECURE=False, LOGIN_PAIR_LIMIT=5, LOGIN_IP_LIMIT=60, LOGIN_WINDOW=300)
class LoginTests(TestCase):
 def setUp(self):
  self.password='Test-only-Long!2026'; self.user=get_user_model().objects.create_user(username='regente',password=self.password)
 def post(self,**kw): return self.client.post('/login/',{'username':'regente','password':self.password,**kw})
 def test_valid(self):
  self.assertRedirects(self.post(),'/'); self.assertEqual(LoginEvent.objects.get().outcome,'success')
 def test_invalid(self):
  self.assertContains(self.post(password='wrong'),'Usuario o contraseña incorrectos.'); self.assertNotIn('_auth_user_id',self.client.session)
 def test_inactive(self):
  self.user.is_active=False; self.user.save(); self.assertContains(self.post(),'Usuario o contraseña incorrectos.')
 def test_rate_limit(self):
  for _ in range(5): self.assertEqual(self.post(password='wrong').status_code,200)
  self.assertEqual(self.post().status_code,429)
 def test_external_redirect(self): self.assertRedirects(self.post(next='https://example.invalid/'),'/')
 def test_csrf(self): self.assertEqual(Client(enforce_csrf_checks=True).post('/login/',{'username':'regente','password':self.password}).status_code,403)
 def test_logout(self):
  self.post(); self.assertEqual(self.client.get('/logout/').status_code,405); self.client.post('/logout/'); self.assertNotIn('_auth_user_id',self.client.session)
 def test_anonymous(self): self.assertRedirects(self.client.get('/'),'/login/?next=/')
 def test_idle(self):
  self.post(); s=self.client.session; s['last_activity']=1; s.save(); self.assertRedirects(self.client.get('/'),'/login/')
