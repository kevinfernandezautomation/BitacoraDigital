from django.test import TestCase, Client, override_settings
from .models import User, Regency, Sheet, Comment, ClosedArchive
from .closure import verify_archive

@override_settings(ALLOW_UNSIGNED_CLOSE=True, SECURE_SSL_REDIRECT=False)
class CommentTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user('owner',role='regente')
        self.reg=Regency.objects.create(owner=self.owner,company='QA',hours=1,status='aprobada')
        self.sheet=Sheet.objects.create(regency=self.reg,date='2026-01-01',title='QA',body='Original')
        self.url=f'/sheet/{self.sheet.pk}/'
        self.client.force_login(self.owner)
    def close(self):
        self.assertEqual(self.client.post(self.url+'action/',{'action':'close','confirm_close':'yes'}).status_code,302)
    def post(self,body):
        return self.client.post(self.url+'action/',{'action':'comment','body':body})
    def test_roles_and_integrity(self):
        self.close(); a=ClosedArchive.objects.get(sheet=self.sheet); original=(a.manifest,a.digest,bytes(a.signature))
        for role in ('regente','empresa','admin','fiscalia'):
            u=self.owner if role=='regente' else User.objects.create_user(role,role=role)
            if role=='empresa': self.reg.members.add(u)
            self.client.force_login(u); self.assertEqual(self.post('Nota '+role).status_code,302)
        a.refresh_from_db(); self.assertEqual(original,(a.manifest,a.digest,bytes(a.signature))); self.assertTrue(verify_archive(a)); self.assertEqual(Comment.objects.count(),4)
    def test_draft(self):
        self.assertEqual(self.post('Nota').status_code,403); self.assertFalse(Comment.objects.exists())
    def test_validation(self):
        self.close()
        for text in ('','   ','x'*4001): self.assertEqual(self.post(text).status_code,400)
        self.assertEqual(self.post('x'*4000).status_code,302)
    def test_unauthorized(self):
        self.close()
        for role in ('empresa','regente','soporte'):
            self.client.force_login(User.objects.create_user(role,role=role)); self.assertEqual(self.post('Nota').status_code,404)
    def test_xss(self):
        self.close(); self.post('<script>alert(1)</script>'); self.assertContains(self.client.get(self.url),'&lt;script&gt;alert(1)&lt;/script&gt;')
    def test_csrf(self):
        self.close(); c=Client(enforce_csrf_checks=True); c.force_login(self.owner); self.assertEqual(c.post(self.url+'action/',{'action':'comment','body':'Nota'}).status_code,403)
    def test_pagination(self):
        self.close()
        for i in range(26): self.post('Nota '+str(i))
        self.assertEqual(len(self.client.get(self.url).context['comments_page']),25)
        self.assertEqual(len(self.client.get(self.url+'?comments_page=2').context['comments_page']),1)
