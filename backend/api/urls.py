# backend/api/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.SignupView.as_view(), name='signup'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('upload/', views.MediaUploadView.as_view(), name='upload'),
    path('media/', views.MediaListView.as_view(), name='media-list'),
    path('search/', views.MediaSearchView.as_view(), name='search'),
    path('delete/<int:media_id>/', views.DeleteMediaView.as_view(), name='delete'),
]