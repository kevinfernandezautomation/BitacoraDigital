from django.test import TestCase, Client, override_settings
from django.utils import timezone
from datetime import timedelta
from .models import User, Regency, Sheet, Task, TaskEvent, ClosedArchive

@override_settings(ALLOW_UNSIGNED_CLOSE=True,SECURE_SSL_REDIRECT=False)
class TaskTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user('owner',role='regente')
        self.member=User.objects.create_user('member',role='empresa')
        self.other=User.objects.create_user('other',role='empresa')
        self.reg=Regency.objects.create(owner=self.owner,company='QA',hours=1,status='aprobada')
        self.reg.members.add(self.member)
        self.sheet=Sheet.objects.create(regency=self.reg,date=timezone.localdate(),title='QA',body='Original')
        self.url=f'/sheet/{self.sheet.pk}/action/'
        self.client.force_login(self.owner)
    def close(self):
        self.assertEqual(self.client.post(self.url,{'action':'close','confirm_close':'yes'}).status_code,302)
    def assign(self,**kw):
        return self.client.post(self.url,{'action':'task','body':'Ordenar bodega','assignee':self.member.pk,'due':timezone.localdate().isoformat(),**kw})
    def test_workflow_integrity(self):
        self.close(); archive=ClosedArchive.objects.get(sheet=self.sheet); before=(archive.manifest,archive.digest,bytes(archive.signature))
        self.assertEqual(self.assign().status_code,302); t=Task.objects.get()
        self.client.force_login(self.member)
        self.assertContains(self.client.get('/tasks/'),'Ordenar bodega')
        for old,new in [('Pendiente','En progreso'),('En progreso','Realizada')]:
            self.assertEqual(self.client.post(self.url,{'action':'status','task':t.pk,'previous':old,'status':new}).status_code,302)
        t.refresh_from_db(); self.assertEqual(t.status,'Realizada'); self.assertEqual(TaskEvent.objects.count(),3)
        archive.refresh_from_db(); self.assertEqual(before,(archive.manifest,archive.digest,bytes(archive.signature)))
    def test_draft(self):
        self.assertEqual(self.assign().status_code,403)
    def test_invalid(self):
        self.close()
        for data in [{'body':' '},{'body':'x'*4001},{'assignee':self.other.pk},{'assignee':self.owner.pk},{'due':(timezone.localdate()-timedelta(days=1)).isoformat()}]:
            self.assertEqual(self.assign(**data).status_code,400)
        self.assertFalse(Task.objects.exists())
    def test_outsider(self):
        self.close(); self.client.force_login(self.other); self.assertEqual(self.assign().status_code,404)
    def test_company_assigns(self):
        self.close(); self.client.force_login(self.member); self.assertEqual(self.assign(assignee=self.owner.pk).status_code,302)
    def test_stale_and_unauthorized(self):
        self.close(); self.assign(); t=Task.objects.get(); data={'action':'status','task':t.pk,'previous':'Pendiente','status':'Realizada'}
        self.assertEqual(self.client.post(self.url,data).status_code,302); self.assertEqual(self.client.post(self.url,data).status_code,409)
        admin=User.objects.create_user('admin',role='admin'); self.client.force_login(admin); self.assertEqual(self.client.post(self.url,data).status_code,403)
    def test_csrf(self):
        self.close(); c=Client(enforce_csrf_checks=True); c.force_login(self.owner); self.assertEqual(c.post(self.url,{'action':'task'}).status_code,403)
