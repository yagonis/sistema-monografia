"""Regras de negócio compartilhadas. Chamadores não devem gravar estados diretamente."""
import hashlib
import secrets
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django.core.cache import cache

from .models import Auditoria, Avaliacao, Banca, Documento, Evento, MembroBanca, Monografia


def sha256(arquivo):
    digest = hashlib.sha256()
    arquivo.seek(0)
    for bloco in arquivo.chunks():
        digest.update(bloco)
    arquivo.seek(0)
    return digest.hexdigest()


def auditar(ator, acao, objeto, **detalhes):
    Auditoria.objects.create(ator=ator if getattr(ator, 'is_authenticated', False) else None,
                            acao=acao, entidade=objeto._meta.label, registro_id=objeto.pk, detalhes=detalhes)


def evento(tipo, **dados):
    # Outbox durável: o worker publica/processa somente registros já confirmados.
    return Evento.objects.create(tipo=tipo, dados=dados)


def pode_gerir(usuario, trabalho):
    return usuario.is_authenticated and usuario.is_active and (
        usuario.is_superuser or (usuario.eh_professor and trabalho.orientador_id == usuario.pk)
        or (usuario.eh_coordenador and trabalho.curso.coordenador_id == usuario.pk)
    )


def exigir_gestor(usuario, trabalho):
    if not pode_gerir(usuario, trabalho):
        raise PermissionDenied


def conferir_integridade(trabalho):
    try:
        with trabalho.arquivo.open('rb') as arquivo:
            correto = sha256(arquivo) == trabalho.hash_sha256
    except OSError:
        correto = False
    if not correto:
        raise ValidationError('Arquivo indisponível ou com integridade inválida.')


@transaction.atomic
def submeter(usuario, pk):
    trabalho = Monografia.objects.select_for_update().get(pk=pk)
    if not usuario.eh_aluno or trabalho.autor_id != usuario.pk:
        raise PermissionDenied
    if not trabalho.pode_editar:
        raise ValidationError('Somente rascunhos podem ser submetidos.')
    if not trabalho.orientador or not trabalho.orientador.eh_professor:
        raise ValidationError('Escolha um orientador ativo antes de submeter.')
    conferir_integridade(trabalho)
    chave_taxa = f'submissoes:{usuario.pk}:{timezone.now().strftime("%Y%m%d%H")}'
    cache.add(chave_taxa, 0, 3600)
    if cache.incr(chave_taxa) > 10:
        raise ValidationError('Limite de submissões por hora atingido.')
    if not cache.add(f'upload_em_andamento:{pk}', True, 3600):
        raise ValidationError('Este upload já está em processamento.')
    trabalho.status = Monografia.Status.EM_AVALIACAO
    trabalho.submetida_em = timezone.now()
    trabalho.save(update_fields=['status', 'submetida_em'])
    auditar(usuario, 'submissao', trabalho)
    evento('monografia_submetida', monografia_id=pk)
    return trabalho


@transaction.atomic
def aprovar(usuario, pk):
    trabalho = Monografia.objects.select_for_update().get(pk=pk)
    if not usuario.eh_professor or trabalho.orientador_id != usuario.pk:
        raise PermissionDenied
    if trabalho.status != Monografia.Status.EM_AVALIACAO:
        raise ValidationError('A monografia não está aguardando aprovação.')
    conferir_integridade(trabalho)
    trabalho.status = Monografia.Status.APROVADA_ORIENTADOR
    trabalho.aprovado_por = usuario
    trabalho.aprovado_em = timezone.now()
    trabalho.save(update_fields=['status', 'aprovado_por', 'aprovado_em'])
    auditar(usuario, 'aprovacao_orientador', trabalho)
    return trabalho


@transaction.atomic
def salvar_banca(usuario, trabalho, dados, instancia=None):
    trabalho = Monografia.objects.select_for_update().get(pk=trabalho.pk)
    exigir_gestor(usuario, trabalho)
    if trabalho.status != Monografia.Status.APROVADA_ORIENTADOR:
        raise ValidationError('É necessária aprovação do orientador.')
    if instancia:
        banca = Banca.objects.select_for_update().get(pk=instancia.pk)
        if banca.status not in [Banca.Status.EM_PREPARACAO, Banca.Status.AGENDADA] or banca.membros.filter(avaliacao__isnull=False).exists():
            raise ValidationError('Bancas realizadas ou com avaliações não podem ser editadas.')
    else:
        if trabalho.bancas.exclude(status=Banca.Status.CANCELADA).exists():
            raise ValidationError('Já existe uma banca não cancelada.')
        banca = Banca(monografia=trabalho)
    for campo in ['data_hora', 'fim', 'local', 'link']:
        if campo in dados:
            setattr(banca, campo, dados[campo])
    if banca.data_hora <= timezone.now():
        raise ValidationError('Informe uma data futura.')
    if banca.fim and banca.fim <= banca.data_hora:
        raise ValidationError('O fim precisa ser posterior ao início.')
    if not banca.local and not banca.link:
        raise ValidationError('Informe local ou link.')
    banca.full_clean()
    banca.status = Banca.Status.EM_PREPARACAO
    banca.save()
    if instancia:
        banca.membros.update(confirmado=False)
        evento('banca_alterada', banca_id=banca.pk)
    auditar(usuario, 'preparacao_banca', banca)
    return banca


@transaction.atomic
def convidar(usuario, banca, dados):
    banca = Banca.objects.select_for_update().get(pk=banca.pk)
    exigir_gestor(usuario, banca.monografia)
    if banca.status != Banca.Status.EM_PREPARACAO:
        raise ValidationError('A composição só pode mudar durante a preparação.')
    pessoa = dados.get('usuario')
    if pessoa and (not pessoa.eh_professor or pessoa.pk == banca.monografia.autor_id):
        raise ValidationError('Membro interno deve ser professor ativo e não pode ser o autor.')
    if not pessoa and (not dados.get('email') or not dados.get('nome')):
        raise ValidationError('Membro externo precisa de nome e e-mail.')
    if pessoa and not pessoa.email:
        raise ValidationError('Cadastre o e-mail do professor para enviar o convite.')
    email = (pessoa.email if pessoa else dados['email']).strip().lower()
    if email == banca.monografia.autor.email.strip().lower():
        raise ValidationError('O autor não pode integrar a própria banca.')
    if banca.membros.filter(Q(email__iexact=email) | Q(usuario__email__iexact=email)).exists():
        raise ValidationError('Esta pessoa já foi convidada para a banca.')
    membro = MembroBanca(banca=banca, usuario=pessoa,
                         nome=dados.get('nome', ''), email=email)
    token = None
    if not pessoa:
        token = secrets.token_urlsafe(32)
        membro.token_hash = hashlib.sha256(token.encode()).hexdigest()
        membro.expira_em = timezone.now() + timedelta(hours=settings.CONVITE_VALIDADE_HORAS)
    membro.full_clean()
    membro.save()
    # Token não fica em texto puro no banco; entrega pelo retorno privado ao gestor.
    evento('membro_convidado', membro_id=membro.pk)
    auditar(usuario, 'convite_banca', banca, membro_id=membro.pk)
    return membro, token


def membro_por_token(token):
    if not token or len(token) > 200:
        raise PermissionDenied
    membro = MembroBanca.objects.filter(token_hash=hashlib.sha256(token.encode()).hexdigest(),
                                       usuario__isnull=True, revogado=False, expira_em__gt=timezone.now()).first()
    if membro is None:
        raise PermissionDenied
    return membro


@transaction.atomic
def confirmar(membro, usuario=None):
    banca = Banca.objects.select_for_update().get(pk=membro.banca_id)
    membro = MembroBanca.objects.select_for_update().get(pk=membro.pk)
    if membro.usuario_id is None and usuario is not None:
        raise PermissionDenied
    if membro.usuario_id is None and (not membro.expira_em or membro.expira_em <= timezone.now()):
        raise PermissionDenied
    if banca.status != Banca.Status.EM_PREPARACAO or membro.revogado:
        raise ValidationError('Convite indisponível.')
    if membro.usuario_id and (usuario is None or usuario.pk != membro.usuario_id or not usuario.eh_professor):
        raise PermissionDenied
    membro.confirmado = True
    membro.save(update_fields=['confirmado'])
    auditar(usuario, 'confirmacao_banca', banca, membro_id=membro.pk)
    return membro


@transaction.atomic
def agendar(usuario, pk):
    banca = Banca.objects.select_for_update().select_related('monografia').get(pk=pk)
    exigir_gestor(usuario, banca.monografia)
    if banca.status != Banca.Status.EM_PREPARACAO or banca.monografia.status != Monografia.Status.APROVADA_ORIENTADOR:
        raise ValidationError('Banca não pode ser agendada neste estado.')
    membros = list(banca.membros.order_by('pk'))
    if not membros or any(not m.confirmado or m.revogado for m in membros):
        raise ValidationError('Todos os membros precisam confirmar disponibilidade.')
    if any(m.usuario_id and not m.usuario.eh_professor for m in membros):
        raise ValidationError('Um membro interno não está mais ativo como professor.')
    if not banca.fim or banca.fim <= banca.data_hora or banca.data_hora <= timezone.now():
        raise ValidationError('Informe intervalo futuro válido para a defesa.')
    # Serializa agendamentos: impede corrida inclusive entre membros externos de bancas distintas.
    from .models import Curso
    list(Curso.objects.select_for_update().order_by('pk').values_list('pk', flat=True))
    candidatos = MembroBanca.objects.filter(banca__status=Banca.Status.AGENDADA,
        banca__data_hora__lt=banca.fim, banca__fim__gt=banca.data_hora).exclude(banca=banca)
    for membro in membros:
        email = membro.usuario.email if membro.usuario_id else membro.email
        identidade = Q(email__iexact=email) | Q(usuario__email__iexact=email)
        if membro.usuario_id:
            identidade |= Q(usuario_id=membro.usuario_id)
        conflito = candidatos.filter(identidade).exists()
        if conflito:
            raise ValidationError('Há conflito de horário para um dos membros.')
    conferir_integridade(banca.monografia)
    banca.status = Banca.Status.AGENDADA
    banca.save(update_fields=['status'])
    auditar(usuario, 'agendamento', banca)
    evento('banca_agendada', banca_id=banca.pk)
    return banca


@transaction.atomic
def cancelar(usuario, pk):
    banca = Banca.objects.select_for_update().get(pk=pk)
    exigir_gestor(usuario, banca.monografia)
    if banca.status not in [Banca.Status.EM_PREPARACAO, Banca.Status.AGENDADA] or banca.membros.filter(avaliacao__isnull=False).exists():
        raise ValidationError('Não é possível cancelar esta banca.')
    banca.status = Banca.Status.CANCELADA
    banca.save(update_fields=['status'])
    banca.membros.update(revogado=True)
    auditar(usuario, 'cancelamento_banca', banca)
    return banca


@transaction.atomic
def avaliar(membro, dados, usuario=None):
    banca = Banca.objects.select_for_update().get(pk=membro.banca_id)
    membro.refresh_from_db()
    if membro.usuario_id is None and usuario is not None:
        raise PermissionDenied
    if membro.usuario_id is None and (not membro.expira_em or membro.expira_em <= timezone.now()):
        raise PermissionDenied
    if membro.usuario_id and (usuario is None or usuario.pk != membro.usuario_id or not usuario.eh_professor):
        raise PermissionDenied
    if membro.revogado or not membro.confirmado or banca.status != Banca.Status.AGENDADA or banca.encerrada_em:
        raise ValidationError('A banca não está aberta para avaliações.')
    if not banca.fim or banca.fim > timezone.now():
        raise ValidationError('A avaliação só pode ser lançada após a defesa.')
    nota = Decimal(str(dados['nota']))
    if nota < settings.NOTA_MINIMA_ESCALA or nota > settings.NOTA_MAXIMA_ESCALA:
        raise ValidationError('Nota fora da escala configurada.')
    avaliacao = Avaliacao.objects.filter(membro=membro).first() or Avaliacao(membro=membro)
    avaliacao.nota, avaliacao.parecer, avaliacao.recomendacao = nota, dados['parecer'], dados['recomendacao']
    avaliacao.full_clean()
    avaliacao.save()
    auditar(usuario, 'avaliacao', avaliacao, membro_id=membro.pk)
    evento('avaliacao_registrada', banca_id=banca.pk)
    return avaliacao


@transaction.atomic
def fechar_resultado(pk):
    banca = Banca.objects.select_for_update().get(pk=pk)
    if banca.encerrada_em or banca.status != Banca.Status.AGENDADA:
        return banca
    membros = list(banca.membros.all())
    avaliacoes = list(Avaliacao.objects.filter(membro__banca=banca))
    if not membros or len(avaliacoes) != len(membros):
        return banca
    banca.nota_final = sum(a.nota for a in avaliacoes) / len(avaliacoes)
    recomendacoes = {a.recomendacao for a in avaliacoes}
    trabalho = Monografia.objects.select_for_update().get(pk=banca.monografia_id)
    if 'reprovado' in recomendacoes:
        trabalho.status = Monografia.Status.REPROVADA
    elif 'ressalvas' in recomendacoes:
        trabalho.status = Monografia.Status.RESSALVAS
    else:
        trabalho.status = Monografia.Status.APROVADA
    trabalho.save(update_fields=['status'])
    banca.encerrada_em = timezone.now()
    banca.status = Banca.Status.REALIZADA
    banca.save(update_fields=['nota_final', 'encerrada_em', 'status'])
    auditar(None, 'resultado_final', banca, nota=str(banca.nota_final), resultado=trabalho.status)
    publicar_se_pronta(trabalho.pk)
    return banca


@transaction.atomic
def publicar_se_pronta(pk):
    trabalho = Monografia.objects.select_for_update().get(pk=pk)
    if trabalho.status not in [Monografia.Status.APROVADA, Monografia.Status.RESSALVAS]:
        return False
    validos = trabalho.documentos.filter(validado_em__isnull=False)
    if not validos.filter(tipo=Documento.Tipo.TERMO).exists():
        return False
    if trabalho.status == Monografia.Status.RESSALVAS and not validos.filter(tipo=Documento.Tipo.CORRIGIDA).exists():
        return False
    conferir_integridade(trabalho)
    trabalho.status = Monografia.Status.PUBLICADA
    trabalho.publicada_em = timezone.now()
    trabalho.save(update_fields=['status', 'publicada_em'])
    auditar(None, 'publicacao', trabalho)
    evento('monografia_publicada', monografia_id=pk)
    return True


@transaction.atomic
def validar_documento(usuario, pk):
    documento = Documento.objects.select_for_update().get(pk=pk)
    trabalho = Monografia.objects.select_for_update().get(pk=documento.monografia_id)
    exigir_gestor(usuario, trabalho)
    if trabalho.status == Monografia.Status.PUBLICADA:
        raise ValidationError('Documentos de monografia publicada estão bloqueados.')
    with documento.arquivo.open('rb') as arquivo:
        if sha256(arquivo) != documento.hash_sha256:
            raise ValidationError('Integridade do documento inválida.')
    documento.validado_por, documento.validado_em = usuario, timezone.now()
    documento.save(update_fields=['validado_por', 'validado_em'])
    auditar(usuario, 'validacao_documento', documento)
    publicar_se_pronta(trabalho.pk)
    return documento
