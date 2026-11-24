from django.test import TestCase, override_settings
from django.urls import reverse
from .models import User, Regency, Sheet, Audit
from django.core.files.uploadedfile import SimpleUploadedFile

@override_settings(ALLOW_UNSIGNED_CLOSE=True, SECURE_SSL_REDIRECT=False)
class EnterpriseTests(TestCase):
    def setUp(self):
        self.users={r:User.objects.create_user(r,role=r) for r in ('regente','empresa','admin','fiscalia','soporte')}
        self.r=Regency.objects.create(owner=self.users['regente'],company='Empresa A',hours=2,status='aprobada')
        self.r.members.add(self.users['empresa'])
        self.s=Sheet.objects.create(regency=self.r,date='2026-01-01',title='Visita',body='Texto')
        self.url=f'/sheet/{self.s.pk}/'
    def login(self,r): self.client.force_login(self.users[r])
    def close(self):
        self.login('regente'); self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'})
    def test_draft_roles(self):
        for role in self.users:
            with self.subTest(role=role):
                self.login(role); self.assertEqual(self.client.get(self.url).status_code,200 if role=='regente' else 404)
    def test_closed_roles(self):
        self.close()
        for role in self.users:
            with self.subTest(role=role):
                self.login(role); self.assertEqual(self.client.get(self.url).status_code,404 if role=='soporte' else 200)
    def test_reports_roles(self):
        for role in self.users:
            with self.subTest(role=role):
                self.login(role); self.assertEqual(self.client.get('/reports/').status_code,200 if role in ('admin','fiscalia') else 403)
    def test_audit_roles(self):
        for role in self.users:
            with self.subTest(role=role):
                self.login(role); self.assertEqual(self.client.get('/audit/').status_code,200 if role=='admin' else 403)
    def test_integrity(self):
        self.close(); self.assertTrue(self.client.get(self.url+'integrity/').json()['integrity'])
    def test_company_cannot_close(self):
        self.login('empresa'); self.assertEqual(self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'}).status_code,404)
    def test_closed_cannot_edit(self):
        self.close(); self.assertEqual(self.client.get(f'/regency/{self.r.pk}/edit/{self.s.pk}/').status_code,404)
    def test_receipt_idempotent(self):
        self.close(); self.login('empresa')
        for _ in range(2): self.client.post(self.url+'action/',{'action':'receipt'})
        self.assertEqual(self.s.receipt_set.count(),1)
    def test_comments_do_not_change_digest(self):
        self.close(); self.s.refresh_from_db(); digest=self.s.digest; self.login('empresa'); self.client.post(self.url+'action/',{'action':'comment','body':'Observación'}); self.s.refresh_from_db(); self.assertEqual(self.s.digest,digest)
    def test_empty_attachment(self):
        self.login('regente'); self.assertEqual(self.client.post(self.url+'action/',{'action':'attach','file':SimpleUploadedFile('a.txt',b'')}).status_code,400)
    def test_suspended_owner(self):
        u=self.users['regente']; u.suspended=True; u.save(); self.login('regente'); self.assertEqual(self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'}).status_code,403)
    @override_settings(ALLOW_UNSIGNED_CLOSE=False)
    def test_production_blocks_unsigned(self):
        self.login('regente'); self.assertEqual(self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'}).status_code,503)
    def test_health(self): self.assertEqual(self.client.get('/health/').status_code,200)
    def test_unauthenticated(self): self.assertEqual(self.client.get('/reports/').status_code,302)
