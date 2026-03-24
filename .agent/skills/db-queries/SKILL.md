---
name: db-queries
description: >
  Formata queries SQL de conferência e alteração de dados com estrutura ultra-minimalista e padronizada.
  Use SEMPRE que o usuário pedir uma query SQL para: simular alteração, conferir dados antes de alterar,
  escrever UPDATE, DELETE, ou qualquer SQL que modifica dados. Também acione quando o usuário disser
  "monta o SQL", "gera o SQL de alteração", "cria um UPDATE para", "faz um DELETE onde",
  "quero conferir antes de alterar", "me dá o SQL pra mudar", "simula a alteração", ou qualquer variação
  de solicitar SQL que leia ou altere dados em banco. Na dúvida, use esta skill — o custo de usá-la
  quando não necessário é mínimo, e o custo de não usá-la é o usuário receber um formato incorreto.
---

## Regra de ouro

Entregue **um único bloco SQL** com toda a resposta dentro. Sem texto fora do bloco, sem múltiplos blocos separados.

---

## Estrutura do bloco

Cada operação tem um SELECT de conferência seguido do UPDATE/DELETE. Quando houver múltiplas operações, use um título de seção visualmente destacado com `-- ======`.

```sql
-- ====== Descrição da operação ======

SELECT id, <coluna_1>, <coluna_2>
FROM <tabela>
WHERE <mesma condição do UPDATE/DELETE>;

-- <coluna>: 'valor1', 'valor2', 'valor3'
UPDATE <tabela>
SET <coluna> = '<novo_valor>'
WHERE <condição>;
```

**SELECT:**
- Sempre inclua `id` como primeira coluna.
- Liste apenas as colunas que serão alteradas — não faça `SELECT *`.
- O `WHERE` deve ser idêntico ao do UPDATE/DELETE.

**UPDATE/DELETE:**
- Antes do `UPDATE`, inclua obrigatoriamente `-- <coluna>: 'valor1', 'valor2', ...` para cada coluna alterada.
- **Infira os enums** a partir do contexto da conversa, arquivos de schema abertos (migrations, models, enums), ou tipagens TypeScript/PHP. Prioridade: (1) enums explícitos no código, (2) exemplos mencionados na conversa, (3) placeholder `'<PREENCHER>'`.
- `DELETE` não precisa do comentário de valores.

---

## Segurança obrigatória

**NUNCA gere `UPDATE` ou `DELETE` sem cláusula `WHERE`.** Se o usuário pedir uma alteração sem condição, recuse e peça que ele especifique o filtro antes de continuar. Isso previne alterações acidentais em toda a tabela.

---

## Exemplo de output correto

Pedido: "Monta o SQL pra ativar o driver 463"

```sql
SELECT id, status
FROM drivers
WHERE id = 463;

-- status: 'active', 'inactive', 'blocked', 'pending'
UPDATE drivers
SET status = 'active'
WHERE id = 463;
```

Pedido com múltiplas operações: "Simula falha e depois o reset"

```sql
-- ====== Simula falha ======

SELECT id, status
FROM drivers
WHERE id = 463;

-- status: 'active', 'inactive', 'blocked', 'pending'
UPDATE drivers
SET status = 'blocked'
WHERE id = 463;


-- ====== Reset ======

SELECT id, status
FROM drivers
WHERE id = 463;

-- status: 'active', 'inactive', 'blocked', 'pending'
UPDATE drivers
SET status = 'active'
WHERE id = 463;
```

---

## O que NÃO fazer

- Não escreva frases como "Aqui estão as queries:" ou "Lembre-se de conferir antes de executar."
- Não adicione explicações fora do bloco SQL.
- Não use múltiplos blocos de código separados — tudo vai dentro de um único bloco SQL.
- Não omita o comentário de valores possíveis antes do UPDATE.
- Não gere UPDATE ou DELETE sem WHERE — nunca, sob nenhuma circunstância.
