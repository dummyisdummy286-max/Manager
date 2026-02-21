from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('folder/<path:path>/', views.home, name='home_folder'),
    path('download/<path:path>/', views.download_folder, name='download_folder'),
    path('download_file/<path:path>/', views.download_file, name='download_file'),
    path('view/<path:path>/', views.view_file, name='view_file'),
]
