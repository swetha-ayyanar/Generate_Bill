from django.urls import path
from . import views

app_name = 'bill_app'

urlpatterns = [
    path('', views.billing_page, name='billing_page'),
    path('get-products/', views.get_products, name='get_products'),
    path('generate-bill/', views.generate_bill, name='generate_bill'),
    path('history/', views.history, name='history'),
    path('purchase/<int:pk>/', views.purchase_detail, name='purchase_detail'),
]
