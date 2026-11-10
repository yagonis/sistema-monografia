# Etapa: autenticação e orientação

## Resultado da análise do enunciado

O PDF fornecido exige allauth, diferenciação por permissões, acompanhamento e aprovação pelo orientador antes da banca. Esta entrega implementa essa etapa sobre as páginas Django existentes. Ainda não implementa a interface JavaScript consumindo REST exigida na entrega final.

## Funcionalidades desta etapa

- Login em `/contas/login/` e logout por POST, usando django-allauth e sessão Django.
- Página inicial com navegação conforme os grupos atribuídos pela administração.
- Grupos `Alunos`, `Professores` e `Coordenadores` criados por migração. O grupo de coordenadores está reservado: ainda não concede fluxo de banca.
- Alunos criam e editam seus próprios rascunhos e acompanham todos os seus trabalhos em `/minhas-monografias/`.
- Professores acessam `/orientacoes/`, que mostra somente trabalhos submetidos à sua orientação e os já aprovados por eles. Rascunhos não são expostos ao professor.
- Download privado em `/monografias/<id>/pdf/`: autor com perfil de aluno ou orientador com perfil de professor, após submissão. Sem rota pública para a pasta de uploads.
- Aprovação somente por POST com CSRF, pelo orientador vinculado, em estado `em_avaliacao`. Verifica o SHA-256 do arquivo antes de aprovar.
- Estado `aprovada_orientador`, `aprovado_por` e `aprovado_em` registram a decisão. Não representa aprovação em defesa nem publicação.
- Edição e submissão do rascunho e aprovação utilizam transações e bloqueio do registro no PostgreSQL.
- Corrigido o nome da exceção na rejeição de PDF acima de 50 MiB.

Os grupos acadêmicos não concedem `is_staff` nem acesso automático ao admin. Um usuário pode acumular grupos quando a instituição assim determinar. Superusuários também precisam do grupo acadêmico correspondente para usar essas telas; continuam com acesso administrativo pelo Django admin.

## Instalação e uso local

No ambiente virtual do projeto, com PostgreSQL operacional e `DB_PASSWORD` já definida:

```bash
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

As migrações do PostgreSQL local não foram executadas nesta entrega. Elas criam os grupos e os campos de aprovação, além das tabelas do allauth. Não adicionam automaticamente usuários existentes aos grupos, pois não há informação confiável sobre seus papéis.

1. Entre em `/admin/` com o superusuário existente.
2. Em usuários, crie ou edite contas e atribua `Alunos` aos alunos e `Professores` aos orientadores. Não é necessário conceder acesso ao admin para esses perfis.
3. Entre em `/contas/login/` como aluno, crie um rascunho com um PDF válido e escolha um professor ativo como orientador. Submeta o trabalho.
4. Em outra sessão, entre como o professor selecionado e abra “Minhas orientações”. Baixe o PDF e aprove a submissão.
5. Como aluno, consulte “Minhas monografias” para ver o novo status.

O cadastro público está fechado pelo adapter para impedir autoatribuição de papéis institucionais. A autenticação usa os nomes de usuário e senhas das contas Django existentes. A restrição de IP/VPN do admin continua pendente, portanto o admin existente ainda não atende a esse requisito do enunciado.

## Validação

Ambiente usado: Python 3.12, Django 6.1.3, django-allauth 65.21.1 e pypdf 7.0.0.

```bash
python manage.py test --settings=config.settings_test
python manage.py makemigrations --check --dry-run --settings=config.settings_test
```

Os testes usam SQLite em memória e uploads temporários. Cobrem login/logout, credenciais inválidas, conta inativa, perfis, isolamento entre usuários, download privado, submissão, aprovação, integridade do PDF e CSRF. Não validam concorrência real ou operação do PostgreSQL. O arquivo de configurações de teste não deve ser usado para servir a aplicação.

Integração baseada na [instalação oficial do allauth](https://docs.allauth.org/en/latest/installation/quickstart.html) e no [adapter de contas](https://docs.allauth.org/en/latest/account/advanced.html).

## Próximas etapas

1. Disponibilizar REST/JSON via Django REST Framework, reutilizando as verificações de perfil, vínculo e estado. Adaptar a interface para JavaScript conforme o enunciado.
2. Implementar bancas: agendamento permitido apenas após aprovação do orientador, membros, confirmação de disponibilidade e conflitos.
3. Implementar avaliações, resultado final, documentos e publicação condicionada. Definir antes escala de notas e critérios acadêmicos.
4. Completar cadastros acadêmicos, auditoria geral e restrição institucional do admin.
5. Integrar fila para extração de texto/notificações e Redis para sessões, busca, controle de uploads e limitação de taxa.
6. Separar serviços independentes, implementar busca pública, relatórios e validar desempenho.

`requisitos.md` descreve o escopo integral. As rotas desta etapa retornam HTML, arquivos ou redirecionamentos; ainda não são um contrato REST/JSON para um front-end separado.
