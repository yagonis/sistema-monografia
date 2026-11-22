"""Consulta do acervo público no serviço independente de Repositório e Busca.

O serviço acadêmico continua sendo a origem única do portal (mesma origem, PDFs e detalhes);
a listagem/busca é encaminhada ao repositório quando `REPOSITORIO_URL` está configurada.
"""
import json
import logging
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

# Parâmetro do portal -> parâmetro do repositório.
PARAMETROS = {'busca': 'busca', 'curso': 'curso_id', 'ano_defesa': 'ano_defesa', 'palavras_chave': 'palavras_chave',
              'autor': 'autor_id', 'orientador': 'orientador_id', 'page': 'page'}
CHAVE_INDISPONIVEL = 'busca:repositorio_indisponivel'


def buscar(params, request):
    """Retorna a página no formato da API acadêmica, ou None para usar a consulta local."""
    if not settings.REPOSITORIO_URL or cache.get(CHAVE_INDISPONIVEL):
        return None
    consulta = {destino: params[origem] for origem, destino in PARAMETROS.items() if params.get(origem)}
    url = settings.REPOSITORIO_URL.rstrip('/') + '/api/publicadas/?' + urlencode(consulta)
    try:
        with urlopen(url, timeout=3) as resposta:
            dados = json.loads(resposta.read())
    except (URLError, OSError, ValueError) as exc:
        # Degrada para a consulta local e evita novas tentativas lentas por 30 s.
        logger.warning('Repositório indisponível (%s); usando consulta local.', exc)
        cache.set(CHAVE_INDISPONIVEL, True, 30)
        return None
    pagina, total, tamanho = dados['page'], dados['count'], dados['page_size']

    def link(numero):
        query = params.copy()
        query['page'] = numero
        return request.build_absolute_uri('?' + query.urlencode())

    return {'count': total, 'next': link(pagina + 1) if pagina * tamanho < total else None,
            'previous': link(pagina - 1) if pagina > 1 else None, 'results': dados['results']}
