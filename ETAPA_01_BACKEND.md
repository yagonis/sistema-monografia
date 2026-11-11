# Etapa 1 — regras de edição e exclusão de cursos

Branch: `codex/backend-regras-e-integridade`.

## Problema e comportamento corrigido

As páginas do aluno já bloqueavam edição após submissão. O Django admin, porém, permitia alterar metadados e substituir o PDF de trabalhos submetidos ou aprovados, mantendo a aprovação. Agora o admin permite consultar esses trabalhos, mas recusa a gravação, inclusive por POST direto. O rascunho continua editável.

Excluir um curso usado por uma monografia levantava `ProtectedError` sem tratamento. O banco já protegia o vínculo; faltava uma resposta compreensível. Agora a aplicação preserva o curso e a monografia, apresenta uma mensagem e responde com HTTP 409 (conflito). Curso sem vínculos continua podendo ser excluído.

## Como ler a mudança

1. Em `monografias/models.py`, `pode_editar` expressa a regra: o status precisa ser `rascunho`. É uma propriedade Python, não uma coluna de banco, portanto não exige migração.
2. Em `monografias/forms.py`, `clean()` consulta o status persistido e rejeita edição de trabalho que já saiu de rascunho. Consultar o banco evita confiar apenas em uma instância antiga recebida pelo formulário.
3. Em `monografias/admin.py`, `has_change_permission()` usa a mesma regra. O GET mantém a consulta; um POST de alteração em trabalho submetido/aprovado recebe 403. Status, hash e dados da aprovação são somente leitura. O orientador também fica visível no admin.
4. Ainda no admin, `changeform_view()` mantém uma transação com bloqueio do registro no PostgreSQL até o fim da gravação. Isso coordena a edição administrativa com a submissão, que já usa bloqueio na mesma monografia.
5. Em `monografias/views.py`, a exclusão de curso captura especificamente `ProtectedError`, sem esconder outras falhas. O template `excluir_curso.html` apresenta o erro com `role="alert"`.

Essas proteções cobrem os formulários e caminhos de edição atuais. Não são uma proibição automática de qualquer `Model.save()`, `QuerySet.update()` ou SQL direto. A futura API deverá aplicar a mesma regra dentro da transação; operações administrativas por shell também exigem cuidado. Este passo não define ainda reabertura de submissões ou versionamento de PDFs.

## Testes

Os oito testes novos foram executados antes da correção: três falharam e um levantou erro, reproduzindo os problemas. Depois da correção, os 29 testes da suíte passaram:

```bash
python manage.py test --settings=config.settings_test
python manage.py makemigrations --check --dry-run --settings=config.settings_test
```

Cobertura adicionada: consulta/recusa de edição no admin, tentativa de substituição de PDF aprovado com preservação de arquivo/hash/aprovação, edição normal de rascunho, formulário com instância desatualizada, exclusão de curso vinculado, exclusão de curso livre, GET sem exclusão e usuário sem permissão.

Os testes usam SQLite em memória e arquivos temporários. O bloqueio concorrente do PostgreSQL não foi validado com requisições simultâneas nesta etapa. Nenhuma migração ou alteração foi aplicada ao banco real.

## Acompanhar manualmente

1. No admin, abra uma monografia em rascunho: os dados acadêmicos continuam editáveis.
2. Submeta o trabalho pela conta do aluno e reabra-o no admin: os dados ficam somente para consulta.
3. Como orientador, aprove a submissão e confirme que o admin continua sem permitir substituir o PDF.
4. Tente excluir um curso usado por uma monografia pela página de cursos: deve aparecer a mensagem explicando o vínculo.

Próxima etapa: completar dados acadêmicos e permissões do coordenador antes de concluir o agendamento de bancas. O início de bancas já existente em `origin/feat/preparacao-de-banca` deve ser reaproveitado.
