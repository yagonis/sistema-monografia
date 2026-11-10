from django.contrib.auth.models import AbstractUser

class Usuario(AbstractUser):
    @property
    def eh_aluno(self):
        return self.is_active and self.groups.filter(name='Alunos').exists()

    @property
    def eh_professor(self):
        return self.is_active and self.groups.filter(name='Professores').exists()
