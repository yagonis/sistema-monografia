from django.urls import path, include
from rest_framework.routers import DefaultRouter
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from . import views

router = DefaultRouter()
for prefixo, view, nome in [
    ('cursos', views.CursoViewSet, 'curso'), ('publicadas', views.Publicas, 'publicada'),
    ('monografias', views.Monografias, 'monografia'), ('bancas', views.Bancas, 'banca'),
    ('membros', views.Membros, 'membro'), ('avaliacoes', views.Avaliacoes, 'avaliacao'),
    ('documentos', views.Documentos, 'documento'), ('usuarios', views.Usuarios, 'usuario'),
    ('alunos', views.Alunos, 'aluno'), ('professores', views.Professores, 'professor'),
    ('auditoria', views.Auditorias, 'auditoria'), ('eventos', views.Eventos, 'evento'),
]:
    router.register(prefixo, view, basename=nome)
urlpatterns = [
    path('health/', views.Health.as_view()),
    path('conta/', views.Conta.as_view()), path('orientadores/', views.Orientadores.as_view()),
    path('relatorios/', views.Relatorios.as_view()), path('externo/', views.Externo.as_view()),
    path('externo/pdf/', views.ExternoPDF.as_view()),
    path('schema/', SpectacularAPIView.as_view(), name='schema'),
    path('docs/', SpectacularSwaggerView.as_view(url_name='schema')),
    path('', include(router.urls)),
]
