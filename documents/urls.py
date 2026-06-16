from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('documents/', views.document_list, name='document_list'),
    path('documents/export/', views.document_export, name='document_export'),
    path('documents/create/', views.document_create, name='document_create'),
    path('documents/<str:slug>/', views.document_detail, name='document_detail'),
    path('documents/<str:slug>/edit/', views.document_edit, name='document_edit'),
    path('documents/<str:slug>/delete/', views.document_delete, name='document_delete'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('audit/', views.audit_log_list, name='audit_log'),
    path('login/', auth_views.LoginView.as_view(template_name='documents/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
]
