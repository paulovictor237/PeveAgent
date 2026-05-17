---
name: db-queries
description: >
  Formats SQL queries for data verification and modification with an ultra-minimalist and standardized structure.
  Use ALWAYS when the user requests an SQL query to: simulate a change, verify data before modifying,
  write UPDATE, DELETE, or any SQL that modifies data. Also trigger when the user says
  "prepare the SQL", "generate the modification SQL", "create an UPDATE for", "do a DELETE where",
  "I want to check before changing", "give me the SQL to change", "simulate the change", or any variation
  of requesting SQL that reads or modifies data in the database. When in doubt, use this skill — the cost of using it
  when unnecessary is minimal, and the cost of not using it is the user receiving an incorrect format.
---

## Golden Rule

Deliver **a single SQL block** with the entire response inside. No text outside the block, no multiple separate blocks.

---

## Block Structure

Each operation has a verification SELECT followed by the UPDATE/DELETE. When there are multiple operations, use a visually highlighted section title with `-- ======`.

```sql
-- ====== Operation description ======

SELECT id, <column_1>, <column_2>
FROM <table>
WHERE <same condition as UPDATE/DELETE>;

-- <column>: 'value1', 'value2', 'value3'
UPDATE <table>
SET <column> = '<new_value>'
WHERE <condition>;
```

**SELECT:**
- Always include `id` as the first column.
- List only the columns that will be changed — do not use `SELECT *`.
- The `WHERE` must be identical to that of the UPDATE/DELETE.

**UPDATE/DELETE:**
- Before the `UPDATE`, it is mandatory to include `-- <column>: 'value1', 'value2', ...` for each changed column.
- **Infer enums** from the conversation context, open schema files (migrations, models, enums), or TypeScript/PHP typings. Priority: (1) explicit enums in the code, (2) examples mentioned in the conversation, (3) placeholder `'<FILL_IN>'`.
- `DELETE` does not need the values comment.

---

## Mandatory Safety

**NEVER generate `UPDATE` or `DELETE` without a `WHERE` clause.** If the user asks for a change without a condition, refuse and ask them to specify the filter before continuing. This prevents accidental changes to the entire table.

---

## Correct Output Example

Request: "Prepare the SQL to activate driver 463"

```sql
SELECT id, status
FROM drivers
WHERE id = 463;

-- status: 'active', 'inactive', 'blocked', 'pending'
UPDATE drivers
SET status = 'active'
WHERE id = 463;
```

Request with multiple operations: "Simulate failure and then reset"

```sql
-- ====== Simulate failure ======

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

## What NOT to do

- Do not write phrases like "Here are the queries:" or "Remember to check before executing."
- Do not add explanations outside the SQL block.
- Do not use multiple separate code blocks — everything goes inside a single SQL block.
- Do not omit the possible values comment before the UPDATE.
- Do not generate UPDATE or DELETE without WHERE — never, under any circumstances.
