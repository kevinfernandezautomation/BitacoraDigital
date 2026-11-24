import os
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from core.models import User, LoginBucket
class Command(BaseCommand):
 def handle(self,*args,**kwargs):
  if not settings.DEBUG or os.getenv('ENABLE_TEST_SEED')!='1': raise CommandError('Solo ambiente de pruebas explícitamente autorizado')
  password=os.environ['TEST_LOGIN_PASSWORD']
  for role in ['regente','empresa','fiscalia','admin','soporte','inactive']:
   u,_=User.objects.get_or_create(username='qa_'+role)
   u.role=role if role!='inactive' else 'regente'; u.is_active=role!='inactive'; u.set_password(password); u.save()
  LoginBucket.objects.all().delete()
