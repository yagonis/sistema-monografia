from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("cursos/", views.listar_cursos, name="listar_cursos"),
    path("cursos/cadastrar/", views.cadastrar_curso, name="cadastrar_curso")
 ]