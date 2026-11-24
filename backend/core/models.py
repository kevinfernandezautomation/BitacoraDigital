from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
class User(AbstractUser):
 role=models.CharField(max_length=15,choices=[(x,x) for x in ['regente','empresa','fiscalia','admin','soporte']],default='regente')
 suspended=models.BooleanField(default=False)
class Regency(models.Model):
 company_id=models.CharField(max_length=40,blank=True)
 establishment=models.CharField(max_length=200,blank=True)
 address=models.CharField(max_length=300,blank=True)
 contact_email=models.EmailField(blank=True)
 contact_phone=models.CharField(max_length=40,blank=True)
 additional_contacts=models.TextField(blank=True)
 submitted_at=models.DateTimeField(null=True)
 reviewed_at=models.DateTimeField(null=True)
 reviewer=models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT,related_name='reviewed_regencies')
 review_note=models.TextField(blank=True)
 evaluation_digest=models.CharField(max_length=64,blank=True)

 owner=models.ForeignKey(User,on_delete=models.PROTECT,related_name='regencies')
 company=models.CharField(max_length=200); contact=models.CharField(max_length=200); kind=models.CharField(max_length=100); hours=models.PositiveIntegerField(); evaluation=models.FileField(upload_to='evaluations/')
 status=models.CharField(max_length=15,default='solicitada',choices=[(x,x) for x in ['solicitada','aprobada','rechazada','suspendida','observada']])
 members=models.ManyToManyField(User,blank=True,related_name='memberships')
 def __str__(self): return self.company
class Sheet(models.Model):
 commitments=models.TextField(blank=True)
 reference=models.ForeignKey("self",null=True,blank=True,on_delete=models.PROTECT)
 revision=models.PositiveIntegerField(default=0)
 regency=models.ForeignKey(Regency,on_delete=models.PROTECT); date=models.DateField(); title=models.CharField(max_length=200); body=models.TextField(); people=models.CharField(max_length=250,blank=True); tags=models.CharField(max_length=250,blank=True)
 closed=models.BooleanField(default=False); digest=models.CharField(max_length=64,blank=True); closed_at=models.DateTimeField(null=True); snapshot=models.TextField(blank=True)
 def save(self,*a,**kw):
  if self.pk and Sheet.objects.filter(pk=self.pk,closed=True).exists(): raise ValidationError('Hoja inalterable')
  super().save(*a,**kw)
 def delete(self,*a,**kw):
  if self.closed: raise ValidationError('Hoja inalterable')
  return super().delete(*a,**kw)
class Attachment(models.Model):
 original_name=models.CharField(max_length=255,blank=True)
 sheet=models.ForeignKey(Sheet,on_delete=models.PROTECT,related_name='attachments'); file=models.FileField(upload_to='attachments/'); digest=models.CharField(max_length=64)
class Comment(models.Model):
 sheet=models.ForeignKey(Sheet,on_delete=models.PROTECT); author=models.ForeignKey(User,on_delete=models.PROTECT); body=models.TextField(); created=models.DateTimeField(auto_now_add=True)
class Receipt(models.Model):
 sheet=models.ForeignKey(Sheet,on_delete=models.PROTECT); author=models.ForeignKey(User,on_delete=models.PROTECT); created=models.DateTimeField(auto_now_add=True)
 class Meta: unique_together=('sheet','author')
class Task(models.Model):
 sheet=models.ForeignKey(Sheet,on_delete=models.PROTECT)
 assignee=models.ForeignKey(User,on_delete=models.PROTECT)
 creator=models.ForeignKey(User,null=True,blank=True,on_delete=models.PROTECT,related_name='assigned_tasks')
 body=models.TextField()
 due=models.DateField()
 status=models.CharField(max_length=15,default='Pendiente',choices=[(x,x) for x in ('Pendiente','En progreso','Realizada','Suspendida')])
 created=models.DateTimeField(auto_now_add=True)
 class Meta:
  indexes=[models.Index(fields=['assignee','status','due'])]
  constraints=[models.CheckConstraint(condition=models.Q(status__in=['Pendiente','En progreso','Realizada','Suspendida']),name='task_valid_status')]
 @property
 def overdue(self):
  from django.utils import timezone
  return self.due<timezone.localdate() and self.status in ('Pendiente','En progreso')
 @property
 def next_states(self):
  from .tasks import TRANSITIONS
  return TRANSITIONS.get(self.status,())
class TaskEvent(models.Model):
 task=models.ForeignKey(Task,on_delete=models.PROTECT,related_name='events')
 actor=models.ForeignKey(User,on_delete=models.PROTECT)
 previous=models.CharField(max_length=15,blank=True)
 current=models.CharField(max_length=15)
 created=models.DateTimeField(auto_now_add=True)
class Audit(models.Model):
 actor=models.ForeignKey(User,on_delete=models.PROTECT); action=models.CharField(max_length=250); created=models.DateTimeField(auto_now_add=True)

class LoginBucket(models.Model):
 key=models.CharField(max_length=64,primary_key=True)
 window=models.DateTimeField()
 count=models.PositiveIntegerField(default=0)

class LoginEvent(models.Model):
 identifier=models.CharField(max_length=64)
 outcome=models.CharField(max_length=20)
 created=models.DateTimeField(auto_now_add=True,db_index=True)

class ClosedArchive(models.Model):
 sheet=models.OneToOneField(Sheet,on_delete=models.PROTECT,related_name='archive')
 manifest=models.TextField()
 digest=models.CharField(max_length=64)
 signature=models.BinaryField()

class ArchivedFile(models.Model):
 archive=models.ForeignKey(ClosedArchive,on_delete=models.PROTECT,related_name='files')
 source_id=models.PositiveBigIntegerField()
 name=models.CharField(max_length=255)
 digest=models.CharField(max_length=64)
 content=models.BinaryField()
 class Meta:
  constraints=[models.UniqueConstraint(fields=['archive','source_id'],name='unique_archived_file')]

class Delivery(models.Model):
 id=models.UUIDField(primary_key=True,editable=False)
 sheet=models.ForeignKey(Sheet,on_delete=models.PROTECT)
 actor=models.ForeignKey(User,on_delete=models.PROTECT)
 recipient=models.EmailField(max_length=254)
 digest=models.CharField(max_length=64)
 status=models.CharField(max_length=15,default='registrado',choices=[(x,x) for x in ('registrado','aceptado','simulado','incierto')])
 created=models.DateTimeField(auto_now_add=True)
 finished=models.DateTimeField(null=True)
 class Meta:
  indexes=[models.Index(fields=['actor','created'])]
  constraints=[models.CheckConstraint(condition=models.Q(status__in=['registrado','aceptado','simulado','incierto']),name='delivery_valid_status')]

class FeatureRestriction(models.Model):
 regent=models.ForeignKey(User,on_delete=models.PROTECT,related_name='feature_restrictions')
 feature=models.CharField(max_length=20)
 reason=models.CharField(max_length=500)
 starts=models.DateTimeField(auto_now_add=True)
 ends=models.DateTimeField(null=True,blank=True)
 created_by=models.ForeignKey(User,on_delete=models.PROTECT,related_name='restrictions_created')
 revoked_at=models.DateTimeField(null=True,blank=True)
 revoked_by=models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='restrictions_revoked')
 class Meta:
  indexes=[models.Index(fields=['regent','feature','revoked_at'])]
