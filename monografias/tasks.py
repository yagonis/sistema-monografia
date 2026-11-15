from celery import shared_task, Task
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from pypdf import PdfReader
from .models import Evento, Monografia, Banca, MembroBanca
from .servicos import conferir_integridade, fechar_resultado


class EventoTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        from django.core.cache import cache
        if args:
            Evento.objects.filter(pk=args[0]).update(erro=type(exc).__name__)
            cache.delete(f'evento_em_andamento:{args[0]}')


@shared_task(base=EventoTask, autoretry_for=(Exception,), retry_backoff=True, max_retries=5)
def processar_evento(pk):
    with transaction.atomic():
        ev = Evento.objects.select_for_update().get(pk=pk)
        if ev.processado_em:
            return
        try:
            if ev.tipo in ['monografia_submetida', 'monografia_publicada']:
                trabalho = Monografia.objects.get(pk=ev.dados['monografia_id'])
                conferir_integridade(trabalho)
                corrigida = trabalho.documentos.filter(tipo='corrigida', validado_em__isnull=False).order_by('-validado_em').first() if trabalho.status == 'publicada' else None
                with (corrigida.arquivo if corrigida else trabalho.arquivo).open('rb') as arquivo:
                    texto = '\n'.join(page.extract_text() or '' for page in PdfReader(arquivo).pages)
                trabalho.texto_extraido = texto
                trabalho.save(update_fields=['texto_extraido'])
                if ev.tipo == 'monografia_publicada':
                    indexar_publicacao(trabalho)
                destino = trabalho.orientador.email if ev.tipo == 'monografia_submetida' else trabalho.autor.email
                notificar([destino], 'Atualização de monografia', trabalho.titulo)
            elif ev.tipo in ['banca_agendada', 'banca_alterada']:
                banca = Banca.objects.get(pk=ev.dados['banca_id'])
                emails = [m.usuario.email if m.usuario_id else m.email for m in banca.membros.all()]
                assunto = 'Banca agendada' if ev.tipo == 'banca_agendada' else 'Banca alterada: confirme novamente a disponibilidade'
                notificar(emails + [banca.monografia.autor.email], assunto, f'{banca.monografia.titulo} — {banca.data_hora}')
            elif ev.tipo == 'membro_convidado':
                membro = MembroBanca.objects.get(pk=ev.dados['membro_id'])
                notificar([membro.usuario.email if membro.usuario_id else membro.email], 'Convite para banca',
                          f'Você foi convidado para a banca {membro.banca_id}. Acesse o sistema ou solicite seu token temporário ao responsável.')
            elif ev.tipo == 'avaliacao_registrada':
                fechar_resultado(ev.dados['banca_id'])
            ev.processado_em = timezone.now()
            ev.erro = ''
            ev.save(update_fields=['processado_em', 'erro'])
            from django.core.cache import cache
            cache.delete(f'evento_em_andamento:{ev.pk}')
            if ev.tipo == 'monografia_submetida':
                from django.core.cache import cache
                cache.delete(f'upload_em_andamento:{ev.dados["monografia_id"]}')
        except Exception as exc:
            # O erro será registrado pelo despachante/monitor; nunca marcar evento falho como entregue.
            raise exc


def notificar(emails, assunto, mensagem):
    for email in set(filter(None, emails)):
        send_mail(assunto, mensagem, None, [email], fail_silently=False)


def indexar_publicacao(trabalho):
    from django.conf import settings
    if not settings.REPOSITORIO_URL:
        return
    import json
    from urllib.request import Request, urlopen
    banca = trabalho.bancas.filter(status='realizada').order_by('-data_hora').first()
    dados_publicos = {'id': trabalho.pk, 'titulo': trabalho.titulo, 'resumo': trabalho.resumo,
        'autor': trabalho.autor.get_full_name() or trabalho.autor.username,
        'orientador': trabalho.orientador.get_full_name() or trabalho.orientador.username,
        'curso': trabalho.curso_id, 'palavras_chave': trabalho.palavras_chave,
        'ano_defesa': banca.data_hora.year if banca else None}
    payload = {'origem_id': trabalho.pk, 'titulo': trabalho.titulo, 'autor': dados_publicos['autor'],
        'orientador': dados_publicos['orientador'], 'curso_id': trabalho.curso_id,
        'ano_defesa': dados_publicos['ano_defesa'], 'palavras_chave': trabalho.palavras_chave,
        'texto': trabalho.texto_extraido, 'dados': dados_publicos}
    req = Request(settings.REPOSITORIO_URL.rstrip('/') + '/internal/indexar/',
        data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json',
        'X-Integration-Key': settings.REPOSITORIO_INTEGRATION_KEY}, method='POST')
    with urlopen(req, timeout=10) as response:
        response.read()


@shared_task
def despachar_eventos():
    from django.core.cache import cache
    from django.db.models import F
    for pk in Evento.objects.filter(processado_em__isnull=True, tentativas__lt=5).order_by('pk').values_list('pk', flat=True)[:100]:
        if cache.add(f'evento_em_andamento:{pk}', True, 600):
            Evento.objects.filter(pk=pk).update(tentativas=F('tentativas') + 1)
            try:
                processar_evento.delay(pk)
            except Exception as exc:
                cache.delete(f'evento_em_andamento:{pk}')
                Evento.objects.filter(pk=pk).update(erro=type(exc).__name__)
