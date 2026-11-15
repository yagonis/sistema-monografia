from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Usuario, PerfilAluno, PerfilProfessor

class PerfilAlunoInline(admin.StackedInline):
    model = PerfilAluno
    fk_name = 'usuario'
    extra = 0


class PerfilProfessorInline(admin.StackedInline):
    model = PerfilProfessor
    extra = 0


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    inlines = [PerfilAlunoInline, PerfilProfessorInline]
