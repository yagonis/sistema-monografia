from django.conf import settings
from django.db import models

from .validadores import validar_pdf


class Curso(models.Model):
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=20, unique=True)
    coordenador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
        related_name='cursos_coordenados',
        limit_choices_to={'groups__name': 'Coordenadores', 'is_active': True},
    )

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Monografia(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_AVALIACAO = "em_avaliacao", "Em Avaliação pelo orientador"
        APROVADA_ORIENTADOR = "aprovada_orientador", "Aprovada pelo orientador"
        APROVADA = 'aprovada', 'Aprovada em defesa'
        RESSALVAS = 'ressalvas', 'Aprovada com ressalvas'
        REPROVADA = 'reprovada', 'Reprovada'
        PUBLICADA = 'publicada', 'Publicada'

    titulo = models.CharField(max_length=250)
    resumo = models.TextField(blank=True)
    palavras_chave = models.CharField(max_length=500, blank=True)
    submetida_em = models.DateTimeField(null=True, blank=True, editable=False)
    publicada_em = models.DateTimeField(null=True, blank=True, editable=False)
    texto_extraido = models.TextField(blank=True, editable=False)
    versao = models.PositiveIntegerField(default=1, editable=False)

    autor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
    )

    orientador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="monografias_orientadas",
        limit_choices_to={"groups__name": "Professores", "is_active": True},
        null=True,
        blank=True,
    )

    curso = models.ForeignKey(
        Curso,
        on_delete=models.PROTECT,
    )

    arquivo = models.FileField(
        upload_to="monografias/%Y/%m/",
        validators=[validar_pdf],
    )
    hash_sha256 = models.CharField(max_length=64, editable=False)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.RASCUNHO,
    )
    aprovado_em = models.DateTimeField(null=True, blank=True, editable=False)
    aprovado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='aprovacoes_orientador', null=True, blank=True, editable=False,
    )

    @property
    def pode_editar(self):
        return self.status == self.Status.RASCUNHO

    def __str__(self):
        return self.titulo

class Banca(models.Model):
    class Status(models.TextChoices):
        EM_PREPARACAO = "em_preparacao", "Em Preparação"
        AGENDADA = "agendada", "Agendada"
        REALIZADA = "realizada", "Realizada"
        CANCELADA = "cancelada", "Cancelada"

    monografia = models.ForeignKey(
        Monografia,
        on_delete=models.PROTECT,
        related_name='bancas',
    )

    data_hora = models.DateTimeField("Data e hora da defesa")
    fim = models.DateTimeField(null=True, blank=True)
    encerrada_em = models.DateTimeField(null=True, blank=True, editable=False)
    nota_final = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    local = models.CharField("Local presencial", max_length=250, blank=True)
    link = models.URLField("Link de videoconferência", blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.EM_PREPARACAO,
    )

    def __str__(self):
        return f"Banca de {self.monografia.titulo} em {self.data_hora}"


class MembroBanca(models.Model):
    banca = models.ForeignKey(Banca, on_delete=models.CASCADE, related_name='membros')
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)
    nome = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    confirmado = models.BooleanField(default=False)
    token_hash = models.CharField(max_length=64, blank=True, editable=False)
    expira_em = models.DateTimeField(null=True, blank=True)
    revogado = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['banca', 'usuario'], condition=models.Q(usuario__isnull=False), name='membro_interno_unico'),
            models.UniqueConstraint(fields=['banca', 'email'], condition=models.Q(usuario__isnull=True), name='membro_externo_unico'),
        ]


class Avaliacao(models.Model):
    class Recomendacao(models.TextChoices):
        APROVADO = 'aprovado', 'Aprovado sem ressalvas'
        RESSALVAS = 'ressalvas', 'Aprovado com ressalvas'
        REPROVADO = 'reprovado', 'Reprovado'

    membro = models.OneToOneField(MembroBanca, on_delete=models.PROTECT, related_name='avaliacao')
    nota = models.DecimalField(max_digits=6, decimal_places=2)
    parecer = models.TextField()
    recomendacao = models.CharField(max_length=12, choices=Recomendacao.choices)
    atualizada_em = models.DateTimeField(auto_now=True)


class Documento(models.Model):
    class Tipo(models.TextChoices):
        ATA = 'ata', 'Ata de defesa'
        TERMO = 'termo', 'Termo de autorização'
        ORTOGRAFIA = 'ortografia', 'Comprovante de revisão ortográfica'
        CORRIGIDA = 'corrigida', 'Versão corrigida'

    monografia = models.ForeignKey(Monografia, on_delete=models.PROTECT, related_name='documentos')
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    arquivo = models.FileField(upload_to='documentos/%Y/%m/', validators=[validar_pdf])
    hash_sha256 = models.CharField(max_length=64, editable=False)
    validado_em = models.DateTimeField(null=True, blank=True, editable=False)
    validado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True)


class Auditoria(models.Model):
    ator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    acao = models.CharField(max_length=80)
    entidade = models.CharField(max_length=80)
    registro_id = models.PositiveBigIntegerField()
    detalhes = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)


class Evento(models.Model):
    tipo = models.CharField(max_length=80)
    dados = models.JSONField(default=dict)
    criado_em = models.DateTimeField(auto_now_add=True)
    processado_em = models.DateTimeField(null=True, blank=True)
    erro = models.TextField(blank=True)
    tentativas = models.PositiveIntegerField(default=0)
