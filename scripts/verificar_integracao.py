"""Executar somente no Compose de verificação, nunca sobre dados reais."""
import os
if os.environ.get('VERIFICACAO_ISOLADA') != '1':
    raise RuntimeError('Esta verificação exige VERIFICACAO_ISOLADA=1 em banco descartável.')
import io
import json
import time
import uuid
from datetime import timedelta
from urllib.request import urlopen
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from pypdf import PdfWriter
from monografias.models import Curso, Monografia, Banca, Documento, Evento
from monografias import servicos as s

ident = uuid.uuid4().hex[:10]
Usuario = get_user_model()
aluno = Usuario.objects.create_user('aluno-'+ident, email='aluno@example.test', first_name='Aluno')
professor = Usuario.objects.create_user('professor-'+ident, email='professor@example.test', first_name='Professor')
aluno.groups.add(Group.objects.get(name='Alunos'))
professor.groups.add(Group.objects.get(name='Professores'))
curso = Curso.objects.create(nome='Curso de teste', codigo=ident)
buffer = io.BytesIO(); pdf = PdfWriter(); pdf.add_blank_page(width=100, height=100); pdf.write(buffer)
conteudo = buffer.getvalue()
trabalho = Monografia.objects.create(titulo='Verificacao '+ident, autor=aluno, orientador=professor, curso=curso,
    arquivo=SimpleUploadedFile('teste.pdf', conteudo), hash_sha256=__import__('hashlib').sha256(conteudo).hexdigest())


def esperar(condicao, descricao):
    limite = time.monotonic()+50
    while time.monotonic() < limite:
        if condicao():
            print('OK:', descricao, flush=True)
            return
        time.sleep(1)
    raise AssertionError('Tempo excedido: '+descricao)

s.submeter(aluno, trabalho.pk)
esperar(lambda: Evento.objects.filter(tipo='monografia_submetida', dados__monografia_id=trabalho.pk, processado_em__isnull=False).exists(), 'RabbitMQ/worker extrai PDF e processa submissão')
s.aprovar(professor, trabalho.pk)
banca = s.salvar_banca(professor, trabalho, {'data_hora': timezone.now()+timedelta(days=1), 'fim': timezone.now()+timedelta(days=1,hours=1), 'local': 'Sala de teste'})
interno, _ = s.convidar(professor, banca, {'usuario': professor})
externo, token = s.convidar(professor, banca, {'nome': 'Externo', 'email': 'externo@example.test'})
s.confirmar(interno, professor); s.confirmar(s.membro_por_token(token)); s.agendar(professor, banca.pk)
# Avanço de tempo restrito à fixture: simula o fim de uma defesa.
Banca.objects.filter(pk=banca.pk).update(data_hora=timezone.now()-timedelta(hours=2), fim=timezone.now()-timedelta(hours=1))
s.avaliar(interno, {'nota': 8, 'parecer': 'Aprovado', 'recomendacao': 'aprovado'}, professor)
s.avaliar(s.membro_por_token(token), {'nota': 6, 'parecer': 'Corrigir', 'recomendacao': 'ressalvas'})
esperar(lambda: Banca.objects.filter(pk=banca.pk, nota_final=7, status='realizada').exists(), 'média calculada somente após todas as avaliações')
for tipo in ['termo', 'corrigida']:
    doc = Documento.objects.create(monografia=trabalho, tipo=tipo, arquivo=SimpleUploadedFile(tipo+'.pdf', conteudo), hash_sha256=s.sha256(SimpleUploadedFile(tipo+'.pdf', conteudo)))
    s.validar_documento(professor, doc.pk)
esperar(lambda: Evento.objects.filter(tipo='monografia_publicada', dados__monografia_id=trabalho.pk, processado_em__isnull=False).exists(), 'publicação enviada ao serviço independente')
with urlopen('http://repositorio:8001/api/publicadas/?busca='+ident, timeout=10) as resposta:
    dados = json.load(resposta)
assert dados['count'] == 1, dados
print('OK: busca pública encontra somente a publicação indexada; integração completa.', flush=True)
