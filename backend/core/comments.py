"""Append-only marginal comments; never update the signed sheet."""
from django import forms
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.core.paginator import Paginator
from .models import Comment, Audit

class CommentForm(forms.Form):
    body = forms.CharField(label='Comentario al margen', max_length=4000, strip=True, widget=forms.Textarea(attrs={'rows':4,'maxlength':4000,'required':True}))

def context(request, sheet, form=None):
    return {'comment_form': form if form is not None else CommentForm(),
            'comments_page': Paginator(Comment.objects.filter(sheet=sheet).select_related('author').order_by('-created','-pk'),25).get_page(request.GET.get('comments_page'))}

@transaction.atomic
def publish(request, sheet):
    from .views import sheets
    from django.shortcuts import get_object_or_404, redirect, render
    from django.db.models import Q
    from .models import User
    sheet = get_object_or_404(sheets(request.user).select_for_update(), pk=sheet.pk, closed=True)
    if request.user.role not in ('regente','empresa','admin','fiscalia'):
        raise PermissionDenied
    form = CommentForm(request.POST)
    if not form.is_valid():
        from .tasks import context as task_context
        return render(request,'detail.html',{'s':sheet,'members':User.objects.filter(Q(pk=sheet.regency.owner_id)|Q(memberships=sheet.regency)|Q(role__in=['admin','fiscalia'])).distinct(), **context(request,sheet,form),**task_context(request,sheet)},status=400)
    comment = Comment.objects.create(sheet=sheet,author=request.user,body=form.cleaned_data['body'])
    Audit.objects.create(actor=request.user,action=f'Comentario {comment.pk} hoja {sheet.pk}')
    response = redirect('detail',pk=sheet.pk)
    response['Location'] += '#comentarios'
    return response
