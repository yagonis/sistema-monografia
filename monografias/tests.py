import hashlib
import io
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from pypdf import PdfWriter

from .forms import MonografiaForm
from .models import Curso, Monografia
from .validadores import validar_pdf


class FluxoOrientacaoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        Usuario = get_user_model()
        cls.aluno = Usuario.objects.create_user('aluno', password='senha-teste')
        cls.professor = Usuario.objects.create_user('professor', password='senha-teste')
        cls.outro = Usuario.objects.create_user('outro-professor', password='senha-teste')
        cls.sem_perfil = Usuario.objects.create_user('sem-perfil', password='senha-teste')
        cls.aluno.groups.add(Group.objects.get(name='Alunos'))
        for professor in [cls.professor, cls.outro]:
            professor.groups.add(Group.objects.get(name='Professores'))
        cls.curso = Curso.objects.create(nome='Sistemas', codigo='SI')

    def setUp(self):
        self.diretorio = tempfile.TemporaryDirectory()
        self.addCleanup(self.diretorio.cleanup)
        self.configuracao = override_settings(MEDIA_ROOT=self.diretorio.name)
        self.configuracao.enable()
        self.addCleanup(self.configuracao.disable)
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.write(buffer)
        self.pdf = buffer.getvalue()
        self.trabalho = Monografia.objects.create(
            titulo='Trabalho do aluno', curso=self.curso, autor=self.aluno,
            orientador=self.professor, arquivo=SimpleUploadedFile('trabalho.pdf', self.pdf),
            hash_sha256=hashlib.sha256(self.pdf).hexdigest(), status='em_avaliacao',
        )

    def aprovar(self):
        return self.client.post(reverse('aprovar_orientacao', args=[self.trabalho.pk]))

    def test_visitante_precisa_login(self):
        for nome in ['orientacoes', 'meus_rascunhos', 'minhas_monografias', 'enviar_rascunho']:
            resposta = self.client.get(reverse(nome))
            self.assertEqual(resposta.status_code, 302)
            self.assertIn('/contas/login/', resposta.url)

    def test_login_allauth_e_logout(self):
        self.assertEqual(self.client.get(reverse('account_login')).status_code, 200)
        resposta = self.client.post(reverse('account_login'), {'login': 'professor', 'password': 'senha-teste'})
        self.assertRedirects(resposta, reverse('inicio'))
        self.assertContains(self.client.get(reverse('inicio')), 'Área do professor')
        self.client.post(reverse('account_logout'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_senha_incorreta_e_conta_inativa_nao_autenticam(self):
        self.client.post(reverse('account_login'), {'login': 'professor', 'password': 'incorreta'})
        self.assertNotIn('_auth_user_id', self.client.session)
        self.professor.is_active = False
        self.professor.save()
        self.client.post(reverse('account_login'), {'login': 'professor', 'password': 'senha-teste'})
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cadastro_publico_fechado(self):
        resposta = self.client.get(reverse('account_signup'))
        self.assertContains(resposta, 'Cadastro fechado')

    def test_aluno_nao_acessa_area_professor_nem_aprova(self):
        self.client.force_login(self.aluno)
        self.assertEqual(self.client.get(reverse('orientacoes')).status_code, 403)
        self.assertEqual(self.aprovar().status_code, 403)

    def test_professor_nao_acessa_operacoes_aluno(self):
        self.client.force_login(self.professor)
        for nome in ['meus_rascunhos', 'enviar_rascunho', 'minhas_monografias']:
            self.assertEqual(self.client.get(reverse(nome)).status_code, 403)
        self.assertEqual(self.client.post(reverse('submeter_rascunho', args=[self.trabalho.pk])).status_code, 403)

    def test_sem_perfil_nao_recebe_acesso_academico(self):
        self.client.force_login(self.sem_perfil)
        self.assertEqual(self.client.get(reverse('orientacoes')).status_code, 403)
        self.assertEqual(self.client.get(reverse('enviar_rascunho')).status_code, 403)

    def test_professor_ve_apenas_submetidos_sob_sua_orientacao(self):
        self.client.force_login(self.professor)
        self.assertContains(self.client.get(reverse('orientacoes')), self.trabalho.titulo)
        self.trabalho.status = 'rascunho'
        self.trabalho.save()
        self.assertNotContains(self.client.get(reverse('orientacoes')), self.trabalho.titulo)
        self.client.force_login(self.outro)
        self.assertNotContains(self.client.get(reverse('orientacoes')), self.trabalho.titulo)

    def test_outro_professor_nao_aprova_nem_baixa(self):
        self.client.force_login(self.outro)
        self.assertEqual(self.aprovar().status_code, 404)
        self.assertEqual(self.client.get(reverse('baixar_pdf', args=[self.trabalho.pk])).status_code, 404)

    def test_aprovacao_registra_responsavel_data_e_estado(self):
        self.client.force_login(self.professor)
        self.assertRedirects(self.aprovar(), reverse('orientacoes'))
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'aprovada_orientador')
        self.assertEqual(self.trabalho.aprovado_por, self.professor)
        self.assertIsNotNone(self.trabalho.aprovado_em)
        self.assertEqual(self.aprovar().status_code, 404)

    def test_get_e_post_sem_csrf_nao_aprovam(self):
        self.client.force_login(self.professor)
        url = reverse('aprovar_orientacao', args=[self.trabalho.pk])
        self.assertEqual(self.client.get(url).status_code, 405)
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.professor)
        self.assertEqual(cliente.post(url).status_code, 403)

    def test_rascunho_nao_pode_ser_aprovado_ou_baixado_por_professor(self):
        self.trabalho.status = 'rascunho'
        self.trabalho.save()
        self.client.force_login(self.professor)
        self.assertEqual(self.aprovar().status_code, 404)
        self.assertEqual(self.client.get(reverse('baixar_pdf', args=[self.trabalho.pk])).status_code, 404)

    def test_pdf_alterado_bloqueia_aprovacao(self):
        Path(self.trabalho.arquivo.path).write_bytes(b'arquivo adulterado')
        self.client.force_login(self.professor)
        self.aprovar()
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'em_avaliacao')
        self.assertIsNone(self.trabalho.aprovado_em)

    def test_download_privado_para_autor_e_orientador(self):
        url = reverse('baixar_pdf', args=[self.trabalho.pk])
        for usuario in [self.aluno, self.professor]:
            self.client.force_login(usuario)
            resposta = self.client.get(url)
            self.assertEqual(resposta.status_code, 200)
            self.assertEqual(b''.join(resposta.streaming_content), self.pdf)
            resposta.close()
        self.client.force_login(self.sem_perfil)
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_acompanhamento_mantem_submetidos_e_bloqueia_edicao(self):
        self.client.force_login(self.aluno)
        self.assertContains(self.client.get(reverse('minhas_monografias')), self.trabalho.titulo)
        self.assertNotContains(self.client.get(reverse('meus_rascunhos')), self.trabalho.titulo)
        self.assertEqual(self.client.post(reverse('editar_rascunho', args=[self.trabalho.pk]), {'titulo': 'alterado'}).status_code, 404)

    def test_submissao_requer_orientador_ativo_do_grupo(self):
        self.trabalho.status = 'rascunho'
        self.trabalho.orientador = self.sem_perfil
        self.trabalho.save()
        self.client.force_login(self.aluno)
        url = reverse('submeter_rascunho', args=[self.trabalho.pk])
        self.client.post(url)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'rascunho')
        self.trabalho.orientador = self.professor
        self.trabalho.save()
        self.client.post(url)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'em_avaliacao')

    def test_formulario_valida_pdf_e_calcula_hash(self):
        form = MonografiaForm(
            {'titulo': 'Novo', 'curso': self.curso.pk, 'orientador': self.professor.pk},
            {'arquivo': SimpleUploadedFile('novo.pdf', self.pdf)},
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.instance.hash_sha256, hashlib.sha256(self.pdf).hexdigest())
        arquivo = SimpleUploadedFile('grande.pdf', b'%PDF-')
        arquivo.size = 50 * 1024 * 1024 + 1
        with self.assertRaises(ValidationError):
            validar_pdf(arquivo)

    def test_criacao_submissao_e_aprovacao_completas(self):
        self.client.force_login(self.aluno)
        resposta = self.client.post(reverse('enviar_rascunho'), {
            'titulo': 'Fluxo completo', 'curso': self.curso.pk, 'orientador': self.professor.pk,
            'arquivo': SimpleUploadedFile('novo.pdf', self.pdf),
        })
        self.assertRedirects(resposta, reverse('meus_rascunhos'))
        trabalho = Monografia.objects.get(titulo='Fluxo completo')
        self.assertEqual(trabalho.autor, self.aluno)
        self.assertEqual(trabalho.status, 'rascunho')
        self.client.post(reverse('submeter_rascunho', args=[trabalho.pk]))
        self.client.force_login(self.professor)
        self.assertContains(self.client.get(reverse('orientacoes')), 'Fluxo completo')
        self.client.post(reverse('aprovar_orientacao', args=[trabalho.pk]))
        trabalho.refresh_from_db()
        self.assertEqual(trabalho.status, 'aprovada_orientador')

    def test_outro_aluno_nao_consulta_nem_edita_trabalho(self):
        outro = get_user_model().objects.create_user('outro-aluno')
        outro.groups.add(Group.objects.get(name='Alunos'))
        self.client.force_login(outro)
        self.assertNotContains(self.client.get(reverse('minhas_monografias')), self.trabalho.titulo)
        self.assertEqual(self.client.get(reverse('baixar_pdf', args=[self.trabalho.pk])).status_code, 404)
        self.trabalho.status = 'rascunho'
        self.trabalho.save()
        self.assertEqual(self.client.post(reverse('editar_rascunho', args=[self.trabalho.pk])).status_code, 404)

    def test_arquivo_ausente_nao_aprova(self):
        Path(self.trabalho.arquivo.path).unlink()
        self.client.force_login(self.professor)
        self.aprovar()
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'em_avaliacao')

    def test_professor_inativo_nao_pode_ser_escolhido_no_formulario(self):
        self.professor.is_active = False
        self.professor.save()
        form = MonografiaForm(
            {'titulo': 'Novo', 'curso': self.curso.pk, 'orientador': self.professor.pk},
            {'arquivo': SimpleUploadedFile('novo.pdf', self.pdf)},
        )
        self.assertFalse(form.is_valid())
        self.assertIn('orientador', form.errors)
