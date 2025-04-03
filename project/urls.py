from django.urls import path
from . import views
from django.conf import settings
from django.conf.urls.static import static

app_name = 'project'

urlpatterns = [
    path('', views.project_list, name='project_list'),
    path('create/', views.project_create, name='project_create'),
    path('<int:pk>/', views.project_detail, name='project_detail'),
    path('<int:pk>/update/', views.project_update, name='project_update'),
    path('<int:pk>/delete/', views.project_delete, name='project_delete'),
    # path('employee-search/', views.employee_search, name='employee_search'),
]
# if settings.DEBUG:
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)