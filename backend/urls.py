from django.urls import path
from django.contrib.auth import views as auth
from core import views as v
from core.authentication import sign_in
from core.security import OwnPasswordChange, panel as security_panel
urlpatterns=[path('',v.home),path('login/',sign_in,name='login'),path('logout/',auth.LogoutView.as_view()),path('password/',OwnPasswordChange.as_view()),path('regency/new/',v.new_regency),path('regency/<int:pk>/approve/',v.approve),path('regency/<int:pk>/evaluation/',v.evaluation),path('regency/<int:rid>/new/',v.edit),path('regency/<int:rid>/edit/<int:pk>/',v.edit),path('sheet/<int:pk>/',v.detail,name='detail'),path('sheet/<int:pk>/action/',v.action),path('attachment/<int:pk>/',v.download),path('users/',v.users),path('suspend/<int:pk>/',v.suspend),path('api/sheets/',v.api)]
from core import enterprise as e
urlpatterns += [path('reports/',e.reports),path('audit/',e.audit_log),path('sheet/<int:pk>/integrity/',e.integrity),path('health/',e.health)]

urlpatterns += [path('regency/<int:pk>/',v.review_regency,name='regency-review'),path('regency/<int:pk>/revise/',v.revise_regency)]

urlpatterns += [path('sheet/<int:pk>/archive/',e.archive_download)]

from core.tasks import dashboard
urlpatterns += [path('tasks/',dashboard,name='tasks')]
from core.delivery import send_sheet
urlpatterns += [path('sheet/<int:pk>/email/',send_sheet,name='sheet-email')]
from core.restrictions import panel
urlpatterns += [path('restrictions/',panel,name='restrictions')]

urlpatterns += [path('security/',security_panel,name='security')]
