#!/usr/bin/env python3
"""
tiny_task.py — pipeline autônomo para tarefas "tiny" do Jira.

Etapas (na ordem):
  1. Validar argumentos e estado do git
  2. git switch <base> && git pull --ff-only
  3. criar worktree + branch <TICKET>
  4. exportar GITHUB_TOKEN=$PX_GH_TOKEN
  5. npm ci (fallback npm i)
  6. <pausa para o agente desenvolver>
  7. git add -A && commit (mensagem via --commit-msg ou --commit-msg-file)
  8. git push -u origin <TICKET>
  9. imprime JSON com a worktree e a branch — PR fica para a skill
     pr-description (o script NÃO abre PR para permitir descrição rica)

Uso:
  python tiny_task.py \\
    --ticket APX-1234 \\
    --summary "fix label color in orders table" \\
    --base main \\
    --commit-msg "fix(orders): correct label color in table header"

Saídas:
  stdout: logs coloridos + JSON final com { worktree, branch, ticket }
  exit 0 em sucesso, 1 em qualquer falha
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# --------------------------- visual helpers ---------------------------


class C:
    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    RESET = "\033[0m"


def info(msg: str) -> None:
    print(f"{C.CYAN}ℹ{C.RESET}  {msg}", flush=True)


def step(msg: str) -> None:
    print(f"\n{C.BOLD}{C.MAGENTA}▶ {msg}{C.RESET}", flush=True)


def ok(msg: str) -> None:
    print(f"{C.GREEN}✓{C.RESET}  {msg}", flush=True)


def warn(msg: str) -> None:
    print(f"{C.YELLOW}⚠{C.RESET}  {msg}", flush=True)


def die(msg: str, code: int = 1) -> None:
    print(f"{C.RED}✗{C.RESET}  {msg}", flush=True)
    sys.exit(code)


# --------------------------- subprocess helpers ---------------------------


@dataclass
class CmdResult:
    returncode: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def run(
    cmd: list[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
    check: bool = True,
    capture: bool = True,
    input_text: Optional[str] = None,
) -> CmdResult:
    """Run a command, print a short log, return CmdResult. Die on failure if check=True."""
    printable = " ".join(_redact(cmd))
    info(f"$ {printable}" + (f"   {C.DIM}(cwd={cwd}){C.RESET}" if cwd else ""))
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        env={**os.environ, **(env or {})},
        input=input_text,
        text=True,
        capture_output=capture,
    )
    result = CmdResult(proc.returncode, proc.stdout, proc.stderr)
    if check and not result.ok:
        if proc.stdout:
            print(proc.stdout)
        if proc.stderr:
            print(proc.stderr, file=sys.stderr)
        die(f"comando falhou (exit {proc.returncode}): {printable}")
    return result


def _redact(cmd: list[str]) -> list[str]:
    out = []
    for c in cmd:
        if any(k in c for k in ("TOKEN", "SECRET", "KEY", "PASSWORD")):
            out.append("***")
        else:
            out.append(c)
    return out


# --------------------------- validation ---------------------------

TICKET_RE = re.compile(r"^[A-Z][A-Z0-9]+-\d+$")
BRANCH_SAFE_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def validate_ticket(ticket: str) -> str:
    ticket = ticket.strip().upper()
    if not TICKET_RE.match(ticket):
        die(f"ticket inválido: {ticket!r} (esperado PROJ-1234)")
    return ticket


def validate_branch_name(name: str) -> str:
    if not BRANCH_SAFE_RE.match(name) or name.startswith("-") or name.endswith("/"):
        die(f"nome de branch inseguro: {name!r}")
    return name


def git_repo_root(cwd: Path) -> Path:
    res = run(["git", "rev-parse", "--show-toplevel"], cwd=cwd, check=False)
    if not res.ok:
        die("não estamos dentro de um repositório git")
    return Path(res.stdout.strip())


def git_current_branch(cwd: Path) -> str:
    res = run(["git", "branch", "--show-current"], cwd=cwd, check=False)
    if not res.ok or not res.stdout.strip():
        die("não foi possível detectar a branch atual (HEAD detached?)")
    return res.stdout.strip()


def is_interactive_terminal() -> bool:
    """Detecta se o stdin é um TTY interativo. Em agentes (subprocess pipes),
    retorna False. Em terminais humanos, retorna True."""
    try:
        return os.isatty(sys.stdin.fileno())
    except (OSError, ValueError):
        return False


def has_worktree_conflict(cwd: Path, worktree_path: Path) -> bool:
    res = run(["git", "worktree", "list", "--porcelain"], cwd=cwd, check=False)
    if not res.ok:
        return False
    for line in res.stdout.splitlines():
        if (
            line.startswith("worktree ")
            and Path(line.split(" ", 1)[1]).resolve() == worktree_path.resolve()
        ):
            return True
    return False


def worktree_branch(cwd: Path, worktree_path: Path) -> Optional[str]:
    """Devolve a branch associada a uma worktree existente, ou None."""
    res = run(["git", "worktree", "list", "--porcelain"], cwd=cwd, check=False)
    if not res.ok:
        return None
    target = str(worktree_path.resolve())
    branch = None
    for line in res.stdout.splitlines():
        if line.startswith("worktree ") and Path(
            line.split(" ", 1)[1]
        ).resolve() == Path(target):
            continue
        if line.startswith("worktree "):
            branch = None
            continue
        if line.startswith("branch "):
            ref = line.split(" ", 1)[1]
            if ref.startswith("refs/heads/"):
                branch = ref[len("refs/heads/") :]
    return branch


def branch_exists(cwd: Path, branch: str) -> bool:
    res = run(
        ["git", "rev-parse", "--verify", f"refs/heads/{branch}"], cwd=cwd, check=False
    )
    return res.ok


def detect_github_token() -> Optional[str]:
    for var in ("PX_GH_TOKEN", "GITHUB_TOKEN", "GH_TOKEN"):
        val = os.environ.get(var)
        if val:
            return val
    return None


# --------------------------- pipeline steps ---------------------------


def step_switch_and_pull(repo: Path, base: str) -> None:
    step(f"1. Sincronizando {base}")
    current = git_current_branch(repo)
    if current != base:
        run(["git", "switch", base], cwd=repo)
    run(["git", "fetch", "origin", base, "--prune"], cwd=repo)
    res = run(["git", "pull", "--ff-only"], cwd=repo, check=False)
    if not res.ok:
        warn(
            "pull --ff-only falhou — provavelmente não há upstream ainda. Continuando."
        )


def step_create_worktree(repo: Path, base: str, ticket: str, summary_slug: str) -> Path:
    step("2. Criando worktree e branch")

    repo_name = repo.name
    suffix = f"-{summary_slug}" if summary_slug else ""
    wt_dir_name = f"{repo_name}-{ticket.lower()}{suffix}"
    worktree_path = (repo.parent / wt_dir_name).resolve()

    if has_worktree_conflict(repo, worktree_path):
        existing_branch = worktree_branch(repo, worktree_path)
        if existing_branch == ticket.lower():
            ok(f"worktree já existe em {worktree_path} — reutilizando")
            return worktree_path
        die(
            f"já existe uma worktree em {worktree_path} mas em outra branch "
            f"({existing_branch}). Remova com `git worktree remove {worktree_path}`."
        )

    if worktree_path.exists():
        die(f"o caminho {worktree_path} já existe e não é uma worktree")

    branch = validate_branch_name(ticket.lower())
    if branch_exists(repo, branch):
        die(
            f"branch local {branch} já existe. Para retomar: "
            f"`git worktree add {worktree_path} {branch}` (após remover a worktree anterior, se houver)."
        )

    run(
        ["git", "worktree", "add", str(worktree_path), "-b", branch, f"origin/{base}"],
        cwd=repo,
    )
    ok(f"worktree criada: {worktree_path}")
    ok(f"branch: {branch}")
    return worktree_path


def step_export_github_token(worktree: Path) -> None:
    step("3. Exportando token do GitHub")
    token = detect_github_token()
    if not token:
        warn("nenhum token encontrado (PX_GH_TOKEN, GITHUB_TOKEN, GH_TOKEN).")
        warn("o push provavelmente falhará.")
        return
    os.environ["GITHUB_TOKEN"] = token
    os.environ["GH_TOKEN"] = token
    ok(
        f"token exportado (origem: "
        + (
            "PX_GH_TOKEN"
            if os.environ.get("PX_GH_TOKEN")
            else "GITHUB_TOKEN"
            if os.environ.get("GITHUB_TOKEN")
            else "GH_TOKEN"
        )
        + ")"
    )


def has_npm_lock(worktree: Path) -> bool:
    return (worktree / "package-lock.json").exists()


def node_modules_ready(worktree: Path) -> bool:
    return (worktree / "node_modules" / ".package-lock.json").exists() or (
        worktree / "node_modules"
    ).exists()


def step_install_deps(worktree: Path) -> None:
    step("4. Instalando dependências")
    if not (worktree / "package.json").exists():
        warn("sem package.json — pulando npm install")
        return
    npm = shutil.which("npm")
    if not npm:
        die("npm não encontrado no PATH")
    if node_modules_ready(worktree):
        ok("node_modules já presente — pulando install (reuso)")
        return
    if has_npm_lock(worktree):
        run([npm, "ci"], cwd=worktree)
    else:
        run([npm, "i"], cwd=worktree)
    ok("dependências instaladas")


def step_wait_for_dev(worktree: Path) -> None:
    """Pausa explícita para o agente humano/IA codar. Não escreve código por conta própria."""
    step("5. Pausa para desenvolvimento")
    if not is_interactive_terminal():
        warn(
            "terminal não-interativo detectado (agente). "
            "`input()` não vai bloquear. Encerrando aqui — use o worktree, "
            "faça as mudanças e rode o commit/push manualmente, ou reexecute "
            "este script com --no-wait após editar."
        )
        die(
            "worktree pronta para edição. Para retomar sem worktree nova, "
            f"rode os comandos: git -C {worktree} add -A && "
            f"git -C {worktree} commit -m '...' && "
            f"git -C {worktree} push -u origin <branch>",
            code=2,
        )
    print(
        f"{C.DIM}    O script NÃO escreve código. Desenvolva a mudança em {worktree}\n"
        f"    Quando terminar (e quiser commitar), pressione ENTER para continuar.{C.RESET}"
    )
    try:
        input(f"{C.CYAN}?{C.RESET}  pronto para commitar? [ENTER] ")
    except EOFError:
        die("input() retornou EOFError — abortando antes de commitar vazio", code=2)


def step_commit(
    worktree: Path, message: Optional[str], message_file: Optional[Path]
) -> None:
    step("6. Commit")
    status = run(["git", "status", "--porcelain"], cwd=worktree, check=False)
    if status.ok and not status.stdout.strip():
        die(
            "nada para commitar — working tree limpo. Edite arquivos no "
            f"worktree ({worktree}) e reexecute o pipeline."
        )

    run(["git", "add", "-A"], cwd=worktree)

    if not message and not message_file:
        die("defina --commit-msg ou --commit-msg-file")
    if message_file:
        run(["git", "commit", "-F", str(message_file)], cwd=worktree)
    else:
        run(["git", "commit", "-m", message], cwd=worktree)

    head = run(["git", "log", "-1", "--oneline"], cwd=worktree, check=False)
    if head.ok:
        ok(f"commit criado: {head.stdout.strip()}")


def step_push(worktree: Path, branch: str) -> None:
    step("7. Push")
    run(["git", "push", "-u", "origin", branch], cwd=worktree)
    ok(f"branch {branch} publicada")


# --------------------------- main ---------------------------


def slugify(text: str) -> str:
    s = text.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s[:40]


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="tiny_task.py",
        description="Pipeline autônomo para tasks 'tiny' do Jira.",
    )
    parser.add_argument("--ticket", required=True, help="chave da issue, ex: APX-1234")
    parser.add_argument(
        "--summary", default="", help="resumo curto em kebab-case (opcional)"
    )
    parser.add_argument("--base", default="main", help="branch base (default: main)")
    parser.add_argument(
        "--commit-msg", help="mensagem de commit (Conventional Commits)"
    )
    parser.add_argument(
        "--commit-msg-file", type=Path, help="arquivo com mensagem de commit"
    )
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="não pausar para desenvolvimento (modo CI/script)",
    )
    args = parser.parse_args()

    ticket = validate_ticket(args.ticket)
    summary_slug = slugify(args.summary) if args.summary else ""
    base = args.base.strip()
    if not base:
        die("--base inválido")

    cwd = Path.cwd()
    repo = git_repo_root(cwd)
    ok(f"repo: {repo}")

    step_switch_and_pull(repo, base)
    worktree = step_create_worktree(repo, base, ticket, summary_slug)
    step_export_github_token(worktree)
    step_install_deps(worktree)
    if not args.no_wait:
        step_wait_for_dev(worktree)
    else:
        warn("--no-wait definido: pulando a pausa de desenvolvimento")
    step_commit(worktree, args.commit_msg, args.commit_msg_file)
    step_push(worktree, ticket.lower())

    result = {
        "ok": True,
        "ticket": ticket,
        "branch": ticket.lower(),
        "worktree": str(worktree),
        "next": "use a skill pr-description para abrir o PR",
    }
    print()
    print(f"{C.BOLD}{C.GREEN}=== tiny_task: DONE ==={C.RESET}")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        die("interrompido pelo usuário", code=130)
