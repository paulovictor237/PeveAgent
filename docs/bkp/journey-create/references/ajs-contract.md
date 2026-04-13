# AJS Script Contract — Referência Completa

Este documento define o contrato que todos os scripts do Atomic Journey System (AJS) devem seguir.
O executor `journey-use` depende deste contrato para funcionar corretamente.

---

## As 5 Regras do Contrato

### Regra 1 — Single Responsibility
Um script faz exatamente uma coisa. Não combine "criar usuário" e "enviar email" no mesmo script.
Se você se pegar escrevendo "e também...", está na hora de dividir.

### Regra 2 — Input via state.json
O script recebe o caminho para o arquivo de estado como primeiro argumento (`argv[1]`).
Todos os inputs devem vir desse arquivo. Nunca hardcode IDs, credenciais, ou valores de negócio.

### Regra 3 — Output via state.json
Ao terminar com sucesso, o script escreve o(s) novo(s) valor(es) de volta no mesmo arquivo de estado.
O arquivo deve preservar todas as chaves existentes — apenas adicione/atualize as novas.

### Regra 4 — Exit Codes
- `exit(0)` → sucesso (estado foi atualizado)
- `exit(1)` → erro de negócio (mensagem clara no stdout, estado não alterado)

Nunca use exit codes além de 0 e 1. O executor não interpreta outros valores.

### Regra 5 — Agnosticismo
O script não sabe de qual jornada faz parte. Ele apenas processa os dados que encontra no estado.
Isso permite que o mesmo script seja reutilizado em múltiplas jornadas.

---

## Templates por Linguagem

### PHP

```php
<?php
// <nome-do-script>.php — <descrição de uma linha>
// Input:  state -> <chave1>, <chave2>
// Output: state -> <chave_saida>

$statePath = $argv[1] ?? 'state.json';

if (!file_exists($statePath)) {
    echo "Erro: arquivo de estado não encontrado em {$statePath}";
    exit(1);
}

$state = json_decode(file_get_contents($statePath), true);

// Validar inputs obrigatórios
$campo1 = $state['chave1'] ?? null;
$campo2 = $state['chave2'] ?? null;

if (!$campo1 || !$campo2) {
    echo "Erro: chave1 e chave2 são obrigatórios no estado.";
    exit(1);
}

// --- Lógica de negócio ---
// $resultado = MinhaModel::create([...]);

// Escrever output no estado
$state['chave_saida'] = $resultado->id;
file_put_contents($statePath, json_encode($state, JSON_PRETTY_PRINT));

echo "Operação concluída. chave_saida={$resultado->id}";
exit(0);
```

### Python

```python
#!/usr/bin/env python3
# <nome-do-script>.py — <descrição de uma linha>
# Input:  state -> chave1, chave2
# Output: state -> chave_saida

import sys
import json

def main():
    state_path = sys.argv[1] if len(sys.argv) > 1 else 'state.json'

    try:
        with open(state_path, 'r') as f:
            state = json.load(f)
    except FileNotFoundError:
        print(f"Erro: arquivo de estado não encontrado em {state_path}")
        sys.exit(1)

    campo1 = state.get('chave1')
    campo2 = state.get('chave2')

    if not campo1 or not campo2:
        print("Erro: chave1 e chave2 são obrigatórios no estado.")
        sys.exit(1)

    # --- Lógica de negócio ---
    # resultado = minha_funcao(campo1, campo2)

    state['chave_saida'] = resultado
    with open(state_path, 'w') as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

    print(f"Operação concluída. chave_saida={resultado}")
    sys.exit(0)

if __name__ == '__main__':
    main()
```

### JavaScript (Node.js)

```javascript
// <nome-do-script>.js — <descrição de uma linha>
// Input:  state -> chave1, chave2
// Output: state -> chave_saida

const fs = require('fs');

const statePath = process.argv[2] || 'state.json';

if (!fs.existsSync(statePath)) {
    console.log(`Erro: arquivo de estado não encontrado em ${statePath}`);
    process.exit(1);
}

const state = JSON.parse(fs.readFileSync(statePath, 'utf8'));

const campo1 = state.chave1 ?? null;
const campo2 = state.chave2 ?? null;

if (!campo1 || !campo2) {
    console.log('Erro: chave1 e chave2 são obrigatórios no estado.');
    process.exit(1);
}

// --- Lógica de negócio ---
// const resultado = await minhaFuncao(campo1, campo2);

state.chave_saida = resultado;
fs.writeFileSync(statePath, JSON.stringify(state, null, 2));

console.log(`Operação concluída. chave_saida=${resultado}`);
process.exit(0);
```

---

## Erros Comuns a Evitar

| Erro | Por quê é problema | Solução |
|------|--------------------|---------|
| Hardcodar IDs ou URLs | Quebra portabilidade | Ler do estado ou de variáveis de ambiente |
| Sobrescrever o estado inteiro | Apaga dados de outros scripts | Ler, modificar, reescrever (`merge`) |
| exit codes > 1 | journey-use não interpreta | Usar apenas 0 ou 1 |
| Lógica de duas ações no mesmo script | Dificulta reuso | Dividir em dois scripts |
| Mensagem de erro vaga ("Erro!") | Dificulta debug | Mensagem específica com o valor inválido |

---

## Convenções de Nomenclatura

- Arquivos: `verbo_substantivo.php` → `get_driver.php`, `submit_rating.php`, `cancel_trip.php`
- Chaves de estado: `snake_case` em inglês → `driver_id`, `trip_status`, `rating_value`
- Jornadas: `kebab-case` em português → `avaliar-motorista.md`, `cancelar-corrida.md`
