from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from .models import Curso, Monografia
from .forms import CursoForm, MonografiaForm

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

@login_required(login_url="admin:login")
@require_http_methods(["GET", "POST"])
def enviar_rascunho(request):
    if request.method == "POST":
        form = MonografiaForm(request.POST, request.FILES)

        if form.is_valid():
            rascunho = form.save(commit=False)
            rascunho.autor = request.user
            rascunho.save()

            messages.success(request, f'Rascunho "{rascunho.titulo}" salvo.')
            return redirect("meus_rascunhos")
    else:
        form = MonografiaForm()
        
    return render(request, "monografias/enviar_rascunho.html", {"form": form})

@login_required(login_url="admin:login")
def meus_rascunhos(request):
    rasunhos = Monografia.objects.filter(
        autor=request.user,
        status=Monografia.Status.RASCUNHO,
    ).select_related("curso").order_by("titulo")

    return render(request, "monografias/meus_rascunhos.html", {"rascunhos": rasunhos})

@login_required(login_url="admin:login")
@require_http_methods(["GET", "POST"])
def editar_rascunho(request, pk):
    rascunho = get_object_or_404(
        Monografia, pk=pk, autor=request.user, status=Monografia.Status.RASCUNHO,
    )

    if request.method == "POST":
        form = MonografiaForm(request.POST, request.FILES, instance=rascunho)

        if form.is_valid():
            form.save()
            messages.success(request, f'Rascunho "{rascunho.titulo}" atualizado.')
            return redirect("meus_rascunhos")
    else:
        form = MonografiaForm(instance=rascunho)
    return render(request, "monografias/editar_rascunho.html", {"form": form, "rascunho": rascunho})

@login_required(login_url="admin:login")
@require_POST
@transaction.atomic
def submeter_rascunho(request, pk):
    rascunho = get_object_or_404(
        Monografia, pk=pk, autor=request.user, status=Monografia.Status.RASCUNHO,
    )
    
    if not rascunho.orientador:
        messages.error(request, "Escolha um orientador antes de submeter o rascunho.")
        return redirect("editar_rascunho", pk=pk)
    rascunho.status = Monografia.Status.EM_AVALIACAO
    rascunho.save(update_fields=["status"])

    messages.success(request, f'"{rascunho.titulo}" submetido para avaliação do orientador.')
    return redirect("meus_rascunhos")