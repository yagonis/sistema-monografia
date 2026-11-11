# Etapa 2 — cadastros acadêmicos e coordenação

Branch: `codex/backend-cadastros-e-permissoes`, baseada na etapa 1, registrada localmente no commit `20c5702`. Não foi realizado push nesta etapa.

## O que mudou

- `PerfilAluno`: conta de usuário, matrícula única, curso e orientador atual opcional.
- `PerfilProfessor`: conta de usuário, departamento e área de pesquisa.
- `Curso.coordenador`: conta ativa do grupo `Coordenadores`, selecionada pela administração.
- `Usuario.eh_coordenador`: verificação do grupo e da atividade da conta.
- Área `/coordenacao/`: lista cursos sob responsabilidade do usuário e monografias que saíram de rascunho nesses cursos.
- Download privado também permitido ao coordenador vinculado ao curso da monografia, exceto rascunhos.
- Formulários de perfis no admin de usuários e coluna de coordenador no admin de cursos.
- Exclusão de curso protegido por monografia ou perfil de aluno retorna mensagem de conflito, sem apagar os registros.

## Por que perfis separados

Os dados de login continuam no modelo `Usuario`. Os dados acadêmicos ficam em relações `OneToOneField`: cada usuário pode ter no máximo um perfil de aluno e um de professor, e pode ter os dois. Não há duplicação de senha ou e-mail.

Os perfis não concedem privilégios. Criar `PerfilProfessor` não coloca a conta no grupo Professores nem permite entrar no admin. Os grupos continuam atribuídos pela administração. Nome e e-mail continuam nos campos herdados de `AbstractUser`.

Não são criados perfis automaticamente para contas antigas: não é possível inferir matrícula e curso com segurança. As contas antigas continuam funcionando e os dados podem ser preenchidos progressivamente. Os campos de professor podem ser completados depois; um perfil de aluno, quando cadastrado, exige matrícula e curso.

## Como funciona a permissão

A consulta `monografias_da_coordenacao`, em `monografias/permissoes.py`, exige simultaneamente:

1. Usuário autenticado e ativo no grupo Coordenadores.
2. Vínculo desse usuário em `curso.coordenador`.
3. Trabalho fora do status rascunho.

A mesma consulta é usada na listagem e no download. Assim, ocultar links não é a única proteção: tentar acessar diretamente o PDF de outro curso retorna 404. Ter apenas o grupo ou apenas o vínculo não basta.

O coordenador não ganha poderes para editar a monografia, aprovar como orientador ou administrar cursos. Se também tiver grupo de professor e for o orientador do trabalho, os poderes de orientação existentes se aplicam por esse vínculo independente. O agendamento de bancas continua para a próxima etapa.

## Aplicar e acompanhar

Com o ambiente virtual e `DB_PASSWORD` configurados:

```bash
python manage.py migrate
python manage.py runserver
```

1. No admin de usuários, adicione a conta desejada ao grupo Coordenadores e salve.
2. No admin de cursos, selecione essa conta como coordenador do curso.
3. No admin de um usuário existente, use as seções de perfil de aluno e/ou professor para completar os dados acadêmicos. Para atribuir orientador atual, a conta do orientador precisa estar ativa no grupo Professores.
4. Entre no sistema como coordenador e abra o link Coordenação.
5. Confira que somente submissões dos seus cursos aparecem e que não há acesso a rascunhos.

O vínculo do curso é configurado no admin, não no formulário comum de cursos, para evitar que a permissão genérica de edição de nome/código permita trocar a pessoa responsável pelo acesso privado.

## Migrações e limites

Criadas `monografias/0007_curso_coordenador` e `usuarios/0003_perfilaluno_perfilprofessor`. As dependências foram geradas e aplicadas no banco isolado dos testes. Não foi alterado o PostgreSQL real.

A branch remota de preparação de bancas já tem uma migração independente `0007_banca`. Ao integrá-la, as duas folhas de migração devem ser conciliadas por uma migração de merge que dependa de ambas, preservando o histórico já aplicado. Isso será tratado junto à etapa de bancas.

O curso e o orientador atual do perfil descrevem o vínculo acadêmico atual; os campos na monografia preservam o vínculo daquele trabalho. Alterar um perfil não reatribui monografias existentes. Ainda não foi criada uma política de obrigar novas submissões a usar exclusivamente o curso do perfil: isso alteraria o comportamento das contas antigas e exige uma regra explícita de matrícula/vínculo.

Esta entrega usa o admin para cadastros e templates mínimos para acompanhar o backend. CRUD JSON e frontend JavaScript continuam pendentes. Nenhuma configuração de grupo torna um usuário staff automaticamente.

## Validação

43 testes passaram, incluindo os 29 anteriores. Cobertura nova: perfis coexistentes, matrícula obrigatória/única, contas antigas sem perfis, seletor de coordenador ativo, campos do admin, curso protegido por matrícula e isolamento da coordenação por grupo/curso/status. A verificação de migrações não detectou alterações faltantes.

```bash
python manage.py test --settings=config.settings_test
python manage.py makemigrations --check --dry-run --settings=config.settings_test
```

Os testes usam SQLite em memória e arquivos temporários. Não validam operação ou concorrência no PostgreSQL real.
