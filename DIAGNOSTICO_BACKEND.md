# Diagnóstico do backend e roteiro de implementação

Data: 11/11/2026.

Este arquivo preserva o diagnóstico anterior à implementação. Para o estado após a entrega do backend, consulte `docs/BACKEND.md` e `docs/API.md`.

## Base da revisão

Comparação do PDF `Trabalho_SistemasDistribuidos_Monografias (1).pdf` com os arquivos-fonte, dependências, configurações, migrações, templates, testes e histórico Git. Os IDs RF/RD abaixo vêm da organização feita em `requisitos.md`; o PDF é a especificação original. Os modelos do PDF são sugestões de estrutura: os dados necessários precisam ser atendidos, mas não exigem tabelas exatamente iguais às sugeridas.

Referências remotas atualizadas com `git fetch origin`:

- `authentication`, commit `f3a0cc8`: ponto de partida do código local revisado.
- `origin/main`, commit `a05e2f7`: já contém a autenticação integrada. Sua árvore de arquivos é igual à de `authentication` nesta revisão.
- `origin/feat/preparacao-de-banca`, commit `e6d4543`: contém sete arquivos com implementação inicial de banca, ainda fora da main.
- `origin/autentication_branch` e `origin/crud_branch`: trabalhos anteriores já presentes no histórico da main.
- `codex/diagnostico-backend`: branch criada a partir de `origin/main` para este diagnóstico. Nenhuma funcionalidade alterada nesta etapa.

Não foram consultados dados privados dos uploads nem registros do PostgreSQL. Presença de configuração não comprova banco operacional, migrações aplicadas ou funcionamento em produção.

## Resultado geral

O projeto possui um monólito Django funcional para autenticação, cadastro de cursos, rascunhos, submissão e aprovação inicial do orientador. Ainda não possui o ciclo completo de defesa/publicação nem a arquitetura distribuída e API REST exigidas. Não há base para declarar um percentual preciso de conclusão: os requisitos têm tamanhos muito diferentes.

### Funcionalidades existentes

- Login/logout com django-allauth; senhas por mecanismos do Django e validadores de senha configurados.
- Grupos `Alunos`, `Professores` e `Coordenadores`, com criação por migração. Apenas alunos e professores possuem fluxos acadêmicos específicos.
- Cadastro de contas e grupos pelo Django admin; cadastro público fechado.
- CRUD HTML de cursos com permissões para escrita.
- Criação e edição do próprio rascunho, escolha de orientador ativo do grupo Professores, upload e acompanhamento de todos os trabalhos do aluno.
- Validação de PDF: tamanho de 50 MiB, extensão, assinatura, leitura, páginas e rejeição de criptografia.
- SHA-256 calculado no formulário e conferido antes da aprovação do orientador.
- Listagem privada do professor vinculada à orientação; rascunhos não são listados nessa área.
- Download privado com verificação do vínculo de aluno ou orientador.
- Aprovação pelo orientador em POST com CSRF, responsável/data e transação.
- Estados atuais: `rascunho`, `em_avaliacao`, `aprovada_orientador`. Não existe ainda estado de publicação.

### Matriz de atendimento

“Implementado” significa presente no fluxo atual analisado, não certificação de produção. “Parcial” indica que apenas parte do requisito é atendida. A coluna considera a main; o avanço separado de bancas está descrito adiante.

| ID | Situação | Evidência ou trabalho restante |
| --- | --- | --- |
| RF01 | Implementado | Login por credenciais com allauth configurado e testado |
| RF02 | Parcial | Admin e grupos de aluno/professor; falta coordenador com vínculo de curso e matriz completa de autorização |
| RF03 | Pendente | Token temporário para membro externo, expiração, escopo e revogação |
| RF04 | Implementado na configuração | Hash de senhas e validadores Django; os testes isolados usam MD5 somente para desempenho e não verificam a robustez do ambiente real |
| RF05 | Parcial | Página inicial por grupo; faltam dashboards completos e área de coordenador |
| RF06 | Parcial | Controle nos fluxos existentes; faltam fluxos externos, bancas e avaliações e proteção uniforme no admin |
| RF07 | Pendente | Nenhuma restrição institucional por IP/VPN no admin |
| RF08 | Parcial | Cursos e contas no admin; faltam dados acadêmicos e CRUD completo de monografias, bancas e avaliações |
| RF09 | Pendente nos fluxos acadêmicos | Não há pesquisa com os critérios do enunciado nas páginas atuais; busca genérica do admin de usuários não cobre o requisito |
| RF10 | Parcial | Edição de rascunho bloqueada nas views após submissão; admin permite alteração e bancas ainda não têm edição |
| RF11 | Pendente | Avaliação não existe |
| RF12 | Parcial | Escrita de cursos e admin exige permissão; falta regra específica de exclusão e estado publicada |
| RF13 | Implementado | Rascunho do aluno com orientador opcional até a submissão |
| RF14 | Implementado no fluxo atual | Upload e acompanhamento de rascunho/submissão/aprovação do orientador; faltam etapas futuras |
| RF15 | Implementado no formulário | Validador de PDF e limite; cobertura de testes precisa ampliar casos inválidos |
| RF16 | Parcial | Hash armazenado; não há deduplicação baseada no hash |
| RF17 | Parcial | Aprovação registrada; não há agendamento completo onde se possa validar toda a regra |
| RF18 | Pendente | Biblioteca lê PDF para validação; não extrai/indexa texto via fila |
| RF19 | Parcial | Verificação antes da aprovação; alterações posteriores não são detectadas por um fluxo próprio e o admin pode recalcular hash mantendo a aprovação |
| RF20 | Pendente na main | Proposta inicial na branch de bancas; falta agendamento efetivo e coordenador |
| RF21 | Pendente na main | Branch de bancas tem data/local/link, mas não membros |
| RF22 | Pendente | Convites e confirmações de disponibilidade |
| RF23 | Pendente | Membros, intervalos de defesa e bloqueio de conflitos |
| RF24 | Pendente | Eventos de agendamento e notificações assíncronas |
| RF25 | Pendente | Notas, parecer e recomendação por membro após defesa |
| RF26 | Pendente | Fechamento somente após todas as avaliações e cálculo do resultado |
| RF27 | Pendente | Documentos complementares e tipos |
| RF28 | Pendente | Versão corrigida e fluxo de validação |
| RF29 | Pendente | Publicação automática condicionada à aprovação final e documentos |
| RF30 | Pendente | Repositório público só de publicadas |
| RF31 | Pendente | Pesquisa pública por todos os critérios exigidos |
| RF32 | Pendente | DRF ausente das dependências/configuração; não há serializers, viewsets ou rotas JSON |
| RF33 | Pendente | Cursos têm HTML público; não há endpoints JSON públicos de cursos, orientadores e publicadas |
| RF34 | Pendente | CRUD autenticado via REST para alunos, monografias, bancas e avaliações |
| RF35 | Pendente, etapa posterior | Templates Django são apoio ao desenvolvimento; frontend JavaScript consumindo API ainda não existe |
| RF36 | Parcial | Django admin possui seu log padrão; não existe auditoria geral de todas as operações acadêmicas |
| RF37 | Parcial | Aprovação registra responsável/data; upload, submissão e demais ações não têm histórico completo |
| RF38 | Pendente | Agregações por curso, orientador e ano e gráficos |
| RF39 | Pendente | Taxa de aprovação e duração média entre submissão e defesa |

Todos os itens RD01 a RD07 estão pendentes: cache de sessões, cache de buscas, controle de upload em andamento, limitação de submissões, broker de mensagens, extração/indexação e notificações por fila.

Requisitos não funcionais: há base de autenticação, privacidade de arquivos e integridade inicial; faltam serviços independentes, infraestrutura de cache/fila, rastreabilidade completa, testes de carga e critérios mensuráveis de desempenho.

## Trabalho já iniciado na branch de bancas

`origin/feat/preparacao-de-banca` deve ser aproveitada, não reimplementada sem necessidade. Foi inspecionada por `git show`/`git diff`; não foi integrada nem executada nesta revisão.

Ela possui:

- Modelo `Banca` com monografia, data/hora, local/link e estados preparação/agendada/realizada/cancelada.
- Migração `0007_banca`.
- Formulário exigindo local ou link.
- Rota e página de preparação acessíveis ao orientador vinculado, apenas após aprovação dele.
- Bloqueio de nova proposta se houver banca não cancelada, usando bloqueio da monografia na transação.

Ainda não possui membros, confirmação, duração/fim, conflitos, acesso do coordenador, convites externos, edição/cancelamento por fluxo, notificações ou transição real para agendada. O formulário não valida explicitamente data futura. Não acrescenta testes aos 21 existentes. Portanto, é preparação de banca, não o agendamento completo do enunciado.

## Problemas a corrigir na base existente

### 1. Admin contorna a restrição de edição após submissão

`monografias/admin.py` usa `MonografiaForm` sem bloquear edição por status. Em teste temporário com banco isolado, o admin alterou o título de uma monografia `aprovada_orientador` e manteve a aprovação. A seleção de um novo PDF também passa pelo formulário que recalcula o hash, sem fluxo de invalidação da aprovação. Essa última possibilidade foi identificada no código; não foi o cenário executado no teste temporário.

Correção proposta: centralizar regras de edição e aprovação e aplicá-las em views, admin e API futura. Definir versionamento e quando uma alteração invalida aprovação. A proteção deve cobrir todos os caminhos de escrita da aplicação.

### 2. Exclusão de curso vinculado resulta em erro sem tratamento

`Curso` é protegido por `Monografia.curso` com `PROTECT`, mas `excluir_curso` não trata `ProtectedError`. Foi reproduzida a exceção ao excluir curso com trabalho vinculado. O banco impede a exclusão, mas a aplicação deve responder com mensagem adequada em HTML e erro de conflito/validação na futura API.

### 3. Auditoria e integridade ainda são pontuais

O hash é calculado no formulário, não num fluxo compartilhado por todas as futuras entradas. O registro de aprovação não equivale a histórico de alterações. O hash isolado também não elimina submissões duplicadas. Falta política de retenção de arquivos antigos quando há substituição do PDF.

### 4. Configuração atual é de desenvolvimento

`SECRET_KEY` fixa no repositório, `DEBUG=True`, hosts não configurados, e-mails somente no console e ausência de restrição institucional. A configuração de implantação precisa separar ambientes e segredos, e definir HTTPS/cookies conforme a infraestrutura. Não se deve simplesmente ligar redirecionamento HTTPS no servidor local sem configurar o ambiente.

### 5. Arquivos locais continuam versionados

Há 24 arquivos `.pyc`, `db.sqlite3` e dois PDFs dentro de `uploads_privados` rastreados. O `.gitignore` não remove arquivos já rastreados. Precisam sair do índice Git mantendo as cópias locais. Isso não apaga versões do histórico; caso algum arquivo não devesse ter sido compartilhado, a limpeza do histórico é uma decisão separada.

### 6. Documentação e testes precisam acompanhar as etapas

Os checklists em `requisitos.md` descrevem escopo, não progresso; permanecem desmarcados inclusive para funcionalidades existentes. A seção de situação inicial está desatualizada. Faltam testes de cursos, admin, bancas, arquivos inválidos, API e infraestrutura. Os módulos vazios em `usuarios/views.py` e `usuarios/tests.py` não representam funcionalidades implementadas.

## Dados que faltam para o fluxo completo

- Aluno: matrícula e vínculos acadêmicos com curso/orientador, conforme a política institucional.
- Professor: departamento e área de pesquisa conforme a estrutura escolhida.
- Curso: coordenador e autorização por curso.
- Monografia: palavras-chave, data de submissão, resultado final, versão dos arquivos, publicação e dados que permitam busca por ano de defesa.
- Banca: membros internos/externos, convites, respostas, intervalo de horário e responsável pelo agendamento.
- Avaliação: vínculo de banca/membro, nota, parecer, recomendação e fechamento.
- Documentos: tipo, arquivo, versão, validação e autorização assinada.
- Auditoria: ator, ação, registro afetado, alteração e horário, preservando dados privados.

## Sequência de trabalho acompanhada

Cada etapa deve explicar o problema, apresentar a mudança, mostrar um teste e permitir ao aluno reproduzir o fluxo. O frontend definitivo fica para depois; os templates atuais e testes podem apoiar o aprendizado do backend. A extração/indexação interna nunca deve tornar rascunhos públicos.

| Ordem | Branch proposta | Entrega verificável |
| --- | --- | --- |
| 1 | `codex/backend-regras-e-integridade` | Bloqueio uniforme após submissão/aprovação, tratamento da exclusão de curso e testes de regressão |
| 2 | `codex/backend-cadastros-e-permissoes` | Dados acadêmicos, coordenador vinculado ao curso e autorização compartilhada |
| 3 | `codex/backend-bancas` | Partir da preparação existente, revisar/testar e completar membros, convites, confirmações, intervalo, conflitos e agendamento |
| 4 | `codex/backend-avaliacoes` | Avaliações por membro, edição antes do fechamento e resultado somente após todas as avaliações |
| 5 | `codex/backend-documentos-publicacao` | Documentos, versão corrigida, condições de publicação e proteção de exclusão |
| 6 | `codex/backend-api` | DRF com autenticação/autorização, CRUDs, busca pública só de publicadas, paginação, erros e contrato OpenAPI para o front |
| 7 | `codex/backend-eventos-e-cache` | Broker/worker, Redis, processamento idempotente, extração/indexação, notificações, proteção de uploads e rate limiting |
| 8 | `codex/backend-auditoria-e-operacao` | Concluir auditoria iniciada nos fluxos, IP/VPN, ambientes, segredos e remoção de arquivos locais do índice |
| 9 | `codex/backend-servicos-e-relatorios` | Serviços independentes com APIs, integração, métricas do dashboard e testes de carga |

As branches são uma proposta de divisão; somente a branch de diagnóstico foi criada agora. Os limites dos serviços e contratos de eventos devem ser decididos antes de ampliar a persistência e mensageria, mesmo que a separação de execução aconteça depois. Auditoria deve entrar junto das novas ações desde as primeiras etapas. A infraestrutura de fila será necessária para que o agendamento entregue notificações e a publicação/indexação atendam integralmente ao enunciado.

Nenhuma escolha acadêmica deve ser escondida em constantes inventadas. Antes da etapa correspondente, definir: escala/fórmula e critérios de aprovação; ressalvas e correções; duração das defesas; composição da banca; expiração de convites externos; validação da assinatura; versionamento; rede institucional; limites de submissão e metas de carga. RabbitMQ ou Kafka e biblioteca de tarefas também continuam como decisões técnicas pendentes.

## Validação realizada

- `venv/bin/python manage.py test --settings=config.settings_test`: 21 testes passaram com SQLite em memória e uploads temporários.
- `venv/bin/python manage.py makemigrations --check --dry-run --settings=config.settings_test`: nenhuma diferença detectada na branch atual.
- Dois testes temporários adicionais reproduziram edição pelo admin de trabalho aprovado e `ProtectedError` na exclusão de curso vinculado. Não foram adicionados à suíte: devem se tornar testes de regressão quando as correções forem implementadas.
- `check --deploy` usando as configurações isoladas, que herdam as configurações locais: um erro de backend de e-mail de desenvolvimento e sete alertas de segurança/implantação. Não é uma certificação de produção e não acessou o PostgreSQL.
- Não foram executados testes da branch de bancas, concorrência real, Redis, broker, serviços independentes ou carga. Essas implementações/ambientes ainda não estão disponíveis na branch analisada.

O próximo passo recomendado é a etapa 1: corrigir as regras existentes antes de expandir bancas e API. Ao final do backend, revisar código, regras, contrato JSON, permissões e testes integrados antes de começar o frontend JavaScript.
