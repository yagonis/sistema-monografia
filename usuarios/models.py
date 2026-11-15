from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.db import models

class Usuario(AbstractUser):
    @property
    def eh_aluno(self):
        return self.is_active and self.groups.filter(name='Alunos').exists()

    @property
    def eh_professor(self):
        return self.is_active and self.groups.filter(name='Professores').exists()

    @property
    def eh_coordenador(self):
        return self.is_active and self.groups.filter(name='Coordenadores').exists()


class PerfilAluno(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_aluno')
    matricula = models.CharField(max_length=50, unique=True)
    curso = models.ForeignKey('monografias.Curso', on_delete=models.PROTECT, related_name='alunos')
    orientador_atual = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='alunos_orientados',
        limit_choices_to={'groups__name': 'Professores', 'is_active': True},
    )

    def __str__(self):
        return f'{self.matricula} — {self.usuario}'


class PerfilProfessor(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_professor')
    departamento = models.CharField(max_length=150, blank=True)
    area_pesquisa = models.CharField('área de pesquisa', max_length=250, blank=True)

    def __str__(self):
        return str(self.usuario)
