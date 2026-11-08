from django.db import models

class Curso(models.Model):
    nome = models.CharField(max_length=150)
    codigo = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return f"{self.codigo} - {self.nome}"