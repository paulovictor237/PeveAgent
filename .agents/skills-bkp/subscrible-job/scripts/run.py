#!/usr/bin/env python3
"""subscrible-job — simplified job application form filler."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "lib"))

from playwright.sync_api import sync_playwright

from browser import scan_fields, execute_action, capture_snapshot
from mapping import map_field
from profile import load_profile, update_extra_fields


def find_pdf(skill_dir: Path) -> str:
    candidates = ["Profile-pt.pdf", "Profile-en.pdf", "Profile.pdf"]
    for name in candidates:
        path = skill_dir / "assets" / name
        if path.exists():
            return str(path)
    raise FileNotFoundError(f"Nenhum PDF encontrado em {skill_dir / 'assets'}")


def label_of(field: dict) -> str:
    return field.get("label") or field.get("ariaLabel") or field.get("placeholder") or field.get("name") or field.get("id") or "(sem label)"


def main():
    if len(sys.argv) < 2:
        print("Uso: python run.py <url>")
        sys.exit(1)

    url = sys.argv[1]
    skill_dir = Path(os.environ.get("SKILL_DIR", str(Path(__file__).parent.parent)))
    profile_path = skill_dir / "assets" / "profile.json"
    pdf_path = find_pdf(skill_dir)

    profile = load_profile(str(profile_path))
    print(f"Profile carregado: {profile.get('name', 'N/A')}")
    print(f"Abrindo {url}\n")

    manual_edits = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")

        fields = scan_fields(page)
        baseline = capture_snapshot(page)

        filled = []
        unmapped = []
        cover_letters = []
        failed = []

        for field in fields:
            result = map_field(field, profile, pdf_path)
            label = label_of(field)

            if result["kind"] == "skip":
                continue
            elif result["kind"] == "cover_letter":
                cover_letters.append(label)
                continue
            elif result["kind"] == "unmapped":
                unmapped.append({"label": label, "reason": result.get("reason", "")})
                continue

            ok = execute_action(page, result["action"])
            if ok:
                filled.append({"label": label, "desc": result.get("description", "")})
            else:
                failed.append({"label": label, "desc": result.get("description", "")})

            page.wait_for_timeout(150)

        # Report before close
        print(f"{'━' * 54}")
        print(f"→ {len(fields)} campos detectados\n")

        if filled:
            print(f"✓ Preenchido automaticamente ({len(filled)}):")
            for f in filled:
                print(f"  • {f['label']} → {f['desc']}")

        if cover_letters:
            print(f"\n⚠ Cover letter — preencha manualmente:")
            for c in cover_letters:
                print(f"  • {c}")

        if unmapped:
            print(f"\n○ Não mapeados ({len(unmapped)}):")
            for u in unmapped:
                print(f"  • {u['label']} ({u['reason']})")

        if failed:
            print(f"\n✗ Falhas de preenchimento ({len(failed)}):")
            for f in failed:
                print(f"  • {f['label']} → {f['desc']}")

        print(f"\n{'━' * 54}")
        print("Preencha o restante no browser.")
        print("Quando terminar, feche o browser para salvar e gerar relatório.\n")

        # Capture snapshot before waiting for close
        final_snapshot = capture_snapshot(page)

        # Wait for browser to close
        page.wait_for_event("close", timeout=0)

    # Diff snapshots to find manual edits
    for field in fields:
        key = field.get("name") or field.get("id")
        ftype = field.get("type", "")
        ftag = field.get("tag", "")

        if not key or key == "g-recaptcha-response" or ftype == "hidden":
            continue
        if ftag == "input" and ftype == "file":
            continue

        before = baseline.get(key, "")
        after = final_snapshot.get(key, "")
        if before != after and after:
            manual_edits[label_of(field)] = after

    print(f"→ {len(manual_edits)} edições manuais capturadas")
    for label, value in manual_edits.items():
        preview = value[:60] + ("..." if len(value) > 60 else "")
        print(f"  • {label} = {preview}")

    added = updated = 0
    if manual_edits:
        added, updated = update_extra_fields(str(profile_path), manual_edits)
        print(f"\n✓ profile.json atualizado — {added} novos, {updated} atualizados")
    else:
        print("\n○ Nenhuma edição manual para salvar")

    print("\nFeito.")


if __name__ == "__main__":
    main()