import hashlib

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.db.models.deletion import ProtectedError
from .models import Curso, Monografia
from .forms import CursoForm, MonografiaForm
from django.utils import timezone
from usuarios.decorators import exige_perfil

def inicio(request):
    return render(request, 'monografias/inicio.html')

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
        try:
            curso.delete()
        except ProtectedError:
            return render(request, 'monografias/excluir_curso.html', {
                'curso': curso,
                'erro': 'Não é possível excluir este curso porque existem monografias vinculadas.',
            }, status=409)
        return redirect("listar_cursos")
    return render(request, "monografias/excluir_curso.html", {"curso": curso})

@exige_perfil('eh_aluno')
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

@exige_perfil('eh_aluno')
def meus_rascunhos(request):
    rasunhos = Monografia.objects.filter(
        autor=request.user,
        status=Monografia.Status.RASCUNHO,
    ).select_related("curso").order_by("titulo")

    return render(request, "monografias/meus_rascunhos.html", {"rascunhos": rasunhos})

@exige_perfil('eh_aluno')
@require_http_methods(["GET", "POST"])
@transaction.atomic
def editar_rascunho(request, pk):
    rascunho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, autor=request.user, status=Monografia.Status.RASCUNHO,
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

@exige_perfil('eh_aluno')
@require_POST
@transaction.atomic
def submeter_rascunho(request, pk):
    rascunho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, autor=request.user, status=Monografia.Status.RASCUNHO,
    )
    
    if not rascunho.orientador or not rascunho.orientador.eh_professor:
        messages.error(request, "Escolha um orientador antes de submeter o rascunho.")
        return redirect("editar_rascunho", pk=pk)
    rascunho.status = Monografia.Status.EM_AVALIACAO
    rascunho.save(update_fields=["status"])

    messages.success(request, f'"{rascunho.titulo}" submetido para avaliação do orientador.')
    return redirect("minhas_monografias")


@exige_perfil('eh_aluno')
def minhas_monografias(request):
    trabalhos = Monografia.objects.filter(autor=request.user).select_related('curso', 'orientador').order_by('titulo')
    return render(request, 'monografias/acompanhamento.html', {'trabalhos': trabalhos})


@exige_perfil('eh_professor')
def orientacoes(request):
    trabalhos = Monografia.objects.filter(
        orientador=request.user,
        status__in=[Monografia.Status.EM_AVALIACAO, Monografia.Status.APROVADA_ORIENTADOR],
    ).select_related('autor', 'curso').order_by('titulo')
    return render(request, 'monografias/orientacoes.html', {'trabalhos': trabalhos})


@exige_perfil('eh_professor')
@require_POST
@transaction.atomic
def aprovar_orientacao(request, pk):
    trabalho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, orientador=request.user,
        status=Monografia.Status.EM_AVALIACAO,
    )
    # Aprovar somente a versão efetivamente submetida.
    digest = hashlib.sha256()
    try:
        with trabalho.arquivo.open('rb') as arquivo:
            for bloco in arquivo.chunks():
                digest.update(bloco)
    except OSError:
        messages.error(request, 'Arquivo indisponível. A aprovação não foi registrada.')
        return redirect('orientacoes')
    if digest.hexdigest() != trabalho.hash_sha256:
        messages.error(request, 'A integridade do PDF não pôde ser confirmada. A aprovação não foi registrada.')
        return redirect('orientacoes')
    trabalho.status = Monografia.Status.APROVADA_ORIENTADOR
    trabalho.aprovado_por = request.user
    trabalho.aprovado_em = timezone.now()
    trabalho.save(update_fields=['status', 'aprovado_por', 'aprovado_em'])
    messages.success(request, 'Submissão aprovada pelo orientador. Isso não representa aprovação em banca ou publicação.')
    return redirect('orientacoes')


@login_required
def baixar_pdf(request, pk):
    trabalho = get_object_or_404(Monografia, pk=pk)
    autor = request.user.eh_aluno and trabalho.autor_id == request.user.pk
    orientador = (
        request.user.eh_professor and trabalho.orientador_id == request.user.pk
        and trabalho.status in [Monografia.Status.EM_AVALIACAO, Monografia.Status.APROVADA_ORIENTADOR]
    )
    if not (autor or orientador):
        raise Http404
    try:
        arquivo = trabalho.arquivo.open('rb')
    except OSError as exc:
        raise Http404('Arquivo indisponível') from exc
    return FileResponse(arquivo, as_attachment=True, filename=f'monografia-{trabalho.pk}.pdf', content_type='application/pdf')
