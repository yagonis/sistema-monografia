from django.urls import path

from . import views

urlpatterns = [
    path('coordenacao/', views.coordenacao, name='coordenacao'),
    path('minhas-monografias/', views.minhas_monografias, name='minhas_monografias'),
    path('orientacoes/', views.orientacoes, name='orientacoes'),
    path('orientacoes/<int:pk>/aprovar/', views.aprovar_orientacao, name='aprovar_orientacao'),
    path('monografias/<int:pk>/pdf/', views.baixar_pdf, name='baixar_pdf'),
    path("", views.inicio, name="inicio"),
    path("cursos/", views.listar_cursos, name="listar_cursos"),
    path("cursos/cadastrar/", views.cadastrar_curso, name="cadastrar_curso"),
    path("cursos/<int:pk>/editar/", views.editar_curso, name="editar_curso"),
    path("cursos/<int:pk>/excluir/", views.excluir_curso, name="excluir_curso"),
    path("rascunhos/enviar/", views.enviar_rascunho, name="enviar_rascunho"),
    path("rascunhos/", views.meus_rascunhos, name="meus_rascunhos"),
    path("rascunhos/<int:pk>/editar/", views.editar_rascunho, name="editar_rascunho"),
    path("rascunhos/<int:pk>/submeter/", views.submeter_rascunho, name="submeter_rascunho"),
    path("orientacoes/<int:pk>/banca/preparar/", views.preparar_banca, name="preparar_banca"),
 ]
