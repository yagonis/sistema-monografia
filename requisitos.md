# Requisitos — Repositório de Monografias

## 1. Objetivo

Desenvolver um sistema distribuído para cadastro, submissão, avaliação e publicação de monografias (TCC). O sistema deve permitir que alunos enviem trabalhos, orientadores aprovem submissões, responsáveis agendem bancas e visitantes pesquisem trabalhos publicados.

Este documento organiza os requisitos do enunciado **Trabalho de Sistemas Distribuídos**, do professor Alessandro Vivas Andrade. Os checklists descrevem o escopo a implementar e verificar; não representam funcionalidades já concluídas.

## 2. Tecnologias e restrições

| Item | Requisito |
| --- | --- |
| Linguagem do backend | Python |
| Framework | Django, na última versão conforme solicitado no enunciado |
| API REST | Django REST Framework |
| Autenticação | django-allauth |
| Banco de dados | PostgreSQL |
| Cache e controle de submissões | Redis |
| Mensageria | RabbitMQ ou Kafka; escolha pendente |
| Processamento de PDF | Biblioteca de leitura e extração de texto, como pdfplumber ou equivalente |
| Frontend | JavaScript, consumindo a API |
| Ambiente | Linux |
| Arquitetura | Múltiplos microsserviços independentes, cada um com sua API |
| Equipe | Até cinco alunos |

Decisão de desenvolvimento: utilizar ambiente virtual Python (`.venv`) para isolar as dependências. No desenvolvimento local em Windows, utilizar Ubuntu pelo WSL. Registrar as versões efetivamente usadas no repositório.

## 3. Atores

| Ator | Responsabilidades e acesso |
| --- | --- |
| Administrador | Administrar o sistema conforme suas permissões |
| Coordenador de curso | Gerenciar atividades do curso e agendar bancas |
| Professor/orientador | Acompanhar trabalhos, aprovar submissões, agendar bancas e avaliar quando designado |
| Aluno | Criar rascunhos, enviar arquivos e acompanhar suas submissões |
| Membro externo de banca | Acessar a banca por token temporário, sem conta permanente |
| Visitante | Pesquisar e consultar monografias publicadas sem autenticação |

Os papéis devem ser acompanhados de verificações de permissão e de vínculo com cada registro. A matriz detalhada de permissões ainda será definida.

## 4. Requisitos funcionais

### 4.1. Autenticação e autorização

- [ ] **RF01** Implementar autenticação com django-allauth e login por credenciais de usuário e senha.
- [ ] **RF02** Controlar acesso de administradores, coordenadores, professores/orientadores e alunos por permissões.
- [ ] **RF03** Permitir acesso temporário de membros externos por token, sem conta permanente.
- [ ] **RF04** Armazenar senhas usando hash seguro e aplicar políticas de senha.
- [ ] **RF05** Disponibilizar página principal e dashboard personalizado por tipo de usuário.
- [ ] **RF06** Restringir operações administrativas e de submissão a usuários autenticados e autorizados, contemplando o acesso temporário dos membros externos.
- [ ] **RF07** Restringir a área administrativa à rede institucional, por IP ou VPN.

### 4.2. Cadastros e CRUD

- [ ] **RF08** Disponibilizar criação, leitura, atualização e exclusão autorizada de alunos, professores, cursos, monografias, bancas e avaliações.
- [ ] **RF09** Permitir busca pelos critérios aplicáveis: aluno/autor, orientador, curso, ano de defesa e palavras-chave.
- [ ] **RF10** Permitir edição de monografias em rascunho e de bancas ainda não realizadas.
- [ ] **RF11** Permitir edição de avaliação somente pelo respectivo avaliador e antes do fechamento do resultado.
- [ ] **RF12** Impedir a exclusão de monografias publicadas e restringir as demais exclusões a usuários autorizados.

### 4.3. Submissão de monografias

- [ ] **RF13** Permitir que o aluno crie um rascunho e associe um orientador.
- [ ] **RF14** Permitir upload do PDF e acompanhamento do status da submissão.
- [ ] **RF15** Validar formato PDF e tamanho máximo permitido.
- [ ] **RF16** Calcular e armazenar SHA-256 de cada arquivo submetido, para deduplicação e verificação de integridade.
- [ ] **RF17** Registrar a aprovação do orientador antes do encaminhamento para agendamento de banca.
- [ ] **RF18** Extrair texto do PDF de forma assíncrona, via fila, para indexação de busca.
- [ ] **RF19** Detectar alterações não autorizadas em arquivos após a aprovação usando o hash armazenado.

### 4.4. Bancas e avaliações

- [ ] **RF20** Permitir ao coordenador ou orientador agendar banca de monografia aprovada pelo orientador.
- [ ] **RF21** Registrar data, local presencial ou link remoto e membros internos e/ou externos.
- [ ] **RF22** Validar a confirmação de disponibilidade de todos os membros convidados.
- [ ] **RF23** Impedir conflito de horário entre bancas dos mesmos membros.
- [ ] **RF24** Notificar membros e aluno após o agendamento, utilizando fila de eventos.
- [ ] **RF25** Permitir que cada membro registre nota, parecer e recomendação após a defesa.
- [ ] **RF26** Calcular o resultado final apenas após todas as avaliações e atualizar o status da monografia.

### 4.5. Documentos e publicação

- [ ] **RF27** Registrar documentos complementares, como ata de defesa, termo de autorização e comprovante de correção ortográfica.
- [ ] **RF28** Receber a versão corrigida quando a aprovação tiver ressalvas.
- [ ] **RF29** Publicar automaticamente somente após aprovação final, entrega da versão corrigida quando aplicável e termo de autorização assinado.
- [ ] **RF30** Disponibilizar consulta pública sem login exclusivamente às monografias publicadas.
- [ ] **RF31** Permitir pesquisa pública por título, autor, orientador, curso, ano de defesa e palavras-chave.

### 4.6. API e frontend

- [ ] **RF32** Disponibilizar API REST com respostas JSON usando Django REST Framework.
- [ ] **RF33** Expor endpoints públicos para monografias publicadas, cursos e orientadores.
- [ ] **RF34** Expor CRUD autenticado para alunos, monografias, bancas e avaliações, respeitando permissões e regras de negócio.
- [ ] **RF35** Construir interface JavaScript que consuma a API para submissão, acompanhamento, aprovação, agendamento, avaliação e pesquisa pública.

Exemplos de rotas presentes no enunciado, sujeitos à padronização durante o desenvolvimento:

```http
POST /api/monografias
POST /api/bancas
GET /api/monografias?busca=sistemas+distribuidos
```

### 4.7. Auditoria e dashboards

- [ ] **RF36** Registrar quem realizou cada alteração, qual foi a alteração e sua data e hora.
- [ ] **RF37** Auditar ações como upload, aprovação do orientador, agendamento e lançamento de avaliação.
- [ ] **RF38** Exibir gráficos de monografias por curso, orientador e ano de defesa.
- [ ] **RF39** Exibir taxa de aprovação e tempo médio entre submissão e defesa.

Chart.js e Plotly são sugestões do enunciado para os gráficos; a escolha não é obrigatória nem está definida.

## 5. Regras de negócio

| ID | Regra |
| --- | --- |
| RN01 | A banca não pode ser agendada sem aprovação prévia do orientador. |
| RN02 | O upload deve ser validado quanto a formato, tamanho e hash. O enunciado sugere 50 MB como exemplo; o limite final deve ser definido. |
| RN03 | A extração de texto não deve acontecer durante a requisição de upload. |
| RN04 | O agendamento exige confirmação de todos os membros e ausência de conflito de horário. |
| RN05 | O resultado final depende do registro de todas as avaliações da banca. |
| RN06 | Somente o autor da avaliação pode editá-la, antes do fechamento do resultado. |
| RN07 | Publicação exige aprovação final, correções quando aplicáveis e termo de autorização assinado. |
| RN08 | Monografias publicadas não podem ser excluídas pelo CRUD. |
| RN09 | Rascunhos e trabalhos não publicados não devem ser expostos no repositório público. |
| RN10 | Redis deve impedir reenvio duplicado enquanto o upload estiver em processamento e limitar a taxa de submissões. |
| RN11 | O acesso de membros externos deve expirar e não exigir conta permanente. |
| RN12 | Acesso ao painel administrativo exige autorização e origem na rede institucional/IP/VPN. |

A aprovação do orientador e a aprovação final em banca são decisões diferentes e devem ser registradas separadamente. A política de envio e aprovação da versão corrigida precisa ser definida sem permitir edição irrestrita de trabalhos já aprovados.

## 6. Estrutura de dados de referência

O enunciado apresenta a seguinte estrutura como sugestão. Os modelos finais podem ser ajustados, preservando as funcionalidades e regras exigidas.

| Entidade | Dados principais |
| --- | --- |
| Aluno | Nome, matrícula, e-mail, curso, orientador atual |
| Professor | Nome, e-mail, departamento, área de pesquisa |
| Curso | Nome, código, coordenador |
| Monografia | Título, resumo, palavras-chave, aluno, orientador, curso, data de submissão, PDF, SHA-256, status |
| Banca | Monografia, data, local ou link, membros internos/externos, status |
| Avaliação | Banca, membro avaliador, nota, parecer, recomendação |
| Documento complementar | Monografia, tipo, arquivo |
| Registro de auditoria | Autor da ação, alteração realizada, data e hora |

Estados sugeridos no enunciado:

- **Monografia:** rascunho, em avaliação, aprovada, reprovada, publicada.
- **Banca:** agendada, realizada, cancelada.
- **Recomendação de avaliação:** aprovado sem ressalvas, aprovado com ressalvas, reprovado.

O detalhamento das transições, aprovações intermediárias e versões de arquivos será definido na implementação.

## 7. Arquitetura distribuída

### 7.1. Serviços

O sistema deve possuir múltiplos serviços independentes, cada um com sua API. A divisão abaixo é exemplificativa no enunciado; os limites finais precisam ser definidos.

| Serviço sugerido | Responsabilidade |
| --- | --- |
| Autenticação | Usuários, login e permissões |
| Monografias | CRUD, submissão, upload e hash |
| Bancas | Agendamento, avaliações e resultado final |
| Repositório e busca | Indexação e consulta pública |
| Notificações | E-mails e alertas |
| Relatórios | Estatísticas e dashboards |

Apps Django dentro de um único projeto não constituem, por si só, microsserviços independentes. A base inicial de desenvolvimento deverá evoluir para atender ao requisito de distribuição.

### 7.2. Redis

- [ ] **RD01** Utilizar Redis para cache de sessões.
- [ ] **RD02** Armazenar em cache resultados de buscas no repositório.
- [ ] **RD03** Controlar uploads em processamento para evitar reenvio duplicado.
- [ ] **RD04** Implementar limitação de taxa de submissões.

Exemplos de chaves sugeridas:

```text
busca:hash_da_query
upload_em_andamento:monografia_id
```

### 7.3. Fila de eventos

- [ ] **RD05** Utilizar RabbitMQ ou Kafka para processamento assíncrono.
- [ ] **RD06** Processar extração de texto e indexação após submissão.
- [ ] **RD07** Enviar notificações de agendamento pela fila.

Eventos sugeridos para organizar os fluxos:

| Evento | Processamento associado |
| --- | --- |
| Monografia submetida | Extração de texto, indexação e notificação ao orientador |
| Banca agendada | Notificação aos membros e ao aluno |
| Avaliação registrada | Verificação de avaliações restantes e cálculo do resultado quando completo |
| Monografia publicada | Indexação pública e notificação por e-mail ao aluno |

A extração e eventual indexação interna de um trabalho submetido não autorizam sua exposição na busca pública.

## 8. Requisitos não funcionais

- [ ] **RNF01 — Escalabilidade:** projetar o repositório para milhares de acessos simultâneos, especialmente em períodos de defesa.
- [ ] **RNF02 — Desacoplamento:** utilizar serviços independentes, APIs e mensageria para separar responsabilidades.
- [ ] **RNF03 — Desempenho:** utilizar cache para consultas frequentes e processamento assíncrono para tarefas pesadas.
- [ ] **RNF04 — Integridade:** armazenar hashes e verificar alterações não autorizadas dos arquivos.
- [ ] **RNF05 — Segurança:** aplicar autenticação, autorização, proteção de senhas e restrição de rede na administração.
- [ ] **RNF06 — Rastreabilidade:** registrar o histórico das alterações e seus responsáveis.

O enunciado não fixa latência, taxa de requisições ou número exato de usuários para teste de carga. Esses critérios devem ser definidos antes da validação de escalabilidade.

## 9. Critérios de aceitação essenciais

| Cenário | Resultado esperado |
| --- | --- |
| Enviar arquivo que não é PDF ou excede o limite configurado | Upload rejeitado com mensagem adequada |
| Submeter PDF válido | Hash armazenado e processamento de texto encaminhado à fila |
| Tentar agendar sem aprovação do orientador | Operação bloqueada |
| Agendar com membro sem confirmação ou com conflito de horário | Operação bloqueada |
| Registrar apenas parte das avaliações | Resultado final permanece em aberto |
| Registrar todas as avaliações | Resultado calculado conforme regra acadêmica definida |
| Tentar editar avaliação de outro membro ou após fechamento | Operação bloqueada |
| Aprovar em banca sem termo assinado | Trabalho não publicado |
| Aprovar com ressalvas sem versão corrigida | Trabalho não publicado |
| Cumprir todas as condições de publicação | Publicação automática e disponibilização na busca pública |
| Consultar o repositório sem login | Acesso permitido apenas ao conteúdo público |
| Tentar excluir monografia publicada | Operação bloqueada |
| Acessar a administração fora da rede permitida | Acesso bloqueado |
| Usar token externo expirado | Acesso bloqueado |
| Executar ação auditável | Histórico registra autor, alteração e data/hora |

## 10. Decisões pendentes

- Escolher RabbitMQ ou Kafka e a biblioteca de processamento de tarefas.
- Definir os limites dos microsserviços e a comunicação/autenticação entre eles.
- Definir o limite de upload e a política para PDFs inválidos ou protegidos por senha.
- Definir escala de notas, fórmula do resultado, critérios de aprovação e tratamento das ressalvas.
- Definir duração das bancas para detectar sobreposição de horários.
- Definir validade, escopo e revogação de tokens de membros externos.
- Definir como verificar a assinatura do termo de autorização.
- Definir versionamento dos PDFs e o efeito de alterações sobre aprovações anteriores.
- Definir a matriz de permissões e os vínculos necessários para cada operação.
- Definir rede institucional, IPs permitidos e uso de VPN.
- Definir prazos de cache, invalidação, limites de submissão e tratamento de falhas de eventos.
- Definir metas e cenários de teste de carga.

Esses pontos não devem ser tratados como regras acadêmicas já estabelecidas pelo enunciado.

## 11. Situação inicial do desenvolvimento

Conforme o progresso relatado durante a configuração do projeto:

- Ambiente Ubuntu/WSL e ambiente virtual Python configurados.
- Projeto Django criado, com apps `monografias` e `usuarios`.
- PostgreSQL conectado ao Django.
- Modelo próprio `Usuario`, baseado em `AbstractUser`, criado e migrado.
- Superusuário criado e acesso ao painel administrativo confirmado.
- Primeira rota e view funcionando.
- Modelo inicial `Curso`, com nome e código único, proposto para implementação e validação.

Essa base ainda não representa a conclusão dos requisitos de autenticação com allauth, restrição de rede, API REST, frontend, microsserviços, Redis ou mensageria.

## 12. Sequência de implementação proposta

1. Validar o cadastro de cursos e aprender consultas com o ORM.
2. Definir os limites dos serviços e completar o modelo de dados acadêmicos.
3. Integrar django-allauth, grupos e permissões.
4. Disponibilizar e validar as APIs com Django REST Framework.
5. Implementar submissão, arquivos, hashes e aprovação do orientador.
6. Implementar bancas, avaliações e regras de resultado.
7. Integrar fila, extração assíncrona, notificações e Redis aos fluxos.
8. Implementar publicação condicionada e busca pública.
9. Construir o frontend JavaScript e os dashboards.
10. Validar auditoria, restrição de rede, integração entre serviços e desempenho.

Esta sequência orienta o aprendizado e pode ser ajustada conforme as dependências técnicas, mantendo o escopo exigido.
