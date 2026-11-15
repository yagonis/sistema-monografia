import hashlib
import json
from django.conf import settings
from django.core.cache import cache
from django.db.models import Q
from django.http import JsonResponse
from django.utils.crypto import constant_time_compare
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from .models import Publicacao


@csrf_exempt
@require_http_methods(['POST'])
def indexar(request):
    if not settings.INTEGRATION_KEY or not constant_time_compare(request.headers.get('X-Integration-Key', ''), settings.INTEGRATION_KEY):
        return JsonResponse({'detail': 'Acesso negado'}, status=403)
    try:
        dados = json.loads(request.body)
        campos = {key: dados[key] for key in ['titulo', 'autor', 'orientador', 'curso_id', 'ano_defesa', 'palavras_chave', 'texto', 'dados']}
        objeto = Publicacao(origem_id=dados['origem_id'], **campos)
        objeto.full_clean(exclude=['origem_id'], validate_unique=False)
        Publicacao.objects.update_or_create(origem_id=dados['origem_id'], defaults=campos)
    except (KeyError, ValueError, TypeError) as exc:
        return JsonResponse({'detail': 'Payload inválido'}, status=400)
    except Exception as exc:
        from django.core.exceptions import ValidationError
        if isinstance(exc, ValidationError):
            return JsonResponse({'detail': exc.messages}, status=400)
        raise
    import secrets
    cache.set('repo:versao', secrets.token_hex(16), None)
    return JsonResponse({'detail': 'Indexado'})


@require_http_methods(['GET'])
def pesquisar(request):
    versao = cache.get_or_set('repo:versao', 'inicial', None)
    chave = 'repo:busca:' + str(versao) + ':' + hashlib.sha256(request.GET.urlencode().encode()).hexdigest()
    dados = cache.get(chave)
    if dados is not None:
        return JsonResponse(dados)
    qs = Publicacao.objects.order_by('-atualizado_em', 'origem_id')
    busca = request.GET.get('busca', '')[:200]
    if busca:
        from django.db import connection
        if connection.vendor == 'postgresql':
            from django.contrib.postgres.search import SearchQuery, SearchVector
            qs = qs.annotate(documento=SearchVector('titulo', 'autor', 'orientador', 'palavras_chave', 'texto', config='portuguese')).filter(documento=SearchQuery(busca, config='portuguese'))
        else:
            qs = qs.filter(Q(titulo__icontains=busca) | Q(autor__icontains=busca) | Q(orientador__icontains=busca)
                | Q(palavras_chave__icontains=busca) | Q(texto__icontains=busca))
    for campo in ['curso_id', 'ano_defesa']:
        valor = request.GET.get(campo) or (request.GET.get('curso') if campo == 'curso_id' else None)
        if valor:
            try:
                qs = qs.filter(**{campo: int(valor)})
            except ValueError:
                return JsonResponse({'detail': 'Filtro numérico inválido'}, status=400)
    for campo in ['autor', 'orientador', 'palavras_chave']:
        if request.GET.get(campo):
            qs = qs.filter(**{campo + '__icontains': request.GET[campo][:200]})
    try:
        page = int(request.GET.get('page', '1'))
        if page < 1:
            raise ValueError
    except ValueError:
        return JsonResponse({'detail': 'Página inválida'}, status=400)
    dados = {'count': qs.count(), 'page': page, 'page_size': 25, 'results': [obj.dados for obj in qs[(page-1)*25:page*25]]}
    cache.set(chave, dados, 60)
    return JsonResponse(dados)


@require_http_methods(['GET'])
def health(request):
    Publicacao.objects.exists()
    return JsonResponse({'status': 'ok', 'servico': 'repositorio'})
