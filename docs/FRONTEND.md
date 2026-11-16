# Portal de monografias

Branch de implementação: `codex/frontend-portal`, criada a partir da main após o merge aprovado do backend.

## Execução

O portal está na página inicial `/`. Não há servidor Node separado, dependências npm ou etapa de compilação JavaScript. O Django entrega a estrutura HTML e os módulos JavaScript consomem a API real da mesma origem.

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Mantenha `DB_PASSWORD` e as demais variáveis do backend configuradas. A fila e o worker continuam necessários para extração, notificações, resultado final e publicação; a interface não substitui esse processamento por simulações.

No Docker:

```bash
docker compose build backend worker beat repositorio
docker compose up -d
```

O Dockerfile executa `collectstatic` no build. WhiteNoise entrega os estáticos no Gunicorn. Para implantação fora do Docker, rode `python manage.py collectstatic --noinput` antes de reiniciar o servidor. O diretório gerado `staticfiles/` não deve ser versionado.

## Navegação

- `/#/acervo`: consulta pública com busca, curso, orientação, ano da defesa, palavras-chave e paginação.
- `/#/acervo/{id}`: resumo, metadados e download da versão publicada.
- `/#/login`: login por sessão e CSRF; acesso público continua disponível sem conta.
- `/#/painel`: visão geral dos trabalhos visíveis ao usuário e agenda de bancas.
- `/#/trabalhos`: listagem e filtros de trabalhos vinculados à conta.
- `/#/trabalhos/novo` e `/#/trabalhos/{id}/editar`: rascunho e upload PDF.
- `/#/trabalhos/{id}`: acompanhamento, submissão, aprovação pelo orientador, documentos e preparação de banca conforme as permissões.
- `/#/bancas`: agenda, detalhes, membros, confirmações, convites externos, renovação/revogação de token, agendamento, cancelamento e avaliações.
- `/#/relatorios`: gráficos de barras e indicadores limitados ao escopo autorizado.
- `/#/externo`: acesso temporário por código, confirmação de disponibilidade, download e avaliação do próprio membro.
- `/#/cadastros`: cursos, contas de usuário, perfis acadêmicos e vínculos, exclusivos da administração autorizada.
- `/#/operacao`: auditoria e eventos; permite liberar nova tentativa de processamento pendente.

As antigas rotas HTML de desenvolvimento continuam disponíveis para compatibilidade. O fallback sem JavaScript apresenta links para login e áreas tradicionais.

## Organização do código

- `monografias/templates/monografias/portal.html`: estrutura inicial, metadados, estilos e módulos.
- `monografias/static/portal/app.js`: navegação, telas e interações do portal.
- `monografias/static/portal/api.js`: HTTP, sessão, CSRF, multipart, downloads e mensagens de erro.
- `monografias/static/portal/ui.js`: componentes pequenos, escape HTML e apresentação de datas/status.
- `monografias/static/portal/portal.css`: identidade visual, componentes e regras responsivas.

Direção visual: portal acadêmico com tons verdes, superfícies claras, tipografia serifada nas chamadas e navegação lateral. Os elementos decorativos são CSS/SVG locais; não há fontes, imagens ou bibliotecas dependentes de CDNs.

## Integração e segurança

O portal não usa dados fictícios como fallback. Falhas da API apresentam mensagens e opção de tentar novamente. Paginação pública usa o contrato do backend; listas internas percorrem as páginas disponíveis e aplicam filtros locais. Para conjuntos internos muito grandes, a evolução indicada é adicionar filtros e paginação no servidor também nessas telas.

A interface recebe do `/api/conta/` nome, grupos e indicador de administrador. O novo `/api/grupos/` permite que a administração atribua papéis por seletores, sem IDs fixos no frontend. O acesso externo também recebe o estado da banca, sua própria confirmação e sua própria avaliação para exibir somente as ações adequadas à etapa. Nenhuma avaliação de outro membro é incluída.

O endpoint de grupos exige superusuário e rede autorizada; não amplia as permissões do backend.

Sessões continuam nos cookies. CSRF é atualizado após login. Tokens externos são mantidos somente na memória da aba, nunca em URL ou armazenamento persistente, e enviados pelo cabeçalho `X-Banca-Token`.

Os botões refletem o perfil e o vínculo; a autorização final continua no backend. Conteúdo vindo da API é escapado antes de entrar no HTML. Links de videoconferência aceitam somente HTTP/HTTPS e são abertos com proteção contra acesso à aba de origem.

Ações de submissão, aprovação, agendamento, cancelamento, validação e exclusão pedem confirmação com suas consequências. O envio de formulários bloqueia cliques duplicados enquanto aguarda a resposta. Downloads autorizados recebem o PDF pela API, não por caminho público de uploads.

A interface cobre as regras atuais: escala de 0 a 10 e média aritmética. Se a política acadêmica mudar, os limites e os rótulos da avaliação também devem acompanhar a alteração do backend.

## Verificação

- 68 testes Django passaram, incluindo entrega do portal, metadados da sessão e autorização da consulta de grupos.
- `node scripts/test_frontend.mjs` passou: escape HTML, mensagens, CSRF, credenciais de sessão, upload multipart, token externo e paginação na mesma origem.
- Módulos JavaScript verificados sintaticamente com Node.
- `collectstatic` executado com sucesso e OpenAPI atualizado.
- Navegador real com banco e arquivos temporários: acervo, login, edição e submissão de rascunho, relatórios, banca do professor, troca de perfil, administração, convite externo e mensagem para token inválido.
- Layout verificado em 1440 px e 390 px, incluindo menu recolhível e tabelas com rolagem interna.

As fixtures foram usadas apenas na prévia isolada e não fazem parte do produto. O PostgreSQL pessoal não foi alterado. O envio efetivo de e-mails, a conclusão de resultado por fila e a publicação continuam sendo responsabilidades do backend já validado anteriormente; não foram novamente executados como parte desta revisão visual.
