from pathlib import Path
from django.core.management.base import BaseCommand
from django.db import connection
class Command(BaseCommand):
    help='Instala controles PostgreSQL de inmutabilidad; ejecutar con rol de migración.'
    def handle(self,*args,**kwargs):
        if connection.vendor!='postgresql': return
        with connection.cursor() as c:
            c.execute('DROP TRIGGER IF EXISTS protect_sheet_trigger ON core_sheet; DROP TRIGGER IF EXISTS protect_attachment_trigger ON core_attachment;')
            c.execute((Path(__file__).resolve().parents[3]/'database/immutability.sql').read_text())
