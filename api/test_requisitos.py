"""Sequência de verificação dos requisitos do enunciado (Trabalho de Sistemas Distribuídos).

Cada teste afirma o comportamento pedido pelo enunciado. Uma falha indica divergência
entre o sistema e o requisito citado no nome/docstring do teste.

Executar:
    python manage.py test api.test_requisitos --settings=config.settings_test -v 2
"""
import hashlib
import io
from datetime import timedelta
from unittest import mock

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core import mail
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from pypdf import PdfWriter
from rest_framework.test import APIClient

from monografias import servicos as s
from monografias.models import Auditoria, Banca, Documento, Evento, Monografia
from monografias.tasks import processar_evento
from monografias.tests import DadosMonografiaTests


def pdf_com_texto(texto):
    """PDF mínimo válido com uma página contendo `texto` extraível."""
    conteudo = f'BT /F1 12 Tf 10 100 Td ({texto}) Tj ET'.encode()
    objetos = [
        b'<< /Type /Catalog /Pages 2 0 R >>',
        b'<< /Type /Pages /Kids [3 0 R] /Count 1 >>',
        b'<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] /Contents 4 0 R '
        b'/Resources << /Font << /F1 5 0 R >> >> >>',
        b'<< /Length %d >>\nstream\n' % len(conteudo) + conteudo + b'\nendstream',
        b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>',
    ]
    saida = io.BytesIO()
    saida.write(b'%PDF-1.4\n')
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(saida.tell())
        saida.write(b'%d 0 obj\n' % numero + corpo + b'\nendobj\n')
    xref = saida.tell()
    saida.write(b'xref\n0 %d\n0000000000 65535 f \n' % (len(objetos) + 1))
    for pos in posicoes:
        saida.write(b'%010d 00000 n \n' % pos)
    saida.write(b'trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (len(objetos) + 1, xref))
    return saida.getvalue()


def pdf_variante(i):
    buffer = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100 + i, height=100)
    writer.write(buffer)
    return buffer.getvalue()


class BaseRequisitos(DadosMonografiaTests):
    def setUp(self):
        super().setUp()
        Usuario = get_user_model()
        self.aluno.email = 'aluno@example.test'
        self.aluno.save()
        self.professor.first_name, self.professor.last_name = 'Orientadora', 'Silva'
        self.professor.email = 'professor@example.test'
        self.professor.save()
        self.outro.email = 'outro@example.test'
        self.outro.save()
        self.coordenador = Usuario.objects.create_user('coord', 'coord@example.test', 'senha-teste')
        self.coordenador.groups.add(Group.objects.get(name='Coordenadores'))
        self.curso.coordenador = self.coordenador
        self.curso.save()
        self.api = APIClient()

    # ---------- auxiliares ----------
    def como(self, usuario):
        self.api.force_authenticate(usuario)
        return self.api

    def nova(self, status='rascunho', pdf=None, titulo='Outro trabalho', **extra):
        pdf = pdf or pdf_variante(Monografia.objects.count() + 1)
        return Monografia.objects.create(
            titulo=titulo, curso=self.curso, autor=self.aluno, orientador=self.professor,
            arquivo=SimpleUploadedFile('t.pdf', pdf), hash_sha256=hashlib.sha256(pdf).hexdigest(),
            status=status, **extra)

    def banca_agendada(self, trabalho, externo=False, inicio_dias=1):
        inicio = timezone.now() + timedelta(days=inicio_dias)
        banca = s.salvar_banca(self.professor, trabalho, {'data_hora': inicio, 'fim': inicio + timedelta(hours=1), 'local': 'Sala 1'})
        interno, _ = s.convidar(self.professor, banca, {'usuario': self.professor})
        s.confirmar(interno, self.professor)
        membros, token = [interno], None
        if externo:
            ext, token = s.convidar(self.professor, banca, {'nome': 'Externo', 'email': 'externo@example.test'})
            s.confirmar(ext)
            membros.append(ext)
        s.agendar(self.professor, banca.pk)
        return banca, membros, token

    def encerrar_defesa(self, banca):
        Banca.objects.filter(pk=banca.pk).update(
            data_hora=timezone.now() - timedelta(hours=2), fim=timezone.now() - timedelta(hours=1))

    def documento(self, trabalho, tipo, pdf=None):
        pdf = pdf or pdf_variante(500 + Documento.objects.count())
        return Documento.objects.create(monografia=trabalho, tipo=tipo, arquivo=SimpleUploadedFile(f'{tipo}.pdf', pdf),
                                        hash_sha256=hashlib.sha256(pdf).hexdigest())

    def publicar(self, trabalho, recomendacao='aprovado', palavras=''):
        Monografia.objects.filter(pk=trabalho.pk).update(status='aprovada_orientador', palavras_chave=palavras,
                                                         submetida_em=timezone.now() - timedelta(days=30))
        banca, membros, _ = self.banca_agendada(trabalho)
        self.encerrar_defesa(banca)
        s.avaliar(membros[0], {'nota': 9, 'parecer': 'Ok', 'recomendacao': recomendacao}, self.professor)
        s.fechar_resultado(banca.pk)
        s.validar_documento(self.professor, self.documento(trabalho, 'termo').pk)
        if recomendacao == 'ressalvas':
            s.validar_documento(self.professor, self.documento(trabalho, 'corrigida').pk)
        trabalho.refresh_from_db()
        return trabalho


class R01Autenticacao(BaseRequisitos):
    def test_01_senha_fraca_recusada_na_criacao_de_usuario(self):
        """Políticas de senha seguras também na API administrativa."""
        admin = get_user_model().objects.create_superuser('adm', 'adm@example.test', 'senha-forte-123')
        resposta = self.como(admin).post('/api/usuarios/', {'username': 'novo', 'password': '123'}, format='json',
                                         REMOTE_ADDR='127.0.0.1')
        self.assertEqual(resposta.status_code, 400, resposta.data)

    def test_02_senha_armazenada_com_hash(self):
        self.assertNotEqual(self.aluno.password, 'senha-teste')
        self.assertTrue(self.aluno.check_password('senha-teste'))

    def test_03_restritos_exigem_autenticacao(self):
        for url in ['/api/monografias/', '/api/bancas/', '/api/avaliacoes/', '/api/alunos/', '/api/relatorios/']:
            self.assertIn(self.api.get(url).status_code, (401, 403), url)

    def test_04_dashboard_por_perfil(self):
        conta = self.como(self.coordenador).get('/api/conta/').data
        self.assertIn('Coordenadores', conta['usuario']['grupos'])


class R02Submissao(BaseRequisitos):
    def criar(self, pdf, nome='trab.pdf', **campos):
        dados = {'titulo': 'Novo', 'resumo': 'r', 'palavras_chave': 'k', 'curso': self.curso.pk,
                 'orientador': self.professor.pk, 'arquivo': SimpleUploadedFile(nome, pdf), **campos}
        return self.como(self.aluno).post('/api/monografias/', dados, format='multipart')

    def test_01_upload_valido_calcula_sha256(self):
        pdf = pdf_variante(1)
        resposta = self.criar(pdf)
        self.assertEqual(resposta.status_code, 201, resposta.data)
        self.assertEqual(resposta.data['hash_sha256'], hashlib.sha256(pdf).hexdigest())
        self.assertEqual(resposta.data['status'], 'rascunho')

    def test_02_extensao_nao_pdf_recusada(self):
        self.assertEqual(self.criar(pdf_variante(2), nome='trab.txt').status_code, 400)

    def test_03_conteudo_falso_com_extensao_pdf_recusado(self):
        self.assertEqual(self.criar(b'nao sou pdf', nome='falso.pdf').status_code, 400)

    def test_04_pdf_com_senha_recusado(self):
        buffer = io.BytesIO()
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt('segredo')
        writer.write(buffer)
        self.assertEqual(self.criar(buffer.getvalue()).status_code, 400)

    def test_05_arquivo_acima_de_50mb_recusado(self):
        grande = b'%PDF-1.4\n' + b'0' * (50 * 1024 * 1024)
        self.assertEqual(self.criar(grande).status_code, 400)

    def test_06_pdf_duplicado_do_mesmo_autor_recusado(self):
        pdf = pdf_variante(3)
        self.assertEqual(self.criar(pdf).status_code, 201)
        self.assertEqual(self.criar(pdf).status_code, 400)

    def test_07_rate_limit_de_submissoes(self):
        codigos = [self.criar(pdf_variante(10 + i)).status_code for i in range(12)]
        self.assertIn(429, codigos, codigos)

    def test_08_submeter_sem_orientador_recusado(self):
        trabalho = self.nova()
        Monografia.objects.filter(pk=trabalho.pk).update(orientador=None)
        resposta = self.como(self.aluno).post(f'/api/monografias/{trabalho.pk}/submeter/')
        self.assertEqual(resposta.status_code, 400)

    def test_09_submissao_marca_upload_em_andamento_no_redis(self):
        trabalho = self.nova()
        self.assertEqual(self.como(self.aluno).post(f'/api/monografias/{trabalho.pk}/submeter/').status_code, 200)
        self.assertTrue(cache.get(f'upload_em_andamento:{trabalho.pk}'))

    def test_10_somente_orientador_vinculado_aprova(self):
        self.assertIn(self.como(self.outro).post(f'/api/monografias/{self.trabalho.pk}/aprovar/').status_code, (403, 404))
        self.assertIn(self.como(self.aluno).post(f'/api/monografias/{self.trabalho.pk}/aprovar/').status_code, (403, 404))
        self.assertEqual(self.como(self.professor).post(f'/api/monografias/{self.trabalho.pk}/aprovar/').status_code, 200)

    def test_11_aluno_nao_ve_monografia_de_outro_aluno(self):
        intruso = get_user_model().objects.create_user('intruso', password='x')
        intruso.groups.add(Group.objects.get(name='Alunos'))
        self.assertEqual(self.como(intruso).get(f'/api/monografias/{self.trabalho.pk}/').status_code, 404)


class R03Banca(BaseRequisitos):
    def setUp(self):
        super().setUp()
        Monografia.objects.filter(pk=self.trabalho.pk).update(status='aprovada_orientador')
        self.trabalho.refresh_from_db()
        self.inicio = timezone.now() + timedelta(days=2)
        self.dados = {'monografia': self.trabalho.pk, 'data_hora': self.inicio.isoformat(),
                      'fim': (self.inicio + timedelta(hours=1)).isoformat(), 'local': 'Sala 3'}

    def test_01_banca_sem_aprovacao_do_orientador_recusada(self):
        Monografia.objects.filter(pk=self.trabalho.pk).update(status='em_avaliacao')
        self.assertEqual(self.como(self.professor).post('/api/bancas/', self.dados, format='json').status_code, 400)

    def test_02_coordenador_do_curso_pode_agendar(self):
        self.assertEqual(self.como(self.coordenador).post('/api/bancas/', self.dados, format='json').status_code, 201)

    def test_03_link_remoto_aceito(self):
        dados = {**self.dados, 'local': '', 'link': 'https://meet.example.test/abc'}
        self.assertEqual(self.como(self.professor).post('/api/bancas/', dados, format='json').status_code, 201)

    def test_04_fluxo_externo_por_token(self):
        api = self.como(self.professor)
        banca = api.post('/api/bancas/', self.dados, format='json').data
        convite = api.post('/api/membros/', {'banca': banca['id'], 'nome': 'Ext', 'email': 'ext@example.test'}, format='json')
        self.assertEqual(convite.status_code, 201, convite.data)
        token = convite.data['token_temporario']
        anonimo = APIClient()
        self.assertEqual(anonimo.get('/api/externo/', HTTP_X_BANCA_TOKEN='invalido').status_code, 403)
        self.assertEqual(anonimo.post('/api/externo/', {'acao': 'confirmar'}, format='json', HTTP_X_BANCA_TOKEN=token).status_code, 200)
        self.assertEqual(api.post(f"/api/bancas/{banca['id']}/agendar/").status_code, 200)
        # antes da defesa: avaliação bloqueada
        avaliacao = {'nota': '7.0', 'parecer': 'p', 'recomendacao': 'aprovado'}
        self.assertEqual(anonimo.post('/api/externo/', avaliacao, format='json', HTTP_X_BANCA_TOKEN=token).status_code, 400)
        Banca.objects.filter(pk=banca['id']).update(data_hora=timezone.now() - timedelta(hours=2), fim=timezone.now() - timedelta(hours=1))
        self.assertEqual(anonimo.post('/api/externo/', avaliacao, format='json', HTTP_X_BANCA_TOKEN=token).status_code, 200)

    def test_05_conflito_de_horario_com_membro_externo(self):
        primeira, _, _ = self.banca_agendada(self.trabalho, externo=True)
        outro = self.nova(status='aprovada_orientador')
        segunda = s.salvar_banca(self.professor, outro, {'data_hora': primeira.data_hora, 'fim': primeira.fim, 'local': 'X'})
        self.outro.groups.add(Group.objects.get(name='Professores'))
        m1, _ = s.convidar(self.professor, segunda, {'usuario': self.outro})
        s.confirmar(m1, self.outro)
        m2, _ = s.convidar(self.professor, segunda, {'nome': 'Externo', 'email': 'EXTERNO@example.test'})
        s.confirmar(m2)
        with self.assertRaises(Exception):
            s.agendar(self.professor, segunda.pk)

    def test_06_nota_fora_da_escala_recusada(self):
        banca, membros, _ = self.banca_agendada(self.trabalho)
        self.encerrar_defesa(banca)
        resposta = self.como(self.professor).post('/api/avaliacoes/', {'membro': membros[0].pk, 'nota': '11', 'parecer': 'p',
                                                                     'recomendacao': 'aprovado'}, format='json')
        self.assertEqual(resposta.status_code, 400)

    def test_07_avaliacao_alheia_nao_editavel(self):
        banca, membros, token = self.banca_agendada(self.trabalho, externo=True)
        self.encerrar_defesa(banca)
        avaliacao = s.avaliar(membros[1], {'nota': 8, 'parecer': 'p', 'recomendacao': 'aprovado'})
        resposta = self.como(self.professor).patch(f'/api/avaliacoes/{avaliacao.pk}/', {'nota': '2'}, format='json')
        self.assertIn(resposta.status_code, (403, 404))

    def test_08_resultado_reprovado_nao_publica(self):
        trabalho = self.publicar(self.trabalho, recomendacao='reprovado')
        self.assertEqual(trabalho.status, 'reprovada')

    def test_09_token_revogado_e_renovado_permite_fechar_resultado(self):
        """Revogar após agendamento suspende um token vazado; renovar devolve o acesso e o resultado fecha."""
        banca, membros, token = self.banca_agendada(self.trabalho, externo=True)
        api = self.como(self.professor)
        self.assertEqual(api.post(f'/api/membros/{membros[1].pk}/revogar/').status_code, 204)
        self.assertEqual(APIClient().get('/api/externo/', HTTP_X_BANCA_TOKEN=token).status_code, 403)
        novo = api.post(f'/api/membros/{membros[1].pk}/renovar/').data['token_temporario']
        self.encerrar_defesa(banca)
        s.avaliar(membros[0], {'nota': 8, 'parecer': 'p', 'recomendacao': 'aprovado'}, self.professor)
        avaliacao = {'nota': '6', 'parecer': 'p', 'recomendacao': 'aprovado'}
        self.assertEqual(APIClient().post('/api/externo/', avaliacao, format='json', HTTP_X_BANCA_TOKEN=novo).status_code, 200)
        self.assertIsNotNone(s.fechar_resultado(banca.pk).encerrada_em)

    def test_10_banca_realizada_nao_editavel(self):
        trabalho = self.publicar(self.trabalho)
        banca = trabalho.bancas.get(status='realizada')
        resposta = self.como(self.professor).patch(f'/api/bancas/{banca.pk}/', {'local': 'Nova'}, format='json')
        self.assertEqual(resposta.status_code, 400)


class R04Eventos(BaseRequisitos):
    def ultimo(self, tipo):
        return Evento.objects.filter(tipo=tipo).latest('pk')

    def test_01_submissao_extrai_texto_e_notifica_orientador(self):
        trabalho = self.nova(pdf=pdf_com_texto('SistemasDistribuidosTCC'))
        self.como(self.aluno).post(f'/api/monografias/{trabalho.pk}/submeter/')
        processar_evento(self.ultimo('monografia_submetida').pk)
        trabalho.refresh_from_db()
        self.assertIn('SistemasDistribuidosTCC', trabalho.texto_extraido)
        self.assertIn(self.professor.email, [m.to[0] for m in mail.outbox])
        self.assertIsNone(cache.get(f'upload_em_andamento:{trabalho.pk}'))
        self.assertIsNotNone(self.ultimo('monografia_submetida').processado_em)

    def test_02_agendamento_notifica_membros_e_aluno(self):
        Monografia.objects.filter(pk=self.trabalho.pk).update(status='aprovada_orientador')
        self.banca_agendada(self.trabalho, externo=True)
        processar_evento(self.ultimo('banca_agendada').pk)
        destinos = {m.to[0] for m in mail.outbox}
        self.assertTrue({'aluno@example.test', 'professor@example.test', 'externo@example.test'} <= destinos, destinos)

    def test_03_avaliacao_registrada_fecha_resultado_via_fila(self):
        Monografia.objects.filter(pk=self.trabalho.pk).update(status='aprovada_orientador')
        banca, membros, _ = self.banca_agendada(self.trabalho)
        self.encerrar_defesa(banca)
        s.avaliar(membros[0], {'nota': 7, 'parecer': 'p', 'recomendacao': 'aprovado'}, self.professor)
        processar_evento(self.ultimo('avaliacao_registrada').pk)
        banca.refresh_from_db()
        self.assertEqual(banca.status, 'realizada')

    @override_settings(REPOSITORIO_URL='http://repositorio.test', REPOSITORIO_INTEGRATION_KEY='chave-teste')
    def test_04_publicacao_indexa_e_notifica_aluno(self):
        self.publicar(self.trabalho)
        with mock.patch('urllib.request.urlopen') as urlopen:
            processar_evento(self.ultimo('monografia_publicada').pk)
        requisicao = urlopen.call_args[0][0]
        self.assertTrue(requisicao.full_url.endswith('/internal/indexar/'))
        self.assertEqual(requisicao.get_header('X-integration-key'), 'chave-teste')
        self.assertIn('aluno@example.test', [m.to[0] for m in mail.outbox])


class R05PublicacaoBusca(BaseRequisitos):
    def setUp(self):
        super().setUp()
        self.pub = self.publicar(self.trabalho, palavras='redes, kafka')
        self.anon = APIClient()

    def ids(self, query):
        resposta = self.anon.get(f'/api/publicadas/?{query}')
        self.assertEqual(resposta.status_code, 200, resposta.data)
        return [r['id'] for r in resposta.data['results']]

    def test_01_publicada_automaticamente(self):
        self.assertEqual(self.pub.status, 'publicada')

    def test_02_ressalvas_exigem_corrigida(self):
        outro = self.nova(status='aprovada_orientador')
        Monografia.objects.filter(pk=outro.pk).update(status='ressalvas')
        s.validar_documento(self.professor, self.documento(outro, 'termo').pk)
        outro.refresh_from_db()
        self.assertEqual(outro.status, 'ressalvas')

    def test_03_publico_sem_login_lista_e_baixa(self):
        self.assertIn(self.pub.pk, self.ids(''))
        download = self.anon.get(f'/api/publicadas/{self.pub.pk}/pdf/')
        download.close()
        self.assertEqual(download.status_code, 200)
        self.assertEqual(self.anon.get('/api/cursos/').status_code, 200)
        orientadores = self.anon.get('/api/orientadores/')
        self.assertEqual(orientadores.status_code, 200)
        self.assertNotIn('email', orientadores.data[0])

    def test_04_busca_por_titulo(self):
        self.assertIn(self.pub.pk, self.ids('busca=Trabalho'))

    def test_05_busca_por_autor(self):
        self.assertIn(self.pub.pk, self.ids(f'autor={self.aluno.pk}'))

    def test_06_busca_por_curso_ano_palavras(self):
        ano = timezone.now().year
        self.assertIn(self.pub.pk, self.ids(f'curso={self.curso.pk}&ano_defesa={ano}&palavras_chave=kafka'))
        self.assertNotIn(self.pub.pk, self.ids(f'ano_defesa={ano - 5}'))

    def test_07_busca_por_nome_do_orientador(self):
        """Repositório pesquisável por orientador: visitante digita o nome, não o ID interno."""
        self.assertIn(self.pub.pk, self.ids('busca=Orientadora'))

    def test_08_publicada_nunca_excluida(self):
        admin = get_user_model().objects.create_superuser('adm2', 'a2@example.test', 'senha-forte-123')
        self.assertIn(self.como(admin).delete(f'/api/monografias/{self.pub.pk}/', REMOTE_ADDR='127.0.0.1').status_code, (400, 403, 409))
        self.assertTrue(Monografia.objects.filter(pk=self.pub.pk).exists())

    def test_09_integridade_detecta_arquivo_alterado(self):
        with open(self.pub.arquivo.path, 'wb') as f:
            f.write(pdf_variante(999))
        self.assertNotEqual(self.anon.get(f'/api/publicadas/{self.pub.pk}/pdf/').status_code, 200)

    def test_10_cache_de_busca_publica(self):
        """Redis: cache de resultados de busca do repositório (2ª busca idêntica sem tocar o banco)."""
        self.anon.get('/api/publicadas/?busca=Trabalho')
        with self.assertNumQueries(0):
            self.anon.get('/api/publicadas/?busca=Trabalho')

    def test_10b_nova_publicacao_invalida_cache(self):
        self.assertEqual(len(self.ids('busca=Zookeeper')), 0)  # resultado vazio fica em cache
        outro = self.nova(titulo='Zookeeper em escala')
        with self.captureOnCommitCallbacks(execute=True):
            self.publicar(outro)
        self.assertEqual(len(self.ids('busca=Zookeeper')), 1)

    @override_settings(REPOSITORIO_URL='http://repositorio.test')
    def test_10c_busca_publica_usa_servico_de_repositorio(self):
        """Portal consulta o Serviço de Repositório e Busca, mantendo o formato da API acadêmica."""
        import json as _json
        corpo = {'count': 30, 'page': 1, 'page_size': 25, 'results': [{'id': 77, 'titulo': 'Do repositório'}]}
        resposta = mock.MagicMock()
        resposta.__enter__.return_value.read.return_value = _json.dumps(corpo).encode()
        with mock.patch('api.repositorio.urlopen', return_value=resposta) as urlopen:
            dados = self.anon.get(f'/api/publicadas/?busca=redes&orientador={self.professor.pk}').data
        url = urlopen.call_args[0][0]
        self.assertTrue(url.startswith('http://repositorio.test/api/publicadas/?'))
        self.assertIn(f'orientador_id={self.professor.pk}', url)
        self.assertEqual(dados['results'][0]['id'], 77)
        self.assertIsNotNone(dados['next'])
        self.assertIsNone(dados['previous'])

    @override_settings(REPOSITORIO_URL='http://repositorio.test')
    def test_10d_repositorio_fora_do_ar_usa_consulta_local(self):
        from urllib.error import URLError
        with mock.patch('api.repositorio.urlopen', side_effect=URLError('recusado')) as urlopen:
            self.assertIn(self.pub.pk, self.ids('busca=Trabalho'))
            self.assertIn(self.pub.pk, self.ids('busca=Trabalho+Orientadora'))
        self.assertEqual(urlopen.call_count, 1)  # depois da falha, não tenta de novo por 30 s

    def test_11_visitantes_em_massa_nao_bloqueados(self):
        """Milhares de visitantes (ex.: mesma rede/NAT da instituição) não podem receber 429 na busca."""
        codigos = {self.anon.get('/api/publicadas/').status_code for _ in range(150)}
        self.assertEqual(codigos, {200})


class R08Seguranca(BaseRequisitos):
    """Regressões da revisão de segurança."""

    def setUp(self):
        super().setUp()
        self.anon = APIClient()

    def test_01_throttle_anonimo_ignora_x_forwarded_for_forjado(self):
        """Trocar X-Forwarded-For a cada requisição não pode renovar o limite anônimo (100/h)."""
        codigos = [self.anon.get('/api/health/', HTTP_X_FORWARDED_FOR=f'198.51.100.{i % 250}').status_code
                   for i in range(101)]
        self.assertEqual(codigos[-1], 429, codigos[-5:])

    def test_02_throttle_publico_ignora_x_forwarded_for_forjado(self):
        from rest_framework.settings import api_settings
        with mock.patch.dict(api_settings.DEFAULT_THROTTLE_RATES, {'publico': '5/hour'}):
            codigos = [self.anon.get('/api/cursos/', HTTP_X_FORWARDED_FOR=f'198.51.100.{i}').status_code for i in range(6)]
        self.assertEqual(codigos[-1], 429, codigos)

    def test_03_busca_publica_nao_revela_username(self):
        self.aluno.username, self.aluno.first_name, self.aluno.last_name = 'login2026xyz', 'Ana', 'Souza'
        self.aluno.save()
        pub = self.publicar(self.trabalho)
        resposta = self.anon.get('/api/publicadas/?busca=login2026xyz')
        self.assertEqual(resposta.data['count'], 0)
        self.assertEqual(self.anon.get('/api/publicadas/?busca=Souza').data['results'][0]['id'], pub.pk)

    @override_settings(REPOSITORIO_URL='http://repositorio.test', REPOSITORIO_INTEGRATION_KEY='k')
    def test_04_indexacao_nao_envia_username_sem_nome(self):
        import json as _json
        self.aluno.first_name = self.aluno.last_name = ''
        self.aluno.username = 'login2026xyz'
        self.aluno.save()
        self.publicar(self.trabalho)
        with mock.patch('urllib.request.urlopen') as urlopen:
            processar_evento(Evento.objects.filter(tipo='monografia_publicada').latest('pk').pk)
        corpo = _json.loads(urlopen.call_args[0][0].data)
        self.assertNotIn(self.aluno.username, _json.dumps(corpo))
        self.assertEqual(corpo['autor'], 'Não informado')

    def test_05_busca_com_termos_demais_recusada(self):
        self.assertEqual(self.anon.get('/api/publicadas/?busca=' + '+'.join('abcdefgh')).status_code, 200)
        self.assertEqual(self.anon.get('/api/publicadas/?busca=' + '+'.join('abcdefghi')).status_code, 400)
        privada = self.como(self.aluno).get('/api/monografias/?busca=' + '+'.join('abcdefghi'))
        self.assertEqual(privada.status_code, 400)

    @override_settings(REPOSITORIO_URL='http://repositorio.test')
    def test_06_limite_de_termos_vale_antes_do_repositorio(self):
        with mock.patch('api.repositorio.urlopen') as urlopen:
            resposta = self.anon.get('/api/publicadas/?busca=' + '+'.join('abcdefghi'))
        self.assertEqual(resposta.status_code, 400)
        urlopen.assert_not_called()


class R06CrudApi(BaseRequisitos):
    def test_01_busca_em_api_monografias(self):
        """Enunciado: GET /api/monografias?busca=sistemas+distribuidos"""
        alvo = self.nova(titulo='Sistemas distribuidos com Kafka')
        resposta = self.como(self.aluno).get('/api/monografias/?busca=sistemas+distribuidos')
        ids = [r['id'] for r in resposta.data['results']]
        self.assertIn(alvo.pk, ids)
        self.assertNotIn(self.trabalho.pk, ids)

    def test_02_filtros_privados_por_curso_e_orientador(self):
        outro_curso = type(self.curso).objects.create(nome='Outro', codigo='OU')
        alvo = self.nova()
        Monografia.objects.filter(pk=alvo.pk).update(curso=outro_curso)
        resposta = self.como(self.aluno).get(f'/api/monografias/?curso={outro_curso.pk}')
        self.assertEqual([r['id'] for r in resposta.data['results']], [alvo.pk])

    def test_03_rascunho_editavel_submetida_nao(self):
        rascunho = self.nova()
        api = self.como(self.aluno)
        self.assertEqual(api.patch(f'/api/monografias/{rascunho.pk}/', {'titulo': 'Editado'}, format='multipart').status_code, 200)
        self.assertEqual(api.patch(f'/api/monografias/{self.trabalho.pk}/', {'titulo': 'X'}, format='multipart').status_code, 403)

    def test_04_crud_professores_e_alunos_pela_admin(self):
        admin = get_user_model().objects.create_superuser('adm3', 'a3@example.test', 'senha-forte-123')
        api = self.como(admin)
        r = api.post('/api/professores/', {'usuario': self.outro.pk, 'departamento': 'DC', 'area_pesquisa': 'SD'},
                     format='json', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(r.status_code, 201, r.data)
        r = api.post('/api/alunos/', {'usuario': self.aluno.pk, 'matricula': '2026001', 'curso': self.curso.pk,
                                      'orientador_atual': self.professor.pk}, format='json', REMOTE_ADDR='127.0.0.1')
        self.assertEqual(r.status_code, 201, r.data)


class R07DashboardAuditoria(BaseRequisitos):
    def test_01_relatorio_contem_todos_os_indicadores(self):
        self.publicar(self.trabalho)
        dados = self.como(self.coordenador).get('/api/relatorios/').data
        for chave in ['por_curso', 'por_orientador', 'por_ano_defesa', 'taxa_aprovacao', 'tempo_medio_dias']:
            self.assertIn(chave, dados)
        self.assertEqual(dados['taxa_aprovacao'], 1.0)
        self.assertIsNotNone(dados['tempo_medio_dias'])

    def test_02_auditoria_registra_quem_o_que_quando(self):
        self.como(self.professor).post(f'/api/monografias/{self.trabalho.pk}/aprovar/')
        registro = Auditoria.objects.filter(acao='aprovacao_orientador').latest('pk')
        self.assertEqual(registro.ator, self.professor)
        self.assertEqual(registro.registro_id, self.trabalho.pk)
        self.assertIsNotNone(registro.criado_em)

    def test_03_auditoria_registra_campos_alterados_na_edicao(self):
        """Histórico: 'qual alteração foi realizada' — valores antes/depois na edição de rascunho."""
        rascunho = self.nova(titulo='Antes')
        self.api.force_login(self.aluno)  # sessão real, como no portal
        self.api.patch(f'/api/monografias/{rascunho.pk}/', {'titulo': 'Depois'}, format='multipart')
        registro = Auditoria.objects.filter(acao='alteracao_campos', entidade='monografias.Monografia',
                                            registro_id=rascunho.pk).latest('pk')
        self.assertEqual(registro.detalhes['titulo'], {'antes': 'Antes', 'depois': 'Depois'})
        self.assertEqual(registro.ator, self.aluno)
