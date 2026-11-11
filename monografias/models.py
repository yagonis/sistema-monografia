from django.conf import settings
from django.db import models

from .validadores import validar_pdf


class Curso(models.Model):
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"


class Monografia(models.Model):
    class Status(models.TextChoices):
        RASCUNHO = "rascunho", "Rascunho"
        EM_AVALIACAO = "em_avaliacao", "Em Avaliação pelo orientador"
        APROVADA_ORIENTADOR = "aprovada_orientador", "Aprovada pelo orientador"

    titulo = models.CharField(max_length=250)
    resumo = models.TextField(blank=True)

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
