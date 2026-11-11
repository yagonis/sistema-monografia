from datetime import timedelta
from decimal import Decimal
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import PermissionDenied, ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from monografias.tests import DadosMonografiaTests
from monografias.models import Banca, MembroBanca, Avaliacao, Documento, Evento
from monografias import servicos as s
from django.core.files.uploadedfile import SimpleUploadedFile


class CicloBackendTests(DadosMonografiaTests):
    def setUp(self):
        super().setUp()
        self.professor.email = 'professor@example.test'
        self.professor.save()
        self.trabalho.status = 'aprovada_orientador'
        self.trabalho.save()
        self.api = APIClient()
        self.api.force_authenticate(self.professor)
        self.dados = {'data_hora': timezone.now() + timedelta(days=1), 'fim': timezone.now() + timedelta(days=1, hours=1), 'local': 'Sala 1'}

    def banca(self):
        return s.salvar_banca(self.professor, self.trabalho, self.dados)

    def membro(self, banca):
        membro, token = s.convidar(self.professor, banca, {'usuario': self.professor})
        return s.confirmar(membro, self.professor)

    def test_fluxo_banca_agendamento_e_resultado(self):
        banca = self.banca()
        membro = self.membro(banca)
        s.agendar(self.professor, banca.pk)
        Banca.objects.filter(pk=banca.pk).update(data_hora=timezone.now()-timedelta(hours=2), fim=timezone.now()-timedelta(hours=1))
        s.avaliar(membro, {'nota': 8, 'parecer': 'Bom trabalho', 'recomendacao': 'aprovado'}, self.professor)
        banca = s.fechar_resultado(banca.pk)
        self.assertEqual(banca.nota_final, Decimal('8'))
        self.assertEqual(banca.status, 'realizada')
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'aprovada')
        self.assertFalse(s.publicar_se_pronta(self.trabalho.pk))
        with self.assertRaises(ValidationError):
            s.avaliar(membro, {'nota': 9, 'parecer': 'Alterar', 'recomendacao': 'aprovado'}, self.professor)

    def test_agendamento_sem_confirmacoes_nao_funciona(self):
        banca = self.banca()
        s.convidar(self.professor, banca, {'usuario': self.professor})
        with self.assertRaises(ValidationError):
            s.agendar(self.professor, banca.pk)

    def test_sem_aprovacao_ou_sem_vinculo_nao_prepara(self):
        with self.assertRaises(PermissionDenied):
            s.salvar_banca(self.outro, self.trabalho, self.dados)
        self.trabalho.status = 'rascunho'
        self.trabalho.save()
        with self.assertRaises(ValidationError):
            self.banca()

    def test_conflito_mesmo_professor_bloqueia(self):
        banca = self.banca()
        self.membro(banca)
        s.agendar(self.professor, banca.pk)
        outro = type(self.trabalho).objects.create(titulo='Outro trabalho', autor=self.aluno, curso=self.curso,
            orientador=self.professor, arquivo=self.trabalho.arquivo.name, hash_sha256=self.trabalho.hash_sha256,
            status='aprovada_orientador')
        segunda = s.salvar_banca(self.professor, outro, self.dados)
        self.membro(segunda)
        with self.assertRaises(ValidationError):
            s.agendar(self.professor, segunda.pk)

    def test_token_externo_expira_e_nao_pode_ser_usado_por_outro_logado(self):
        banca = self.banca()
        membro, token = s.convidar(self.professor, banca, {'nome': 'Externo', 'email': 'externo@example.test'})
        self.assertNotEqual(token, membro.token_hash)
        self.assertEqual(s.membro_por_token(token).pk, membro.pk)
        with self.assertRaises(PermissionDenied):
            s.confirmar(membro, self.aluno)
        s.confirmar(s.membro_por_token(token))
        membro.expira_em = timezone.now()-timedelta(seconds=1)
        membro.save()
        with self.assertRaises(PermissionDenied):
            s.membro_por_token(token)

    def test_api_publica_nao_expoe_rascunhos(self):
        self.api.force_authenticate(None)
        resposta = self.api.get('/api/publicadas/')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.data['count'], 0)
        self.assertEqual(self.api.get(f'/api/publicadas/{self.trabalho.pk}/').status_code, 404)

    def test_aluno_nao_pode_forjar_aprovacao_via_patch(self):
        self.api.force_authenticate(self.aluno)
        resposta = self.api.patch(f'/api/monografias/{self.trabalho.pk}/', {'status': 'publicada'}, format='json')
        self.assertEqual(resposta.status_code, 403)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'aprovada_orientador')

    def test_resultado_so_fecha_com_todas_e_faz_media(self):
        banca = self.banca()
        primeiro = self.membro(banca)
        segundo, token = s.convidar(self.professor, banca, {'nome': 'Externo', 'email': 'externo@example.test'})
        s.confirmar(segundo)
        s.agendar(self.professor, banca.pk)
        Banca.objects.filter(pk=banca.pk).update(data_hora=timezone.now()-timedelta(hours=2), fim=timezone.now()-timedelta(hours=1))
        s.avaliar(primeiro, {'nota': 8, 'parecer': 'Bom', 'recomendacao': 'aprovado'}, self.professor)
        self.assertIsNone(s.fechar_resultado(banca.pk).encerrada_em)
        s.avaliar(segundo, {'nota': 6, 'parecer': 'Revisar', 'recomendacao': 'ressalvas'})
        resultado = s.fechar_resultado(banca.pk)
        self.assertEqual(resultado.nota_final, Decimal('7'))
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'ressalvas')

    def test_publicacao_exige_termo_e_corrigida_validos(self):
        self.trabalho.status = 'ressalvas'
        self.trabalho.save()
        termo = Documento.objects.create(monografia=self.trabalho, tipo='termo',
            arquivo=SimpleUploadedFile('termo.pdf', self.pdf), hash_sha256=__import__('hashlib').sha256(self.pdf).hexdigest())
        s.validar_documento(self.professor, termo.pk)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'ressalvas')
        corrigida = Documento.objects.create(monografia=self.trabalho, tipo='corrigida',
            arquivo=SimpleUploadedFile('corrigida.pdf', self.pdf), hash_sha256=termo.hash_sha256)
        s.validar_documento(self.professor, corrigida.pk)
        self.trabalho.refresh_from_db()
        self.assertEqual(self.trabalho.status, 'publicada')
        self.assertTrue(Evento.objects.filter(tipo='monografia_publicada').exists())

    def test_api_cria_banca_e_impede_edicao_por_aluno(self):
        dados = {**self.dados, 'monografia': self.trabalho.pk}
        resposta = self.api.post('/api/bancas/', dados, format='json')
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.api.force_authenticate(self.aluno)
        resposta = self.api.patch(f"/api/bancas/{resposta.data['id']}/", {'local': 'Sala 2'}, format='json')
        self.assertEqual(resposta.status_code, 403)


    def test_convidado_interno_ve_horario_antes_de_confirmar(self):
        banca = self.banca()
        self.outro.email = 'outro@example.test'
        self.outro.save()
        s.convidar(self.professor, banca, {'usuario': self.outro})
        self.api.force_authenticate(self.outro)
        self.assertEqual(self.api.get(f'/api/bancas/{banca.pk}/').status_code, 200)
        self.assertEqual(self.api.get(f'/api/monografias/{self.trabalho.pk}/pdf/').status_code, 404)

    def test_mesma_pessoa_nao_e_duplicada_como_externo(self):
        banca = self.banca()
        self.membro(banca)
        with self.assertRaises(ValidationError):
            s.convidar(self.professor, banca, {'nome': 'Mesmo professor', 'email': self.professor.email.upper()})

    def test_alteracao_de_banca_agendada_exige_novas_confirmacoes(self):
        banca = self.banca()
        membro = self.membro(banca)
        s.agendar(self.professor, banca.pk)
        alterada = s.salvar_banca(self.professor, self.trabalho, {'local': 'Outra sala'}, instancia=banca)
        membro.refresh_from_db()
        self.assertEqual(alterada.status, 'em_preparacao')
        self.assertFalse(membro.confirmado)


class SegurancaAPITests(DadosMonografiaTests):
    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()
        self.api = APIClient(enforce_csrf_checks=True)

    def test_login_json_exige_csrf_e_nao_aceita_senha_errada(self):
        resposta = self.api.post('/api/conta/', {'login': 'aluno', 'password': 'senha-teste'}, format='json')
        self.assertEqual(resposta.status_code, 403)
        token = self.api.get('/api/conta/').data['csrfToken']
        resposta = self.api.post('/api/conta/', {'login': 'aluno', 'password': 'senha-teste'}, format='json', HTTP_X_CSRFTOKEN=token)
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertTrue(self.api.get('/api/conta/').data['autenticado'])

    def test_admin_rejeita_origem_nao_autorizada_sem_confiar_em_proxy(self):
        resposta = self.client.get('/admin/login/', REMOTE_ADDR='203.0.113.5', HTTP_X_FORWARDED_FOR='127.0.0.1')
        self.assertEqual(resposta.status_code, 403)

    def test_pdf_privado_e_usuarios_nao_sao_publicos(self):
        self.assertEqual(self.api.get(f'/api/monografias/{self.trabalho.pk}/pdf/').status_code, 403)
        self.assertEqual(self.api.get('/api/usuarios/').status_code, 403)

    def test_documento_de_outro_autor_nao_pode_ser_enviado(self):
        self.api.force_authenticate(self.sem_perfil)
        resposta = self.api.post('/api/documentos/', {'monografia': self.trabalho.pk, 'tipo': 'termo',
            'arquivo': SimpleUploadedFile('termo.pdf', self.pdf)}, format='multipart')
        self.assertEqual(resposta.status_code, 403)

    def test_submissao_cria_evento_e_auditoria(self):
        from monografias.models import Auditoria
        self.trabalho.status = 'rascunho'
        self.trabalho.save()
        self.api.force_authenticate(self.aluno)
        resposta = self.api.post(f'/api/monografias/{self.trabalho.pk}/submeter/')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        self.assertTrue(Evento.objects.filter(tipo='monografia_submetida').exists())
        self.assertTrue(Auditoria.objects.filter(acao='submissao', ator=self.aluno).exists())

    def test_admin_api_tambem_exige_rede_institucional(self):
        admin = get_user_model().objects.create_superuser('admin-api', 'admin@example.test', 'senha')
        self.api.force_authenticate(admin)
        self.assertEqual(self.api.get('/api/usuarios/', REMOTE_ADDR='203.0.113.5').status_code, 403)
        self.assertEqual(self.api.get('/api/usuarios/', REMOTE_ADDR='127.0.0.1').status_code, 200)
