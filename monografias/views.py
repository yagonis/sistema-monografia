import hashlib

from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib import messages
from django.views.decorators.http import require_POST, require_http_methods
from django.db import transaction
from django.db.models.deletion import ProtectedError
from .models import Curso, Monografia, Banca
from .forms import CursoForm, MonografiaForm, BancaForm
from django.utils import timezone
from usuarios.decorators import exige_perfil
from .permissoes import monografias_da_coordenacao
from . import servicos as regras
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

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
                'erro': 'Não é possível excluir este curso porque existem registros acadêmicos vinculados.',
            }, status=409)
        return redirect("listar_cursos")
    return render(request, "monografias/excluir_curso.html", {"curso": curso})

@exige_perfil('eh_aluno')
@require_http_methods(["GET", "POST"])
@transaction.atomic
def enviar_rascunho(request):
    if request.method == "POST":
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        form = MonografiaForm(request.POST, request.FILES)

        if form.is_valid():
            rascunho = form.save(commit=False)
            rascunho.autor = request.user
            if Monografia.objects.filter(autor=request.user, hash_sha256=rascunho.hash_sha256).exists():
                form.add_error('arquivo', 'Este PDF já foi enviado por você.')
                return render(request, 'monografias/enviar_rascunho.html', {'form': form})
            rascunho.save()
            regras.auditar(request.user, 'upload', rascunho, versao=rascunho.versao)

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
    get_user_model().objects.select_for_update().get(pk=request.user.pk)
    rascunho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, autor=request.user, status=Monografia.Status.RASCUNHO,
    )

    if request.method == "POST":
        form = MonografiaForm(request.POST, request.FILES, instance=rascunho)

        if form.is_valid():
            alterado = form.save(commit=False)
            if Monografia.objects.filter(autor=request.user, hash_sha256=alterado.hash_sha256).exclude(pk=alterado.pk).exists():
                form.add_error('arquivo', 'Este PDF já foi enviado por você.')
                return render(request, 'monografias/editar_rascunho.html', {'form': form, 'rascunho': rascunho})
            if 'arquivo' in request.FILES:
                alterado.versao += 1
            alterado.save()
            regras.auditar(request.user, 'edicao_rascunho', alterado, versao=alterado.versao)
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
    
    try:
        regras.submeter(request.user, pk)
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
        return redirect('editar_rascunho', pk=pk)

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


@exige_perfil('eh_coordenador')
def coordenacao(request):
    trabalhos = monografias_da_coordenacao(request.user).select_related(
        'autor', 'curso', 'orientador',
    ).order_by('curso__nome', 'titulo')
    cursos = Curso.objects.filter(coordenador=request.user).order_by('nome')
    return render(request, 'monografias/coordenacao.html', {'trabalhos': trabalhos, 'cursos': cursos})


@exige_perfil('eh_professor')
@require_POST
@transaction.atomic
def aprovar_orientacao(request, pk):
    trabalho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, orientador=request.user,
        status=Monografia.Status.EM_AVALIACAO,
    )
    try:
        regras.aprovar(request.user, pk)
    except ValidationError as exc:
        messages.error(request, ' '.join(exc.messages))
        return redirect('orientacoes')
    messages.success(request, 'Submissão aprovada pelo orientador. Isso não representa aprovação em banca ou publicação.')
    return redirect('orientacoes')


@login_required
def baixar_pdf(request, pk):
    trabalho = get_object_or_404(Monografia, pk=pk)
    autor = request.user.eh_aluno and trabalho.autor_id == request.user.pk
    orientador = (
        request.user.eh_professor and trabalho.orientador_id == request.user.pk
        and trabalho.status != Monografia.Status.RASCUNHO
    )
    coordenador = monografias_da_coordenacao(request.user).filter(pk=trabalho.pk).exists()
    if not (autor or orientador or coordenador):
        raise Http404
    try:
        regras.conferir_integridade(trabalho)
    except ValidationError as exc:
        raise Http404('Arquivo indisponível ou com integridade inválida') from exc
    try:
        arquivo = trabalho.arquivo.open('rb')
    except OSError as exc:
        raise Http404('Arquivo indisponível') from exc
    return FileResponse(arquivo, as_attachment=True, filename=f'monografia-{trabalho.pk}.pdf', content_type='application/pdf')

@exige_perfil('eh_professor')
@require_http_methods(["GET", "POST"])
@transaction.atomic
def preparar_banca(request, pk):
    trabalho = get_object_or_404(
        Monografia.objects.select_for_update(), pk=pk, orientador=request.user,
        status=Monografia.Status.APROVADA_ORIENTADOR,
    )


    if trabalho.bancas.exclude(status=Banca.Status.CANCELADA).exists():
        messages.info(request, 'Já existe uma banca para esta monografia.')
        return redirect("orientacoes")
    if request.method == "POST":
        form = BancaForm(request.POST)
        if form.is_valid():
            try:
                regras.salvar_banca(request.user, trabalho, form.cleaned_data)
            except ValidationError as exc:
                form.add_error(None, exc)
                return render(request, 'monografias/preparar_banca.html', {'form': form, 'trabalho': trabalho})
            messages.success(request, 'Proposta de banca salva.')
            return redirect("orientacoes")
    else:
        form = BancaForm()

    return render(request, 'monografias/preparar_banca.html', {'form': form, 'trabalho': trabalho})
