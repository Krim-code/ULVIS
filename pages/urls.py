from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('catalog/', views.catalog, name='catalog'),
    path('catalog/<slug:slug>/', views.category_detail, name='category_detail'),
    path('contacts/', views.contacts, name='contacts'),
    path('lead/', views.lead_submit, name='lead_submit'),  # POST формы
    path("offer/", views.offer_page, name="offer"),
    path("privacy/", views.privacy_page, name="privacy"),
]