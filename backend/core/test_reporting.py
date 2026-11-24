from django.test import TestCase, override_settings
from .models import User, Regency, Sheet
from .reporting import safe_cell

@override_settings(SECURE_SSL_REDIRECT=False)
class ReportingTests(TestCase):
    def setUp(self):
        self.users={r:User.objects.create_user(r,role=r) for r in ('admin','fiscalia','regente','empresa','soporte')}
        self.r=Regency.objects.create(owner=self.users['regente'],company='=Empresa',hours=2,status='aprobada')
        self.empty=Regency.objects.create(owner=self.users['regente'],company='Sin visitas',hours=2,status='aprobada')
        for date,closed in [('2026-01-01',True),('2026-01-01',True),('2026-02-01',True),('2026-01-02',False)]:
            Sheet.objects.create(regency=self.r,date=date,closed=closed,title='Histórica' if closed else 'Borrador secreto',body='Texto')
        self.client.force_login(self.users['admin'])
    def test_roles(self):
        for role,u in self.users.items():
            self.client.force_login(u)
            for suffix in ('','?format=csv'):
                self.assertEqual(self.client.get('/reports/'+suffix).status_code,200 if role in ('admin','fiscalia') else 403)
    def test_counts(self):
        r=self.client.get('/reports/?start=2026-01-01&end=2026-01-31')
        self.assertEqual(r.context['leaves'],2)
        self.assertEqual(r.context['no_visits'],1)
        row=next(x for x in r.context['rows'] if x.pk==self.r.pk)
        self.assertEqual((row.visits,row.leaves),(1,2))
        self.assertNotContains(r,'Borrador secreto')
    def test_invalid_dates(self):
        for query in ('start=invalid','start=2026-02-01&end=2026-01-01'):
            self.assertEqual(self.client.get('/reports/?'+query).status_code,400)
    def test_export(self):
        r=self.client.get('/reports/?format=csv&company=%3DEmpresa')
        text=b''.join(r.streaming_content).decode('utf-8-sig')
        self.assertIn("'=Empresa",text); self.assertNotIn('Sin visitas',text)
        self.assertEqual(safe_cell('  =1+1'),"'  =1+1")
    def test_history_after_suspension(self):
        self.r.status='suspendida';self.r.save()
        s=Sheet.objects.filter(regency=self.r,closed=True).first()
        self.assertEqual(self.client.get(f'/sheet/{s.pk}/').status_code,200)
    def test_read_only(self):
        s=Sheet.objects.filter(regency=self.r,closed=True).first()
        self.assertEqual(self.client.post('/reports/').status_code,405)
        for action in ('close','attach','delete_draft','remove_attachment'):
            self.assertEqual(self.client.post(f'/sheet/{s.pk}/action/',{'action':action}).status_code,403)
        self.assertEqual(self.client.get(f'/regency/{self.r.pk}/edit/{s.pk}/').status_code,403)
