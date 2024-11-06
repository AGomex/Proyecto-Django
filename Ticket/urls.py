from django.urls import path
from . import views

urlpatterns = [
    path('', views.ver_tickets, name='ver_tickets'),
    path('agregar/', views.agregar_ticket, name='agregar_ticket'),
    path('aceptar/', views.aceptar_ticket, name='aceptar_ticket'),
    path('aceptados/', views.ver_aceptados, name='ver_aceptados'),
    path('eliminar/<int:ticket_id>/', views.eliminar_ticket, name='eliminar_ticket'),
]
