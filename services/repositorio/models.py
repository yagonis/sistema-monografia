from django.db import models

class Publicacao(models.Model):
    origem_id = models.PositiveBigIntegerField(unique=True)
    titulo = models.CharField(max_length=250)
    autor = models.CharField(max_length=300)
    orientador = models.CharField(max_length=300)
    curso_id = models.PositiveBigIntegerField(db_index=True)
    ano_defesa = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    palavras_chave = models.CharField(max_length=500, blank=True)
    texto = models.TextField(blank=True)
    dados = models.JSONField(default=dict)
    atualizado_em = models.DateTimeField(auto_now=True)
