# Backend — execução, arquitetura e decisões

## Entrega e arquitetura

O backend foi ampliado para o ciclo de submissão, aprovação do orientador, preparação de banca, convites internos/externos, confirmação, conflitos de horário, defesa, avaliações, resultado, documentos, correções e publicação.

Há dois serviços Django com processos, configurações, APIs, migrações e PostgreSQL independentes:

- **Acadêmico**, porta 8000: autenticação allauth, usuários, cursos, submissões, bancas, avaliações, documentos, auditoria e relatórios.
- **Repositório**, porta 8001: recebe projeções públicas autenticadas por chave de integração, mantém somente publicações no banco próprio e oferece busca pública com paginação e cache Redis. Não lê o banco acadêmico nem os uploads privados.

O serviço acadêmico preserva coesos os fluxos transacionais. Autenticação, bancas e relatórios são módulos desse serviço, não são apresentados como microsserviços independentes. O enunciado admite divisões exemplificativas; nesta implementação a separação independente ocorre entre operação acadêmica e consulta pública.

RabbitMQ transporta tarefas Celery; worker e beat executam processamento fora das requisições. Redis armazena cache de sessões, buscas, limites de submissão e travas temporárias. A extração interna de texto de uma submissão não a disponibiliza no serviço público. Somente a publicação gera a projeção pública.

## Iniciar com Docker Compose

```bash
cp .env.example .env
```

Substitua todos os valores de exemplo. Para gerar cada segredo, use `python -c "import secrets; print(secrets.token_hex(32))"`. Use segredos distintos para senhas e chave de integração. Não versione `.env`.

```bash
docker compose up -d --build db busca-db redis rabbitmq
docker compose run --rm backend python manage.py migrate
docker compose run --rm repositorio python manage.py migrate --settings=services.repositorio.settings
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d backend repositorio worker beat
```

A API acadêmica fica em `http://127.0.0.1:8000/api/`; a busca independente em `http://127.0.0.1:8001/api/publicadas/`. A documentação navegável fica em `/api/docs/`, e o OpenAPI em `/api/schema/`.

Os volumes preservam bancos e uploads. `docker compose down` para processos sem apagar volumes. Não use `down -v` sobre dados que deseja manter.

O Compose é um ambiente local. E-mails vão ao console do worker, sem envio real. Configure SMTP em implantação. No Docker, a conexão do navegador pode chegar pela interface de bridge; adicione a origem efetivamente observada a `ADMIN_NETWORKS` somente se for uma origem institucional confiável. A criação inicial do superusuário pode ser feita pelo comando acima independentemente do acesso HTTP ao admin.

## Executar sem Docker

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
celery -A config worker --loglevel=info
celery -A config beat --loglevel=info --schedule=/tmp/monografias-beat
```

Defina `DB_PASSWORD`, `DB_HOST`/`DB_PORT` se necessário, `REDIS_URL` e `CELERY_BROKER_URL`. O projeto não carrega `.env` automaticamente no modo sem Docker; exporte as variáveis no terminal ou use um gerenciador de ambiente. Sem broker e worker, os eventos permanecem pendentes na outbox; não são processados sincronamente como substituto da fila.

Para o segundo serviço, configure `REPOSITORIO_PASSWORD`, `REPOSITORIO_DB_HOST`, `REPOSITORIO_INTEGRATION_KEY` e, opcionalmente, `REPOSITORIO_REDIS_URL`. Execute as migrações com `--settings=services.repositorio.settings` e sirva `services.repositorio.wsgi:application` na porta 8001. No acadêmico, defina `REPOSITORIO_URL` e a mesma chave de integração. A chave deve ser transportada por TLS se a integração atravessar rede não confiável.

## Regras acadêmicas adotadas

- Nota final: média aritmética simples de todas as notas, conforme orientação do usuário.
- Escala inicial: 0 a 10. Não se inventou uma nota mínima de aprovação: o resultado depende das recomendações dos avaliadores.
- Uma recomendação de reprovação resulta em reprovação. Sem reprovação, a presença de ressalvas exige correção. Sem ressalvas, aprovação.
- A política está centralizada em `monografias/servicos.py`; pode ser modificada sem alterar os endpoints.
- Não foi fixado um número acadêmico arbitrário de integrantes: exige-se ao menos um membro e confirmação de todos. O orientador não é adicionado automaticamente como avaliador.
- A defesa exige início e fim explícitos. Intervalos adjacentes são permitidos; intervalos sobrepostos para a mesma pessoa são bloqueados. Não se inventou duração fixa.
- Alterar banca ainda não realizada e sem avaliações devolve a proposta à preparação e invalida as confirmações. Todos precisam confirmar novamente.
- Após todas as avaliações, a fila fecha o resultado. Até esse fechamento, cada avaliador pode editar sua avaliação; depois, fica bloqueada.
- Publicação exige aprovação final e termo validado; em caso de ressalvas, também versão corrigida validada.
- A validação do documento é uma conferência humana registrada pelo orientador/coordenador/administrador autorizado. O sistema não afirma validar assinatura digital ICP-Brasil.
- O PDF corrigido validado mais recente é o disponibilizado publicamente; o arquivo original e seu hash permanecem preservados.
- Deduplicação de envio é por autor/hash. Isso evita reenvios do aluno sem revelar a existência de PDFs privados de outros autores.
- Convites externos duram inicialmente 168 horas, configuráveis por `CONVITE_VALIDADE_HORAS`. O gestor pode renovar o token antes de encerrar a banca. Tokens são armazenados somente como SHA-256 e entregues uma vez ao gestor para compartilhamento privado.

## Estados e segurança

Monografia: `rascunho → em_avaliacao → aprovada_orientador → aprovada/ressalvas/reprovada → publicada`.

O resultado da banca não reutiliza a aprovação do orientador. Rascunhos só podem ser editados pelo autor; o admin permite consultar trabalhos posteriores, mas não alterá-los ou excluí-los. Não há reabertura irrestrita de submissão.

Coordenador precisa do grupo e do vínculo de curso. Professor precisa do vínculo de orientação ou participação em banca conforme a ação. Um aluno não pode aprovar seu próprio trabalho por forjar campos JSON. O backend não aceita alteração direta de status, hash, data ou responsável da aprovação.

A autenticação da interface usa sessão Django/allauth e CSRF. Endpoints administrativos de contas/cadastros exigem superusuário e rede autorizada. A restrição de rede também se aplica ao `/admin/`; não se confia em `X-Forwarded-For` fornecido pelo cliente.

Downloads passam por autorização e conferência de integridade. Arquivos privados não são servidos diretamente pelo servidor web. Logs de auditoria registram campos anteriores/novos, ações, ator e horário, sem senhas, tokens ou texto integral. Scripts SQL diretos continuam fora das garantias da aplicação.

## Outbox, falhas e operação

A transação de negócio grava `Evento`. O beat busca eventos pendentes a cada dez segundos; o worker processa com retries e bloqueio do evento. Reentrega de evento já processado é ignorada.

A entrega de e-mail é **pelo menos uma vez**: uma queda após SMTP aceitar e antes do commit pode resultar em aviso repetido. Não há alegação de envio exatamente uma vez. A projeção de busca usa upsert por identificador, tornando reentregas idempotentes.

Há limite de tentativas de despacho e estado de erro. Superusuários podem consultar `/api/eventos/` e liberar uma nova tentativa com `POST /api/eventos/{id}/repetir/`. Investigue a falha antes de repetir. Eventos não são silenciosamente marcados como concluídos quando uma tarefa falha.

A consistência da busca é eventual. Uma publicação pode levar alguns segundos até aparecer no segundo serviço. As buscas no serviço público usam full-text em português no PostgreSQL, com filtros e cache; SQLite usa busca textual simplificada apenas nos testes locais.

## Implantação

`config/settings_production.py` exige chave secreta, hosts, CIDRs institucionais, Redis, SMTP e remetente pelo ambiente, ativa cookies seguros e redirecionamento HTTPS. Use proxy TLS configurado para a infraestrutura real; não ative confiança em cabeçalhos de proxy de qualquer origem.

`check --deploy` com configuração de produção não apontou erros. Permanecem dois avisos deliberados sobre HSTS em subdomínios e preload, que dependem do domínio real. Não habilitar globalmente sem conhecer todos os subdomínios.

As migrações foram testadas em bancos isolados; o PostgreSQL pessoal do usuário não foi alterado nesta entrega. Datas antigas de submissão permanecem desconhecidas quando não foram registradas historicamente; relatórios não inventam essas datas.

## Validação realizada

- Suíte acadêmica: 64 testes; executada em SQLite e, durante a validação, em PostgreSQL/Redis Docker.
- Serviço público: 3 testes com banco próprio, incluindo ingestão autenticada, upsert, filtros e invalidação de cache.
- Ciclo real: submissão → RabbitMQ → worker → extração → banca → avaliações → média 7 para notas 8 e 6 → termo/correção → publicação → ingestão HTTP → busca no banco independente.
- OpenAPI gerado e validado, sem avisos na última geração.
- Carga local: 1.000 requisições com concorrência 1.000, 1.000 respostas bem-sucedidas, zero falhas, 0,730 s no total e p95 de 0,617 s. Cenário de busca cacheada com um conjunto pequeno de fixtures, na máquina local; não certifica esses números para dados reais ou implantação externa.

Comandos de testes e verificação reproduzíveis:

```bash
python manage.py test --settings=config.settings_test
python manage.py makemigrations --check --dry-run --settings=config.settings_test
python manage.py spectacular --file /tmp/openapi.yaml --validate --settings=config.settings_test
REPOSITORIO_TEST_SQLITE=1 python manage.py test services.repositorio.checks --settings=services.repositorio.settings
```

`config/settings_integration.py` usa o PostgreSQL configurado, criando banco de teste separado. Use apenas em infraestrutura de teste com permissão para criar bancos. `scripts/verificar_integracao.py` cria fixtures e exige `VERIFICACAO_ISOLADA=1`; não executar sobre dados reais. `scripts/testar_carga_busca.py` oferece o teste local de concorrência.

Referências de implementação: [DRF](https://www.django-rest-framework.org/api-guide/viewsets/), [Celery com Django](https://docs.celeryq.dev/en/stable/django/first-steps-with-django.html), [cache Django](https://docs.djangoproject.com/en/6.1/topics/cache/).
