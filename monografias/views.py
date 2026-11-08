from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import permission_required
from django.views.decorators.http import require_http_methods
from .models import Curso
from .forms import CursoForm

def inicio(request):
    return HttpResponse("texto texto texto texto teste")

def listar_cursos(request):
    cursos = Curso.objects.order_by("nome")
    return render(request, "monografias/listar_cursos.html", {"cursos": cursos})

@permission_required("monografias.add_curso", raise_exception=True)
def cadastrar_curso(request):
    if request.method == "POST":
        form = CursoForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("listar_cursos")
    else:
        form = CursoForm()
    return render(request, "monografias/cadastrar_curso.html", {"form": form})

@permission_required("monografias.change_curso", raise_exception=True)
def editar_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)

    if request.method == "POST":
        form = CursoForm(request.POST, instance=curso)
        if form.is_valid():
            form.save()
            return redirect("listar_cursos")
    else:
        form = CursoForm(instance=curso)
    return render(request, "monografias/editar_curso.html", {"form": form, "curso": curso})

@permission_required("monografias.delete_curso", raise_exception=True)
@require_http_methods(["GET", "POST"])
def excluir_curso(request, pk):
    curso = get_object_or_404(Curso, pk=pk)

    if request.method == "POST":
        curso.delete()
        return redirect("listar_cursos")
    return render(request, "monografias/excluir_curso.html", {"curso": curso})