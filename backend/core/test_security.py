from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import identify_hasher
from .models import Regency, Sheet, Audit
from datetime import date

class SecurityTests(TestCase):
    def setUp(self):
        U = get_user_model()
        self.old = 'Long-Original!2026'
        self.new = 'Different-Secret!2027'
        self.regent = U.objects.create_user(username='regent', role='regente', password=self.old)
        self.member = U.objects.create_user(username='company', role='empresa', password=self.old)
        self.regency = Regency.objects.create(owner=self.regent, company='Example', hours=1, status='aprobada')
        self.regency.members.add(self.member)
        self.sheet = Sheet.objects.create(regency=self.regency, date=date.today(), title='Historical', closed=True)
    def test_password_change_preserves_other_user_access(self):
        other = Client(); other.force_login(self.member)
        stale = Client(); stale.force_login(self.regent)
        self.client.force_login(self.regent)
        response = self.client.post('/password/', {'old_password':self.old,'new_password1':self.new,'new_password2':self.new}, secure=True)
        self.assertRedirects(response, '/security/', fetch_redirect_response=False)
        self.regent.refresh_from_db(); self.member.refresh_from_db()
        self.assertTrue(self.regent.check_password(self.new))
        self.assertTrue(self.member.check_password(self.old))
        self.assertEqual(identify_hasher(self.regent.password).algorithm, 'argon2')
        self.assertEqual(other.get(f'/sheet/{self.sheet.pk}/', secure=True).status_code, 200)
        self.assertEqual(stale.get('/security/', secure=True).status_code, 302)
        self.assertEqual(self.client.get('/security/', secure=True).status_code, 200)
        self.assertTrue(Audit.objects.filter(actor=self.regent,action='Cambio de contraseña propia').exists())
    def test_wrong_password(self):
        self.client.force_login(self.regent)
        self.client.post('/password/', {'old_password':'wrong','new_password1':self.new,'new_password2':self.new}, secure=True)
        self.regent.refresh_from_db(); self.assertTrue(self.regent.check_password(self.old))
    def test_headers(self):
        self.client.force_login(self.regent)
        r=self.client.get('/security/', secure=True)
        self.assertIn("frame-ancestors 'none'",r['Content-Security-Policy'])
        self.assertIn('no-store',r['Cache-Control'])
    def test_csrf(self):
        c=Client(enforce_csrf_checks=True); c.force_login(self.regent)
        self.assertEqual(c.post('/password/',{},secure=True).status_code,403)
