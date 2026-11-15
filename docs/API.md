# Contrato da API para o frontend

Base acadêmica: `/api/`. Respostas JSON, exceto downloads PDF. Listas CRUD paginadas usam `count`, `next`, `previous` e `results`, com 25 registros por página. Use `?page=2` para avançar. A consulta pública independente usa `count`, `page`, `page_size` e `results`.

## Sessão e CSRF

1. `GET /api/conta/` retorna `csrfToken`, `autenticado` e, se houver sessão, usuário/grupos.
2. `POST /api/conta/` com `{"login":"usuario","password":"senha"}`, cookie de sessão e cabeçalho `X-CSRFToken`.
3. Após login, use o novo `csrfToken` da resposta nas operações de escrita e envie cookies (`credentials: "include"` no fetch).
4. `DELETE /api/conta/` encerra a sessão; também exige CSRF.

A implantação inicial deve servir frontend e API na mesma origem. Não existe CORS liberado para origens arbitrárias. Não há JWT neste contrato.

## Recursos

| Caminho | Métodos | Uso |
| --- | --- | --- |
| `cursos/` e `cursos/{id}/` | GET, POST, PATCH, DELETE | Leitura pública; escrita administrativa autorizada |
| `orientadores/` | GET | Lista pública reduzida de professores ativos, sem dados de login/e-mail |
| `publicadas/` e `publicadas/{id}/` | GET | Somente monografias publicadas |
| `publicadas/{id}/pdf/` | GET | PDF público original ou corrigido validado |
| `monografias/` e `monografias/{id}/` | GET, POST, PATCH, DELETE | Trabalhos visíveis ao usuário, com restrições por vínculo/estado |
| `monografias/{id}/submeter/` | POST | Autor envia rascunho ao orientador |
| `monografias/{id}/aprovar/` | POST | Orientador vinculado aprova submissão |
| `monografias/{id}/pdf/` | GET | Download autorizado e conferência de integridade |
| `bancas/` e `bancas/{id}/` | GET, POST, PATCH, DELETE | Preparação, edição antes de avaliações e exclusão de proposta |
| `bancas/{id}/agendar/` | POST | Exige membros confirmados e ausência de conflitos |
| `bancas/{id}/cancelar/` | POST | Cancela banca permitida e revoga seus convites |
| `membros/` e `membros/{id}/` | GET, POST, DELETE | Convites internos/externos; alterações por remoção e novo convite em preparação |
| `membros/{id}/confirmar/` | POST | Confirmação pelo professor convidado |
| `membros/{id}/renovar/` | POST | Gestor renova convite externo e recebe token novo |
| `membros/{id}/revogar/` | POST | Gestor revoga acesso |
| `avaliacoes/` e `avaliacoes/{id}/` | GET, POST, PATCH, DELETE | Avaliação do próprio membro; fechamento por worker após todas |
| `documentos/` e `documentos/{id}/` | GET, POST, DELETE | Upload privado de documentos; não permite substituir validados |
| `documentos/{id}/validar/` | POST | Gestor registra conferência humana do documento |
| `documentos/{id}/pdf/` | GET | Download privado autorizado |
| `usuarios/`, `alunos/`, `professores/` e detalhes | GET, POST, PATCH, DELETE | Cadastros administrativos na rede autorizada |
| `relatorios/` | GET | Estatísticas limitadas aos trabalhos visíveis ao usuário |
| `auditoria/` | GET | Histórico administrativo, somente leitura |
| `eventos/` | GET | Operação da outbox, restrita à administração |
| `eventos/{id}/repetir/` | POST | Libera nova tentativa de evento pendente |
| `health/` | GET | Verificação básica de banco/cache |
| `schema/`, `docs/` | GET | OpenAPI e documentação navegável |

Os campos detalhados e tipos estão no OpenAPI. PUT não é exposto; atualizações parciais usam PATCH.

## Exemplos

Criar monografia: `POST /api/monografias/` com `multipart/form-data`, campos `titulo`, `resumo`, `palavras_chave`, `curso`, `orientador` opcional e `arquivo` (PDF). O cliente não define `autor`, `status`, `hash_sha256` ou datas. Ao usar `FormData`, não fixe manualmente o Content-Type.

Preparar banca:

```json
{"monografia":12,"data_hora":"2026-12-10T14:00:00-03:00","fim":"2026-12-10T15:00:00-03:00","local":"Sala 2","link":""}
```

Membro interno: `{"banca":3,"usuario":7}`. Membro externo: `{"banca":3,"nome":"Nome","email":"pessoa@example.org"}`. O retorno inclui `membro` e `token_temporario` para externos. Compartilhe privadamente o token; não o coloque em query strings ou logs.

Avaliação: `{"membro":5,"nota":"8.50","parecer":"Texto do parecer","recomendacao":"aprovado"}`. Recomendações: `aprovado`, `ressalvas` e `reprovado`. Só aceita após o fim da defesa e antes do fechamento.

Documento: upload multipart com `monografia`, `tipo` e `arquivo`. Tipos: `ata`, `termo`, `ortografia`, `corrigida`.

## Membro externo sem conta

Use `X-Banca-Token` como cabeçalho em cada requisição:

- `GET /api/externo/`: dados limitados ao convite.
- `POST /api/externo/` com `{"acao":"confirmar"}`: confirma disponibilidade.
- `GET /api/externo/pdf/`: PDF autorizado após agendamento.
- `POST /api/externo/` com nota, parecer e recomendação: registra/edita a própria avaliação antes do fechamento. O membro é derivado do token; enviar outro ID não amplia acesso.

O token não fornece uma sessão permanente e expira ou pode ser revogado. Não use esse cabeçalho nos endpoints de administração.

## Busca e relatórios

`GET /api/publicadas/?busca=redes&curso=1&ano_defesa=2026` no acadêmico. Filtros adicionais: `autor` e `orientador` por ID, `palavras_chave` e `page`.

No serviço independente: `GET http://127.0.0.1:8001/api/publicadas/?busca=redes&curso=1&ano_defesa=2026`. Nesse serviço, `autor` e `orientador` são filtros textuais. Somente dados projetados de publicações estão disponíveis; documentos privados e IDs de autenticação não são compartilhados.

`/api/relatorios/` retorna contagens por curso/orientador/ano, taxa de aprovação entre resultados fechados e tempo médio em dias entre submissão e defesa. Sem dados suficientes, taxas e duração são `null`.

## Erros

200 consulta/ação, 201 criação, 204 exclusão, 400 validação, 403 sessão/permissão/CSRF, 404 inexistente ou fora do escopo, 405 método não exposto, 409 vínculo/conflito de persistência, 429 limitação de taxa. Alguns erros de negócio de agendamento são validação 400. Nunca trate uma resposta de erro como sucesso apenas porque o corpo é JSON.

Campo inválido normalmente retorna listas por campo; falha geral retorna `detail`. Mensagens podem ser traduzidas; o frontend deve usar status e nomes de campos, não comparar frases exatas. A API não revela caminhos do diretório de arquivos privados.
