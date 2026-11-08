from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import permission_required
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