from django.urls import path

from . import views

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("cursos/", views.listar_cursos, name="listar_cursos"),
    path("cursos/cadastrar/", views.cadastrar_curso, name="cadastrar_curso"),
    path("cursos/<int:pk>/editar/", views.editar_curso, name="editar_curso"),
    path("cursos/<int:pk>/excluir/", views.excluir_curso, name="excluir_curso"),
 ]