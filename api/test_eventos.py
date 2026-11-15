from unittest.mock import patch
from django.test import override_settings
from monografias.tests import DadosMonografiaTests
from monografias.models import Evento, Auditoria, Banca, MembroBanca
from monografias.tasks import processar_evento
from django.utils import timezone
from datetime import timedelta


class EventosTests(DadosMonografiaTests):
    @patch('monografias.tasks.notificar')
    def test_evento_processado_uma_vez_e_remove_trava(self, notificar):
        from django.core.cache import cache
        ev = Evento.objects.create(tipo='monografia_submetida', dados={'monografia_id': self.trabalho.pk})
        cache.set(f'upload_em_andamento:{self.trabalho.pk}', True)
        processar_evento.run(ev.pk)
        processar_evento.run(ev.pk)
        ev.refresh_from_db()
        self.assertIsNotNone(ev.processado_em)
        self.assertEqual(notificar.call_count, 1)
        self.assertIsNone(cache.get(f'upload_em_andamento:{self.trabalho.pk}'))

    def test_falha_nao_marca_evento_como_processado(self):
        ev = Evento.objects.create(tipo='monografia_submetida', dados={'monografia_id': self.trabalho.pk})
        with patch('monografias.tasks.notificar', side_effect=OSError('SMTP indisponível')):
            # Chama o corpo da tarefa sem o wrapper de retry do Celery.
            with self.assertRaises(Exception):
                processar_evento.__wrapped__(ev.pk)
        ev.refresh_from_db()
        self.assertIsNone(ev.processado_em)
