import csv,secrets
from django.core.management.base import BaseCommand
from core.models import User
class Command(BaseCommand):
 def add_arguments(self,p): p.add_argument('csv')
 def handle(self,*a,**o):
  with open(o['csv'],encoding='utf-8-sig') as f:
   for row in csv.DictReader(f):
    u,created=User.objects.get_or_create(username=row['username'],defaults={'email':row['email'],'role':'regente'})
    if created: u.set_unusable_password(); u.save()
  self.stdout.write('Importación terminada. Activar credenciales mediante procedimiento autorizado.')
