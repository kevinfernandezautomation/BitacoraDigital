from django import forms
from .models import Regency,Sheet
class RegencyForm(forms.ModelForm):
 class Meta:
  model=Regency
  fields=['company','company_id','establishment','address','contact','contact_email','contact_phone','additional_contacts','kind','hours','evaluation']
  labels={'company':'Razón social','company_id':'Identificación de empresa','establishment':'Establecimiento','address':'Dirección','contact':'Contacto principal','contact_email':'Correo del contacto','contact_phone':'Teléfono','additional_contacts':'Contactos adicionales','kind':'Tipo de regencia','hours':'Horas de regencia','evaluation':'Evaluación de horas (PDF)'}
  widgets={'evaluation':forms.ClearableFileInput(attrs={'accept':'.pdf,application/pdf'}),'additional_contacts':forms.Textarea(attrs={'rows':3})}
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  for name in self.fields:
   if name!='additional_contacts': self.fields[name].required=True
  self.fields['hours'].min_value=1
  self.fields['hours'].max_value=168
  self.fields['hours'].validators.extend([__import__('django.core.validators',fromlist=['MinValueValidator']).MinValueValidator(1),__import__('django.core.validators',fromlist=['MaxValueValidator']).MaxValueValidator(168)])
 def clean_evaluation(self):
  f=self.cleaned_data['evaluation']
  if f.size>10*1024*1024 or f.size<8 or not f.name.lower().endswith('.pdf'): raise forms.ValidationError('Adjunte un PDF de hasta 10 MiB.')
  f.open('rb')
  if f.read(5)!=b'%PDF-': raise forms.ValidationError('El contenido no corresponde a un PDF.')
  f.seek(0)
  return f

class SheetForm(forms.ModelForm):
 revision=forms.IntegerField(required=False,widget=forms.HiddenInput)
 class Meta:
  model=Sheet
  fields=['date','title','body','commitments','people','tags','reference','revision']
  labels={'date':'Fecha de visita','title':'Título','body':'Actividades realizadas','commitments':'Compromisos establecidos','people':'Personas involucradas','tags':'Etiquetas (separadas por comas)','reference':'Hoja cerrada de referencia'}
  widgets={'date':forms.DateInput(format='%Y-%m-%d',attrs={'type':'date'}),'body':forms.Textarea(attrs={'rows':10,'maxlength':20000}),'commitments':forms.Textarea(attrs={'rows':5,'maxlength':20000})}
 def __init__(self,*args,**kwargs):
  super().__init__(*args,**kwargs)
  self.fields['reference'].queryset=Sheet.objects.filter(regency=self.instance.regency,closed=True)
  self.fields['revision'].initial=self.instance.revision
 def clean(self):
  d=super().clean()
  for field in ('body','commitments'):
   if len(d.get(field,'') or '')>20000: self.add_error(field,'Máximo 20000 caracteres')
  if self.instance.pk and d.get('revision')!=self.instance.revision: self.add_error(None,'El borrador cambió. Recargue antes de editar.')
  return d
