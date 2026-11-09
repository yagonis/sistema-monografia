from django.contrib import admin
from .models import Curso
from .forms import MonografiaForm
from .models import Monografia

admin.site.register(Curso)

@admin.register(Monografia)
class MonografiaAdmin(admin.ModelAdmin):
    form = MonografiaForm
    fields = ["titulo", "resumo", "curso", "autor", "arquivo", "hash_sha256"]
    readonly_fields = ["hash_sha256"]