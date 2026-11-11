from django.contrib import admin
from django.contrib.admin.utils import unquote
from django.db import transaction
from .models import Curso
from .forms import MonografiaForm
from .models import Monografia

@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ['nome', 'codigo', 'coordenador']
    search_fields = ['nome', 'codigo']

@admin.register(Monografia)
class MonografiaAdmin(admin.ModelAdmin):
    form = MonografiaForm
    fields = [
        'titulo', 'resumo', 'curso', 'autor', 'orientador', 'arquivo',
        'hash_sha256', 'status', 'aprovado_por', 'aprovado_em',
    ]
    readonly_fields = ['hash_sha256', 'status', 'aprovado_por', 'aprovado_em']

    def has_change_permission(self, request, obj=None):
        return super().has_change_permission(request, obj) and (obj is None or obj.pode_editar)

    @transaction.atomic
    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        if request.method == 'POST' and object_id is not None:
            obj = self.get_object(request, unquote(object_id))
            if obj is not None:
                # Mantenha o bloqueio até salvar, impedindo disputa com a submissão.
                Monografia.objects.select_for_update().get(pk=obj.pk)
        return super().changeform_view(request, object_id, form_url, extra_context)
