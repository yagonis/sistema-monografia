from django.urls import path
from . import views
urlpatterns = [path('api/publicadas/', views.pesquisar), path('internal/indexar/', views.indexar), path('health/', views.health)]
