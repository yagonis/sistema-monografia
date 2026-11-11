from django.test import TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.urls import reverse

from monografias.models import Curso
from .models import PerfilAluno, PerfilProfessor


class PerfisAcademicosTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user('pessoa')
        self.curso = Curso.objects.create(nome='Sistemas', codigo='SI')

    def test_usuario_antigo_continua_sem_perfis(self):
        self.assertFalse(hasattr(self.usuario, 'perfil_aluno'))
        self.assertFalse(hasattr(self.usuario, 'perfil_professor'))

    def test_perfis_podem_coexistir_sem_conceder_papel(self):
        PerfilAluno.objects.create(usuario=self.usuario, matricula='2026001', curso=self.curso)
        PerfilProfessor.objects.create(usuario=self.usuario, departamento='Computação', area_pesquisa='Redes')
        self.assertEqual(self.usuario.perfil_aluno.curso, self.curso)
        self.assertEqual(self.usuario.perfil_professor.departamento, 'Computação')
        self.assertFalse(self.usuario.eh_aluno)
        self.assertFalse(self.usuario.eh_professor)
        self.assertFalse(self.usuario.is_staff)

    def test_matricula_unica_e_obrigatoria(self):
        PerfilAluno.objects.create(usuario=self.usuario, matricula='2026001', curso=self.curso)
        outro = get_user_model().objects.create_user('outro')
        for matricula in ['2026001', '']:
            with self.assertRaises(ValidationError):
                PerfilAluno(usuario=outro, matricula=matricula, curso=self.curso).full_clean()

    def test_coordenador_selecionavel_precisa_grupo_e_conta_ativa(self):
        self.curso.coordenador = self.usuario
        with self.assertRaises(ValidationError):
            self.curso.full_clean()
        self.usuario.groups.add(Group.objects.get(name='Coordenadores'))
        self.curso.full_clean()
        self.usuario.is_active = False
        self.usuario.save()
        with self.assertRaises(ValidationError):
            self.curso.full_clean()

    def test_admin_exibe_perfis_e_coordenador(self):
        admin = get_user_model().objects.create_superuser('admin', 'admin@example.test', 'senha')
        self.client.force_login(admin)
        resposta = self.client.get(reverse('admin:usuarios_usuario_change', args=[self.usuario.pk]))
        self.assertContains(resposta, 'perfil_aluno')
        self.assertContains(resposta, 'perfil_professor')
        self.assertContains(self.client.get(reverse('admin:monografias_curso_change', args=[self.curso.pk])), 'coordenador')

    def test_curso_com_aluno_sem_monografia_tambem_e_protegido(self):
        PerfilAluno.objects.create(usuario=self.usuario, matricula='2026001', curso=self.curso)
        admin = get_user_model().objects.create_superuser('admin', 'admin@example.test', 'senha')
        self.client.force_login(admin)
        resposta = self.client.post(reverse('excluir_curso', args=[self.curso.pk]))
        self.assertContains(resposta, 'registros acadêmicos vinculados', status_code=409)
        self.assertTrue(Curso.objects.filter(pk=self.curso.pk).exists())
