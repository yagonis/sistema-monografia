import json
from django.test import TestCase, override_settings
from django.core.cache import cache
from .models import Publicacao

@override_settings(INTEGRATION_KEY='test-key')
class RepositorioTests(TestCase):
    def setUp(self):
        cache.clear()
        self.payload = {'origem_id': 1, 'titulo': 'Sistemas distribuídos', 'autor': 'Aluno', 'orientador': 'Professor',
            'curso_id': 1, 'ano_defesa': 2026, 'palavras_chave': 'redes', 'texto': 'Texto da publicação',
            'dados': {'id': 1, 'titulo': 'Sistemas distribuídos'}}
    def test_ingestao_exige_segredo(self):
        self.assertEqual(self.client.post('/internal/indexar/', json.dumps(self.payload), content_type='application/json').status_code, 403)
    def test_ingestao_idempotente_busca_e_cache_invalidado(self):
        for _ in range(2):
            resposta = self.client.post('/internal/indexar/', json.dumps(self.payload), content_type='application/json', HTTP_X_INTEGRATION_KEY='test-key')
            self.assertEqual(resposta.status_code, 200, resposta.content)
        self.assertEqual(Publicacao.objects.count(), 1)
        self.assertEqual(self.client.get('/api/publicadas/?busca=redes').json()['count'], 1)
        self.assertEqual(self.client.get('/api/publicadas/?curso=2').json()['count'], 0)
        self.payload['curso_id'] = 2
        self.client.post('/internal/indexar/', json.dumps(self.payload), content_type='application/json', HTTP_X_INTEGRATION_KEY='test-key')
        self.assertEqual(self.client.get('/api/publicadas/?curso=2').json()['count'], 1)
    def test_parametros_invalidos_nao_geram_erro_interno(self):
        self.assertEqual(self.client.get('/api/publicadas/?page=abc').status_code, 400)
        self.assertEqual(self.client.get('/api/publicadas/?curso=abc').status_code, 400)
