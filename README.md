# Repositório de Monografias — documentação geral
## Integrantes - Maria Vieira, Miguel Moreira, Ian Patrick e Yago Brito

Atualização: **22/11/2026**. Este é o documento único de escopo, acompanhamento, arquitetura, execução e integração do projeto.

O checklist foi organizado a partir do enunciado **Trabalho de Sistemas Distribuídos**, do professor Alessandro Vivas Andrade, conferido com o código atual. Os identificadores RF, RD e RNF são uma organização do projeto, não uma numeração original do PDF.

**Como interpretar:** `[x]` significa implementado no código; `[ ] Parcial` significa que há implementação com uma parte ainda a concluir ou validar; `[ ] Pendente` significa trabalho ainda não concluído. Implementação e testes locais não comprovam implantação institucional ou capacidade em produção.

Navegação: [Escopo](#1-objetivo-e-escopo-do-pdf) · [Checklist](#2-checklist-funcional-do-pdf-e-situação-atual) · [Pendências](#3-o-que-falta-ou-precisa-ser-confirmado) · [Execução local](#7-executar-localmente) · [Docker](#8-executar-com-docker-compose) · [API](#9-api-httpjson) · [Testes](#11-testes-evidências-e-limites) · [Mudanças](#12-histórico-de-mudanças).

## 1. Objetivo e escopo do PDF

Desenvolver um sistema distribuído para cadastro, submissão, avaliação e publicação de monografias/TCCs. O aluno envia seu trabalho, o orientador aprova a submissão, o coordenador ou orientador organiza a banca, os membros avaliam a defesa e o público consulta somente os trabalhos autorizados para publicação.

O escopo exige:

- Autenticação e autorização de administradores, coordenadores, professores/orientadores, alunos e membros externos temporários.
- Cadastros e operações CRUD com permissões, edição por etapa e proteção de trabalhos publicados.
- Upload e integridade de PDF, aprovação prévia do orientador e processamento assíncrono.
- Agendamento de banca, confirmação dos membros, bloqueio de conflitos, avaliações e resultado final.
- Documentos complementares, correções e publicação automática condicionada.
- APIs REST/JSON, frontend JavaScript e repositório público com busca.
- Redis, fila de eventos, serviços independentes, auditoria, dashboards e escalabilidade.
- Ambiente Linux e equipe de até cinco alunos. A composição da equipe é um requisito da entrega acadêmica, não uma funcionalidade verificável pelo código.

### Tecnologias

| Exigência/decisão | Implementação atual |
| --- | --- |
| Python e Django | Python 3.12 usado na validação; dependência Django `>=6.1.3,<6.2` |
| Django na última versão, conforme o enunciado | Conferir a versão exigida na entrega; o documento não afirma que a faixa fixada será sempre a mais recente |
| PostgreSQL | Bancos separados para o serviço acadêmico e o repositório público |
| Django REST Framework | CRUDs, ações de negócio, autenticação de sessão e respostas JSON |
| django-allauth | Login por usuário/senha e integração com as contas Django |
| Redis | Cache de sessões, buscas, limites e controles temporários de processamento |
| RabbitMQ ou Kafka | Escolhido RabbitMQ, com Celery worker e beat |
| Leitura/extração de PDF | `pypdf`, SHA-256 e validação de arquivos |
| Frontend JavaScript | HTML/CSS e módulos JavaScript locais consumindo a API |
| Execução e estáticos | Docker Compose, Gunicorn e WhiteNoise; também há execução local sem Docker |
| Contrato da API | OpenAPI gerado pelo código, disponível em `/api/schema/` e `/api/docs/` |

## 2. Checklist funcional do PDF e situação atual

### 2.1. Autenticação e autorização

- [x] **RF01** Login e senha com django-allauth.
- [x] **RF02** Diferenciação entre administração, coordenadores, professores e alunos, com verificações de perfil e vínculo com o registro/curso.
- [x] **RF03** Membro externo acessa por token temporário, sem conta permanente; há expiração, renovação e revogação.
- [x] **RF04** Senhas armazenadas por hash e políticas de senha configuradas no Django. O hash simplificado nas configurações de teste não é usado como configuração de produção.
- [x] **RF05** Página principal e painel com navegação e dados conforme o perfil.
- [x] **RF06** Operações restritas exigem sessão/permissão ou o token externo correspondente; CSRF protege as escritas com sessão.
- [ ] **RF07 — Parcial:** restrição de rede implementada no admin e nos endpoints administrativos; falta configurar e validar os CIDRs/IPs/VPN da instituição real.

### 2.2. Cadastros, consultas e CRUD

- [x] **RF08** CRUD de usuários, perfis de aluno/professor, cursos, monografias, bancas e avaliações, respeitando as restrições de cada etapa.
- [x] **RF09** Busca e filtros por autor, orientador, curso, ano de defesa e palavras-chave no servidor, tanto na consulta pública quanto em `/api/monografias/` (ex.: `?busca=sistemas+distribuidos`). A busca livre exige todos os termos e considera título, resumo, palavras-chave, texto extraído e nomes de autor/orientador. O portal ainda filtra localmente as listas privadas já carregadas.
- [x] **RF10** Edição de rascunhos e de bancas ainda não realizadas e sem avaliações; editar banca exige novas confirmações. O admin também bloqueia alterações de monografias submetidas/aprovadas.
- [x] **RF11** Avaliação editável somente pelo respectivo avaliador e antes do fechamento do resultado.
- [x] **RF12** Exclusões exigem autorização e respeitam vínculos; monografias publicadas não podem ser excluídas. A implementação restringe a exclusão de monografias aos rascunhos.

### 2.3. Submissão e integridade

- [x] **RF13** Aluno cria seu rascunho e associa orientador; a orientação pode ser definida depois, mas é obrigatória para submeter.
- [x] **RF14** Upload de PDF e acompanhamento dos estados da monografia.
- [x] **RF15** Validação de extensão, assinatura, leitura do PDF, páginas, ausência de criptografia e limite de **50 MiB**.
- [x] **RF16** Cálculo e armazenamento de SHA-256; deduplicação de envio por autor/hash nas páginas do aluno e na API.
- [x] **RF17** Aprovação do orientador registrada com responsável/data e exigida antes da preparação/agendamento de banca.
- [x] **RF18** Texto extraído por worker a partir de evento de submissão; a extração não acontece durante a requisição de upload.
- [x] **RF19** Verificação de integridade antes de aprovação, agendamento/publicação e nos downloads aplicáveis; arquivos/documentos validados têm hash conferido. Não há monitor periódico de todos os arquivos em repouso.

### 2.4. Bancas e avaliações

- [x] **RF20** Orientador vinculado ou coordenador do curso prepara e agenda banca de monografia aprovada pelo orientador.
- [x] **RF21** Registro de início/fim, local presencial ou link e membros internos/externos.
- [x] **RF22** Agendamento exige confirmação de todos os membros; mudanças na proposta invalidam as confirmações anteriores.
- [x] **RF23** Bloqueio de horários sobrepostos da mesma pessoa; identificação também considera e-mail para evitar duplicação entre convites internos e externos.
- [ ] **RF24 — Parcial:** eventos e tarefas notificam membros e aluno após agendamento. O ambiente padrão usa e-mail no console; falta configurar SMTP e comprovar recebimento em caixas reais.
- [x] **RF25** Cada membro registra nota, parecer e recomendação após o horário final da defesa.
- [x] **RF26** O worker fecha o resultado somente após todas as avaliações e atualiza o estado do trabalho; a nota final é a média aritmética das notas.

### 2.5. Documentos e publicação

- [x] **RF27** Upload de ata de defesa, termo de autorização, comprovante de revisão ortográfica e versão corrigida.
- [x] **RF28** Recebimento e validação da versão corrigida quando houver ressalvas.
- [x] **RF29** Publicação automática depende da aprovação final, termo validado e correção validada quando exigida. A assinatura do termo é conferida manualmente pelo responsável, não por validação criptográfica automática.
- [x] **RF30** Consulta e download públicos sem login exclusivamente para monografias publicadas.
- [x] **RF31** Busca pública por título/autor, orientador, curso, ano de defesa e palavras-chave nos endpoints correspondentes.

### 2.6. API e frontend

- [x] **RF32** API REST com respostas JSON usando Django REST Framework.
- [x] **RF33** Endpoints públicos de monografias publicadas, cursos e orientadores.
- [x] **RF34** CRUDs autenticados de alunos, monografias, bancas e avaliações, além dos demais cadastros e ações do fluxo.
- [x] **RF35** Portal JavaScript integrado à API para submissão, acompanhamento, orientação, bancas, avaliações, documentos e consulta pública; layout responsivo e acesso externo por código.

### 2.7. Auditoria e indicadores

- [x] **RF36** Auditoria com ator, ação/alterações de campos, registro afetado e data/hora. Ações automáticas são registradas como sistema.
- [x] **RF37** Registro de uploads, submissões, aprovações, convites, agendamentos, avaliações, documentos e publicação. Senhas, tokens e texto integral são excluídos dos detalhes da auditoria.
- [x] **RF38** Indicadores e gráficos de monografias por curso, orientador e ano de defesa, limitados ao escopo autorizado.
- [x] **RF39** Taxa de aprovação e tempo médio entre submissão e defesa; ausência de dados é apresentada sem inventar valores.

### 2.8. Redis, fila e distribuição

- [x] **RD01** Cache de sessões quando `REDIS_URL` está configurada; o backend de sessões combina cache e banco.
- [x] **RD02** Cache de resultados de busca no serviço independente do repositório, com invalidação após ingestão de publicação.
- [x] **RD03** Chave temporária de upload em processamento para impedir reenvio simultâneo da submissão.
- [x] **RD04** Limitação de taxa de submissões, incluindo limites de requisição na API.
- [x] **RD05** RabbitMQ e Celery para processamento assíncrono.
- [x] **RD06** Extração de texto e projeção/indexação pública por eventos; somente publicações são enviadas ao serviço público.
- [x] **RD07** Notificações de agendamento processadas pela fila; entrega externa depende da configuração de e-mail indicada em RF24.
- [x] Dois serviços Django com APIs, configurações, migrações e PostgreSQL independentes: acadêmico e repositório público.
- [x] A listagem pública `/api/publicadas/` do serviço acadêmico funciona como gateway de mesma origem: resultados em cache Redis (`busca:<versão>:<hash da query>`, invalidado a cada publicação/indexação) e, com `REPOSITORIO_URL` configurada, consulta encaminhada ao serviço de repositório. Se o repositório estiver indisponível, a consulta local é usada e novas tentativas ficam suspensas por 30 s. Detalhe e PDF continuam servidos pelo acadêmico.

### 2.9. Requisitos não funcionais

- [ ] **RNF01 — Parcial:** teste local de 1.000 consultas concorrentes documentado; falta validar capacidade com volume representativo de dados, consultas não cacheadas, arquivos reais e infraestrutura de implantação.
- [x] **RNF02** Separação entre operação acadêmica e consulta pública, com integração HTTP e fila. A divisão em seis serviços citada no PDF é exemplificativa; autenticação, bancas e relatórios continuam módulos do serviço acadêmico.
- [x] **RNF03** Cache e processamento assíncrono implementados; sua operação depende de Redis, broker, worker e beat ativos.
- [x] **RNF04** Hashes e verificações de integridade implementados.
- [ ] **RNF05 — Parcial:** mecanismos de segurança implementados; configuração de domínio, TLS, rede institucional, segredos e serviços externos ainda depende do ambiente real.
- [x] **RNF06** Histórico de alterações e ações da aplicação. Escritas SQL diretas ou scripts que contornem os fluxos não têm a mesma garantia.

## 3. O que falta ou precisa ser confirmado

Este checklist separa pendências reais de implantação e melhorias das funcionalidades já implementadas:

- [ ] **Usar no portal os filtros de servidor das listas privadas**, evitando carregar todos os registros no navegador em contas com muitos vínculos (a API já filtra e pagina).
- [ ] **Reindexar publicações antigas** no repositório para incluir `autor_id`, `orientador_id`, `autor_nome`, `orientador_nome` e `publicada_em`, usados pelos filtros e cartões do portal.
- [ ] **Configurar SMTP e validar e-mails reais** de convites, submissão, agendamento e publicação.
- [ ] **Configurar a rede institucional/VPN e os IPs autorizados** e testar o acesso pela infraestrutura real, inclusive o endereço recebido através de Docker/proxy.
- [ ] **Preparar implantação real:** domínio, HTTPS, hosts, segredos, permissões de volumes, backups/restauração e operação contínua de worker/beat.
- [ ] **Homologar a política acadêmica:** escala de notas, regra das recomendações, composição mínima da banca e procedimento de conferência de assinatura. A política vigente usa média aritmética; os demais critérios atuais estão descritos abaixo para revisão institucional.
- [ ] **Ampliar a homologação ponta a ponta do frontend**, incluindo upload/validação de todos os documentos e avaliação de membro externo com fila ativa, além dos fluxos já testados.
- [ ] **Executar carga representativa em implantação**, incluindo consulta fria, grandes acervos, falhas e recuperação de broker/Redis/SMTP.
- [ ] **Conferir versões e requisitos administrativos da entrega**, incluindo a exigência de Django na última versão, ambiente Linux e equipe de até cinco alunos.

Melhorias que não devem ser confundidas com exigências expressas do PDF:

- [ ] Definir política de retenção/limpeza de PDFs antigos e aperfeiçoar o histórico de versões; hoje há número de versão, hashes e auditoria, mas não um catálogo completo de versões para navegação do usuário.
- [ ] Se houver necessidade institucional, implementar verificação criptográfica de assinatura digital, monitor periódico de integridade ou reabertura controlada de submissão. Atualmente a conferência é humana e a submissão bloqueia edição.
- [ ] Expandir testes automatizados de interface e acessibilidade e definir uma rotina de integração contínua.

## 4. Regras de negócio adotadas

1. Aprovação do orientador e aprovação final da defesa são decisões distintas.
2. O autor edita somente rascunhos. Após submeter, a aplicação não oferece edição irrestrita nem troca de PDF no admin.
3. O limite adotado é 50 × 1024 × 1024 bytes. PDFs protegidos por senha, vazios ou inválidos são recusados.
4. A deduplicação é por autor/hash: não se revela a um aluno a existência de PDFs privados de outro autor.
5. Banca exige aprovação prévia, intervalo futuro com início/fim e confirmação de todos. Intervalos adjacentes são permitidos; sobrepostos são bloqueados.
6. Editar banca ainda não realizada e sem avaliações a devolve à preparação e exige novas confirmações.
7. A nota final é a média aritmética de todas as notas. Escala inicial: **0 a 10**. Não há nota mínima de aprovação definida no código como critério independente.
8. Uma recomendação de reprovação resulta em reprovação; sem reprovação, a presença de ressalvas exige correção; sem ressalvas, o resultado é aprovação.
9. Não foi fixado número acadêmico obrigatório de integrantes: o código exige ao menos um membro e a confirmação de todos.
10. O resultado é fechado pelo worker após todas as avaliações. Até esse fechamento, o próprio avaliador pode editar sua avaliação.
11. Publicar exige aprovação final e termo validado. Se houver ressalvas, exige também versão corrigida validada. A conferência do termo/assinatura é humana e registrada com responsável/data.
12. O download público prioriza a versão corrigida validada mais recente; o original permanece armazenado com seu hash.
13. Tokens externos duram inicialmente **168 horas**, configuráveis por `CONVITE_VALIDADE_HORAS`. O gestor pode renovar/revogar; o token é armazenado por hash e entregue uma vez para compartilhamento privado.
14. Datas históricas de submissão não registradas anteriormente permanecem desconhecidas; os relatórios não as estimam.

### Estados

- **Monografia:** `rascunho → em_avaliacao → aprovada_orientador → aprovada/ressalvas/reprovada → publicada`, sendo a publicação aplicável somente após cumprimento das condições.
- **Banca:** `em_preparacao → agendada → realizada`, ou cancelamento permitido antes de avaliações. Alterar uma agendada sem avaliações devolve à preparação.
- **Avaliação:** `aprovado`, `ressalvas` ou `reprovado`; gravação somente após o fim da defesa e antes do fechamento.

## 5. Atores e permissões

| Ator | Acesso implementado |
| --- | --- |
| Visitante | Consulta e download exclusivamente de publicadas; leitura de cursos e orientadores |
| Aluno | Próprios rascunhos/submissões, PDFs e documentos; acompanhamento do resultado |
| Professor/orientador | Trabalhos sob sua orientação; aprovação e gestão correspondente; participação em bancas quando convidado |
| Coordenador | Trabalhos submetidos dos cursos em que está cadastrado como responsável; gestão das bancas desse escopo |
| Membro externo | Dados, confirmação, PDF e avaliação da própria banca, conforme etapa e token válido |
| Administração | Superusuário e rede autorizada para cadastros, grupos, auditoria e operação; também respeita bloqueios de trabalhos não editáveis |

Os grupos acadêmicos são `Alunos`, `Professores` e `Coordenadores`. Criar perfil de aluno/professor não concede grupo, superusuário ou acesso ao admin automaticamente. Uma pessoa pode acumular grupos. O vínculo com curso/orientação é verificado além do grupo.

## 6. Arquitetura e dados

### Serviços e processamento

| Componente | Responsabilidade |
| --- | --- |
| Serviço acadêmico, porta 8000 | Contas, cursos, monografias, bancas, avaliações, documentos, auditoria, indicadores e portal |
| Repositório, porta 8001 | Banco próprio de projeções públicas, filtros, busca full-text em PostgreSQL e cache |
| PostgreSQL acadêmico / PostgreSQL do repositório | Persistências separadas; o repositório não consulta o banco acadêmico |
| RabbitMQ | Transporte das tarefas |
| Celery worker e beat | Processamento dos eventos e despacho periódico |
| Redis | Cache de sessões/buscas e controles de taxa/processamento |
| WhiteNoise/Gunicorn | Entrega de estáticos e execução WSGI |

A transação de negócio grava um `Evento` na outbox. O beat despacha pendentes a cada dez segundos. O worker processa extração, avisos, cálculo de resultado e indexação. O repositório recebe somente publicações, por HTTP com chave de integração, e faz atualização/inserção por identificador.

Eventos já concluídos não são processados novamente. Há tentativas, erros e liberação administrativa de nova tentativa. A busca tem consistência eventual. A entrega de e-mails é **pelo menos uma vez**: uma falha após aceitação pelo SMTP e antes do commit pode resultar em aviso duplicado.

### Modelos

| Modelo | Informações principais |
| --- | --- |
| `Usuario` | Nome, e-mail, login, senha protegida, grupos e atividade |
| `PerfilAluno` | Conta, matrícula única, curso e orientador atual |
| `PerfilProfessor` | Conta, departamento e área de pesquisa |
| `Curso` | Nome, código único e coordenador |
| `Monografia` | Título, resumo, palavras-chave, autor, orientador, curso, PDF/hash, versão, estados e datas |
| `Banca` | Trabalho, intervalo, local/link, estado, média final e fechamento |
| `MembroBanca` | Conta interna ou nome/e-mail externo, confirmação e controle do token |
| `Avaliacao` | Membro, nota, parecer, recomendação e atualização |
| `Documento` | Trabalho, tipo, PDF/hash e responsável/data da validação |
| `Auditoria` | Ator, ação, entidade, alterações e horário |
| `Evento` | Tipo, dados, tentativas, erro e processamento |
| `Publicacao` no repositório | Projeção pública e texto indexável, sem contas de login ou arquivos privados |

O curso/orientador atual do perfil não reatribui automaticamente trabalhos anteriores. As contas existentes não recebem matrícula ou curso inventados por migração.

### Estrutura do código

- `config/`: configurações locais, de produção e de teste, URLs, middleware e Celery.
- `usuarios/`: contas, perfis, grupos e administração.
- `monografias/`: modelos e regras acadêmicas, arquivos, tarefas, auditoria e templates.
- `api/`: serializers, endpoints, permissões HTTP, erros e testes.
- `services/repositorio/`: serviço público independente e suas migrações.
- `monografias/static/portal/`: módulos JavaScript, estilos e ícone do portal.
- `scripts/`: verificações JavaScript, integração isolada e carga.
- `compose.yaml`, `Dockerfile`, `.env.example`, `requirements.txt`: arquivos operacionais necessários; não são documentação separada.

## 7. Executar localmente

Com PostgreSQL disponível, na pasta do projeto:

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
read -s -p "Senha do PostgreSQL: " DB_PASSWORD
echo
export DB_PASSWORD
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

O banco esperado por padrão é `repositorio_tcc`, com usuário `repositorio_app`, em `localhost:5432`. Os comandos pressupõem que o banco e a conta já existem. Crie superusuário somente se ainda não houver um.

Abra `http://127.0.0.1:8000/` para o portal. O frontend não precisa de servidor Node, instalação npm ou compilação JavaScript. Para servir pelo Gunicorn fora do Docker, execute `python manage.py collectstatic --noinput` antes de iniciar o servidor.

Para os fluxos assíncronos, configure Redis e RabbitMQ e inicie em terminais separados, com as mesmas variáveis de ambiente:

```bash
celery -A config worker --loglevel=info --concurrency=2
celery -A config beat --loglevel=info --schedule=/tmp/monografias-beat
```

Sem worker/broker, os eventos permanecem pendentes; o portal não simula seu processamento. O `.env` não é carregado automaticamente na execução local sem Docker: exporte as variáveis no terminal ou use um gerenciador de ambiente.

### Administração inicial

1. Entre em `/admin/` com o superusuário, a partir da rede permitida.
2. Cadastre contas e atribua os grupos acadêmicos.
3. Complete os perfis de aluno/professor e vincule o coordenador ao curso.
4. As contas acadêmicas entram pelo portal ou pelo login tradicional `/contas/login/`.

Para listar administradores ou redefinir uma senha de login:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; print(list(get_user_model().objects.filter(is_superuser=True).values('username', 'email')))"
python manage.py changepassword nome_do_usuario
```

A senha de login não pode ser consultada em texto puro. `DB_PASSWORD` é a senha do PostgreSQL, distinta da senha do usuário do portal.

## 8. Executar com Docker Compose

```bash
cp .env.example .env
```

Substitua todos os valores de exemplo por segredos reais e distintos. Para gerar um valor: `python -c "import secrets; print(secrets.token_hex(32))"`.

```bash
docker compose up -d --build db busca-db redis rabbitmq
docker compose run --rm backend python manage.py migrate
docker compose run --rm repositorio python manage.py migrate --settings=services.repositorio.settings
docker compose run --rm backend python manage.py createsuperuser
docker compose up -d --build backend repositorio worker beat
```

O portal/API ficam em `http://127.0.0.1:8000/`; o repositório independente, em `http://127.0.0.1:8001/api/publicadas/`. O build executa `collectstatic`. Volumes preservam bancos e uploads. `docker compose down` encerra os processos sem apagar volumes; `down -v` também apaga os volumes e não deve ser usado para preservar dados.

O Compose atual é local e usa e-mail no console. No Docker, o endereço visto pela aplicação pode ser o da bridge; a configuração de rede administrativa precisa considerar a origem real, sem abrir acesso indiscriminadamente.

### Variáveis e implantação

| Variável | Uso |
| --- | --- |
| `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | Conexão acadêmica; senha obrigatória nas configurações normais |
| `REDIS_URL` | Redis acadêmico e habilitação do cache de sessões |
| `CELERY_BROKER_URL` | Endereço do RabbitMQ na execução sem Compose |
| `BROKER_PASSWORD`, `BUSCA_PASSWORD` | Senhas dos serviços no Compose |
| `DJANGO_SECRET_KEY` | Segredo do Django; usar valor real em implantação |
| `ADMIN_NETWORKS` | CIDRs/IPs autorizados; não confia em `X-Forwarded-For` do cliente |
| `REPOSITORIO_URL`, `REPOSITORIO_INTEGRATION_KEY` | Destino da projeção pública e chave compartilhada entre serviços |
| `REPOSITORIO_PASSWORD`, `REPOSITORIO_DB_HOST`, `REPOSITORIO_DB`, `REPOSITORIO_USER` | Banco próprio do serviço público |
| `REPOSITORIO_REDIS_URL`, `REPOSITORIO_SECRET_KEY`, `REPOSITORIO_HOSTS` | Cache, segredo e hosts do repositório |
| `CONVITE_VALIDADE_HORAS` | Validade inicial/renovada do token externo |
| `DJANGO_ALLOWED_HOSTS` | Hosts obrigatórios na configuração de produção |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `DEFAULT_FROM_EMAIL` | E-mail na configuração de produção |

`config/settings_production.py` exige configurações reais e ativa HTTPS e cookies seguros. O Compose não seleciona esse módulo automaticamente: a implantação deve definir `DJANGO_SETTINGS_MODULE=config.settings_production` e fornecer as variáveis correspondentes.

HSTS para todos os subdomínios/preload depende do domínio real. O resultado histórico de `check --deploy` com a configuração de produção teve esses dois avisos, sem erros. A chave de integração deve trafegar por TLS quando sair de rede confiável.

## 9. API HTTP/JSON

Base acadêmica: `/api/`. JSON nas respostas comuns; PDF nos downloads. Listas CRUD usam `count`, `next`, `previous` e `results`, com 25 itens por página. Atualizações parciais usam PATCH; PUT não é exposto.

O contrato OpenAPI é gerado do código em `/api/schema/`; `/api/docs/` apresenta a consulta navegável. Não há cópia estática separada do contrato neste repositório.

### Sessão, CSRF e token externo

1. `GET /api/conta/` devolve `csrfToken`, situação de autenticação e, quando houver sessão, usuário/nome/grupos/`is_admin`.
2. `POST /api/conta/` recebe `{"login":"usuario","password":"senha"}`, cookies e cabeçalho `X-CSRFToken`.
3. Use o token CSRF atualizado após login nas escritas seguintes. No navegador, envie cookies da mesma origem.
4. `DELETE /api/conta/` encerra a sessão e também exige CSRF.
5. Membro externo usa `X-Banca-Token` a cada requisição própria, sem sessão permanente. O código fica somente na memória da aba; não é colocado em URL ou armazenamento persistente.

Frontend e API são servidos na mesma origem. Não há JWT nem CORS liberado indiscriminadamente.

### Endpoints acadêmicos

| Recurso/ação | Métodos | Regra principal |
| --- | --- | --- |
| `cursos/`, `cursos/{id}/` | GET, POST, PATCH, DELETE | Leitura pública; escrita administrativa |
| `orientadores/` | GET | Lista pública reduzida, sem senha/e-mail |
| `publicadas/`, `publicadas/{id}/`, `publicadas/{id}/pdf/` | GET | Apenas publicadas |
| `monografias/`, `monografias/{id}/` | GET, POST, PATCH, DELETE | Vínculo e etapa do trabalho |
| `monografias/{id}/submeter/`, `monografias/{id}/aprovar/` | POST | Autor submete; orientador vinculado aprova |
| `monografias/{id}/pdf/` | GET | Download privado autorizado |
| `bancas/`, `bancas/{id}/` | GET, POST, PATCH, DELETE | Gestão autorizada e etapa permitida |
| `bancas/{id}/agendar/`, `bancas/{id}/cancelar/` | POST | Aprovação, confirmação e integridade/conflitos |
| `membros/`, `membros/{id}/` | GET, POST, DELETE | Composição da banca; alteração por remoção/novo convite em preparação |
| `membros/{id}/confirmar/` | POST | Confirmação do próprio membro interno |
| `membros/{id}/renovar/`, `membros/{id}/revogar/` | POST | Gestão do acesso externo |
| `avaliacoes/`, `avaliacoes/{id}/` | GET, POST, PATCH, DELETE | Próprio avaliador, antes do fechamento |
| `documentos/`, `documentos/{id}/` | GET, POST, DELETE | Documento privado; validado não é substituído/excluído livremente |
| `documentos/{id}/validar/`, `documentos/{id}/pdf/` | POST / GET | Conferência pelo gestor / download autorizado |
| `usuarios/`, `alunos/`, `professores/` e detalhes | GET, POST, PATCH, DELETE | Administração e rede autorizada |
| `grupos/` | GET | Grupos para a administração |
| `relatorios/` | GET | Indicadores do escopo visível |
| `auditoria/`, `eventos/` | GET | Administração, somente consulta |
| `eventos/{id}/repetir/` | POST | Liberar reprocessamento de pendente |
| `health/` | GET | Verificação básica de banco/cache |
| `externo/` | GET, POST | Dados/confirmação/avaliação do próprio convite |
| `externo/pdf/` | GET | PDF conforme token e etapa |

Para criar monografia, envie multipart com `titulo`, `resumo`, `palavras_chave`, `curso`, `orientador` opcional e `arquivo`. Ao usar `FormData`, não defina manualmente o Content-Type. Autor, estado, hash e datas são definidos pelo servidor.

Exemplos JSON:

```json
{"monografia":12,"data_hora":"2026-12-10T14:00:00-03:00","fim":"2026-12-10T15:00:00-03:00","local":"Sala 2","link":""}
```

```json
{"banca":3,"nome":"Convidado externo","email":"pessoa@example.org"}
```

```json
{"membro":5,"nota":"8.50","parecer":"Texto do parecer","recomendacao":"aprovado"}
```

O convite interno usa `{"banca":3,"usuario":7}`. O convite externo retorna `membro` e `token_temporario`; compartilhe o código privadamente. Em `/api/externo/`, `{"acao":"confirmar"}` confirma disponibilidade; nota/parecer/recomendação registram ou editam a avaliação do membro derivado do token. A consulta retorna somente a própria avaliação, nunca a de outro membro.

Documentos usam multipart com `monografia`, `tipo` e `arquivo`; tipos: `ata`, `termo`, `ortografia` e `corrigida`.

### Busca e respostas

- Acadêmico: `/api/publicadas/?busca=redes&curso=1&ano_defesa=2026`. `autor` e `orientador` são IDs; também há `palavras_chave` e `page`.
- Privada: `/api/monografias/` aceita os mesmos filtros, restritos aos trabalhos visíveis para a conta.
- Repositório: `http://127.0.0.1:8001/api/publicadas/`, com busca full-text, curso/ano, autor/orientador textuais e `autor_id`/`orientador_id`. Paginação: `count`, `page`, `page_size`, `results`.
- Limites: leitura pública (acervo, cursos, orientadores) 10.000 requisições/hora por IP; demais acessos anônimos, incluindo login, 100/hora; submissões 10/hora por usuário. O IP é o `REMOTE_ADDR` (`NUM_PROXIES = 0`): `X-Forwarded-For` enviado pelo cliente é ignorado. Atrás de proxy reverso, ajuste `NUM_PROXIES` e `ADMIN_NETWORKS` juntos.
- Busca livre: até 8 termos (400 acima disso). Username nunca é pesquisável nem publicado; sem nome cadastrado, o repositório recebe "Não informado".
- Integração interna: `POST /internal/indexar/` no repositório, com `X-Integration-Key`. Não é endpoint para visitantes; recebe somente projeções de publicações.
- Relatórios retornam contagens por curso/orientador/ano, taxa entre resultados fechados e tempo médio em dias. Sem dados suficientes, taxas/duração podem ser `null`.
- Códigos: 200 consulta/ação, 201 criação, 204 exclusão, 400 validação, 403 sessão/permissão/CSRF, 404 inexistente/fora do escopo, 405 método, 409 vínculo/conflito e 429 limite de taxa. O frontend trata campos e status, sem depender de frases exatas.

## 10. Portal e navegação

| Rota na página inicial | Função |
| --- | --- |
| `/#/acervo`, `/#/acervo/{id}` | Busca pública, resumo e PDF |
| `/#/login`, `/#/painel` | Login e visão geral do perfil |
| `/#/trabalhos` | Trabalhos vinculados à conta |
| `/#/trabalhos/novo`, `/#/trabalhos/{id}/editar` | Formulário e upload de rascunho |
| `/#/trabalhos/{id}` | Acompanhamento, submissão/aprovação, documentos e preparação de banca |
| `/#/bancas`, `/#/bancas/{id}` | Agenda, composição, confirmação, agendamento e avaliações |
| `/#/relatorios` | Indicadores e gráficos |
| `/#/externo` | Código temporário e ações do convidado |
| `/#/cadastros` | Administração de contas, perfis, cursos e vínculos |
| `/#/operacao` | Auditoria e processamento de eventos |

O portal apresenta carregamento, estados vazios, mensagens de erro e confirmações para operações importantes. Não usa dados fictícios como fallback. Os templates antigos continuam disponíveis para compatibilidade. Estilos, SVG, fontes, biblioteca de animação e módulos são locais; o frontend não depende de CDN em tempo de execução.

Arquivos principais: `portal.html` em `monografias/templates/monografias/`; `app.js` para telas/navegação, `api.js` para HTTP/CSRF/downloads, `ui.js` para apresentação e escape HTML, `motion.js` para animações e `portal.css` para layout, em `monografias/static/portal/`.

### Identidade visual e animações

- **Paleta institucional (UFVJM):** tokens em `:root` de `portal.css` — marinho `#071D41` (estrutura), azul `#2969BD`/`#1F57A3` (ações e links), azul claro `#478DEB` (anel de foco) e amarelo `#FFCC4D` (apenas indicação de posição: item ativo, foco da busca). Combinações de texto conferidas em WCAG AA. Somente as cores são usadas; nenhuma marca ou logotipo institucional.
- **Linguagem visual:** acervo como catálogo (registros numerados, título em serifa, “Assuntos”), ficha do trabalho na lateral, indicadores em faixa única, status com marcador quadrado e texto, abas sublinhadas, raio de 4–6 px e sombra apenas em modal e aviso.
- **Fontes:** Public Sans (interface) e Source Serif 4 (títulos e resumos), variáveis, em `monografias/static/portal/fonts/`, licença SIL OFL 1.1 (arquivos `OFL-*.txt` ao lado). `config/settings.py` registra `font/woff2` para o servidor de desenvolvimento.
- **Animações:** GSAP 3.12.5 versionado em `monografias/static/portal/vendor/gsap.min.js`, carregado antes do `app.js`. `motion.js` faz entrada de rota, sequência curta em registros/linhas, contadores, barras de relatório, modal e avisos, animando só `transform`/`opacity` (150–300 ms). Com `prefers-reduced-motion: reduce` nada é animado; sem o arquivo do GSAP o portal funciona sem animação.

## 11. Testes, evidências e limites

### Comandos reproduzíveis

```bash
python manage.py test --settings=config.settings_test
node scripts/test_frontend.mjs
python manage.py makemigrations --check --dry-run --settings=config.settings_test
python manage.py spectacular --file /tmp/monografias-openapi.yaml --validate --settings=config.settings_test
REPOSITORIO_TEST_SQLITE=1 python manage.py test services.repositorio.checks --settings=services.repositorio.settings
```

`config/settings_test.py` usa SQLite em memória e arquivos temporários. `config/settings_integration.py` usa o PostgreSQL configurado e cria banco de teste; use infraestrutura isolada com permissão adequada. O serviço público tem uma suíte própria porque usa outro projeto/configuração Django.

### Evidências já obtidas

- 128 testes acadêmicos/integração do portal e verificações JavaScript (`scripts/test_frontend.mjs`, incluindo rótulos de contagem).
- 4 testes do repositório público: chave de integração, ingestão idempotente, filtros (inclusive por identificador) e invalidação de cache.

### Sequência de verificação do enunciado (`api/test_requisitos.py`)

59 testes organizados pelas seções do enunciado. Cada teste afirma o comportamento pedido; uma falha indica divergência com o requisito. Executar com `python manage.py test api.test_requisitos --settings=config.settings_test -v 2`.

| Classe | Cobre |
| --- | --- |
| `R01Autenticacao` | Senha com hash e política na API administrativa, rotas restritas, painel por perfil |
| `R02Submissao` | PDF válido/SHA-256, extensão e conteúdo falsos, PDF com senha, limite de 50 MiB, duplicidade, limite de submissões (429), `upload_em_andamento`, aprovação só pelo orientador, isolamento entre alunos |
| `R03Banca` | Aprovação prévia, coordenador agenda, link remoto, fluxo completo do membro externo por token, conflito de horário, escala de nota, avaliação alheia, reprovação, revogar/renovar token, banca realizada imutável |
| `R04Eventos` | Worker: extração de texto + aviso ao orientador, aviso de agendamento, fechamento do resultado, indexação com chave de integração + aviso ao aluno |
| `R05PublicacaoBusca` | Publicação automática, ressalvas exigem corrigida, acesso público, filtros (título, autor, curso, ano, palavras-chave, nome do orientador), exclusão bloqueada, integridade do arquivo, cache `busca:*` e invalidação, encaminhamento ao repositório e retorno à consulta local, limite público |
| `R06CrudApi` | `?busca=` e filtros em `/api/monografias/`, edição só de rascunho, CRUD de alunos/professores |
| `R07DashboardAuditoria` | Indicadores do dashboard, tempo médio sem defesas anteriores à submissão, auditoria com ator, nome do responsável e campos antes/depois |
| `R08Seguranca` | Limites anônimos ignoram `X-Forwarded-For` forjado, busca não revela username, indexação não envia username, máximo de 8 termos (inclusive antes do repositório) |

### Verificação visual

Telas capturadas em navegador headless com dados de demonstração (visitante, aluno, professor, coordenação e administração; 1440 px e 390 px), sem erros de console nem respostas HTTP ≥ 400. As capturas ficam fora do repositório; os dados de demonstração são locais e não fazem parte do projeto.
- Validação anterior do backend em PostgreSQL/Redis Docker: 64 testes da versão daquele momento, sem misturar esse resultado histórico com os testes adicionados depois no frontend.
- Integração anterior real: submissão → RabbitMQ/worker → extração → avaliações 8 e 6 → média 7 → termo/correção → publicação → indexação HTTP no banco público.
- Navegador com fixtures isoladas: acervo/busca, login, edição/submissão, relatórios, banca do professor, troca de perfil, administração, convite e mensagem de token inválido; layout em 1440 px e 390 px.
- Teste local anterior de busca cacheada: 1.000 requisições, concorrência 1.000, zero falhas, duração de 0,730 s e p95 de 0,617 s. A base era pequena e a máquina era local; não certifica capacidade de produção.
- OpenAPI, coleta de estáticos e verificação de diferenças de migração executados durante a implementação.

`scripts/verificar_integracao.py` cria fixtures e exige `VERIFICACAO_ISOLADA=1`; não executar sobre dados pessoais/reais. `scripts/testar_carga_busca.py` reproduz o teste de carga em serviço controlado.

Credenciais, uploads, PDFs e bancos locais são dados operacionais e não integram a documentação consolidada. A exclusão de cópias do índice Git não remove versões já existentes no histórico. Nenhum resultado de teste declara, por si só, que o ambiente pessoal ou institucional está configurado e homologado.

## 12. Histórico de mudanças

### 22/11/2026

- **Busca:** filtros de servidor também em `/api/monografias/`; busca livre exige todos os termos (máximo 8) e inclui nomes de autor e orientador.
- **Acervo público:** cache Redis `busca:<versão>:<hash>` com invalidação a cada publicação/indexação; encaminhamento ao serviço de repositório quando `REPOSITORIO_URL` está configurada, com retorno à consulta local.
- **Repositório:** filtros `autor_id`/`orientador_id`; a indexação envia identificadores, nomes e data de publicação, nunca o username.
- **Limites e segurança:** escopo `publico` (10.000/h por IP) para leitura pública; `NUM_PROXIES = 0` (identificação por `REMOTE_ADDR`).
- **Correções:** validador de PDF fecha o arquivo armazenado que abriu; tempo médio do dashboard ignora defesas anteriores à submissão; auditoria mostra o nome do responsável; paginação da operação usa “registros”.
- **Portal:** nova identidade visual com a paleta institucional, fontes locais (OFL) e animações GSAP com respeito a `prefers-reduced-motion`; correções de layout no painel e no celular.
- **Testes:** `api/test_requisitos.py` (59 testes por seção do enunciado e de segurança) e testes de portal para GSAP/fontes locais.
