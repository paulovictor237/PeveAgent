"""Browser automation helpers using Playwright (sync API)."""
from typing import Any


def scan_fields(page) -> list[dict]:
    """Scan all input/select/textarea elements on the page."""
    els = page.locator("input:not([type=hidden]), select, textarea")
    results = []

    for idx in range(els.count()):
        try:
            field = els.nth(idx).evaluate("""
                (node, i) => {
                    const input = node;
                    const id = input.id || "";

                    let label = "";
                    if (id) {
                        const lbl = document.querySelector(`label[for="${CSS.escape(id)}"]`);
                        if (lbl) label = lbl.textContent?.trim() || "";
                    }
                    if (!label) {
                        const parent = input.closest(
                            "label, [class*='field'], [class*='form-group'], [class*='input-wrapper'], [class*='form-field']"
                        );
                        if (parent) {
                            const clone = parent.cloneNode(true);
                            clone.querySelectorAll("input, select, textarea").forEach(e => e.remove());
                            label = clone.textContent?.replace(/\\s+/g, " ").trim() || "";
                        }
                    }
                    if (!label) {
                        const prev = input.previousElementSibling;
                        if (prev && ["LABEL","SPAN","P","DIV"].includes(prev.tagName)) {
                            label = prev.textContent?.trim() || "";
                        }
                    }

                    const options = [];
                    if (input.tagName === "SELECT") {
                        Array.from(input.options).forEach(o => {
                            if (o.value) options.push(o.text.trim());
                        });
                    }

                    input.setAttribute("data-sj-idx", String(i));

                    return {
                        tag: input.tagName.toLowerCase(),
                        type: input.type || "",
                        name: input.name || "",
                        id: id,
                        label: label,
                        placeholder: input.placeholder || "",
                        ariaLabel: input.getAttribute("aria-label") || "",
                        required: input.required || input.getAttribute("aria-required") === "true",
                        options: options,
                    };
                }
            """, idx)
            results.append(field)
        except Exception:
            pass

    return results


def click_option(page, value: str) -> bool:
    """Click a dropdown option by text."""
    selectors = [
        f'[role="option"]:has-text("{value}")',
        f'li[class*="option"]:has-text("{value}")',
        f'li[class*="item"]:has-text("{value}")',
        f'[data-value="{value}"]',
        f'span[class*="label"]:has-text("{value}")',
    ]
    for sel in selectors:
        try:
            page.locator(sel).first.click(timeout=1000)
            return True
        except Exception:
            pass
    return False


def execute_action(page, action: dict) -> bool:
    """Execute a fill/select/check/upload action. Returns True on success."""
    try:
        selector = action["selector"]
        el = page.locator(selector).first()
        el.wait_for(state="attached", timeout=2000)

        kind = action["kind"]
        if kind == "fill":
            try:
                el.fill(action["value"], timeout=2000)
            except Exception:
                el.click(timeout=1500)
                page.wait_for_timeout(400)
                click_option(page, action["value"])
            return True

        elif kind == "select":
            try:
                el.select_option(label=action["label"], timeout=2000)
            except Exception:
                el.click(timeout=1500)
                page.wait_for_timeout(400)
                click_option(page, action["label"])
            return True

        elif kind == "check":
            el.check(force=True, timeout=2000)
            return True

        elif kind == "upload":
            el.set_input_files(action["path"], timeout=5000)
            return True

    except Exception:
        pass
    return False


def capture_snapshot(page) -> dict[str, str]:
    """Capture current values of all tracked fields by name/id."""
    snapshot = {}
    try:
        els = page.locator("[data-sj-idx]").all()
        for el in els:
            try:
                data = el.evaluate("""
                    (node) => {
                        const input = node;
                        const key = input.name || input.id;
                        if (!key) return null;
                        let value = "";
                        if (input.type === "checkbox" || input.type === "radio") {
                            value = input.checked ? "1" : "0";
                        } else if (input.type !== "file") {
                            value = input.value || "";
                        }
                        return { key, value };
                    }
                """)
                if data:
                    snapshot[data["key"]] = data["value"]
            except Exception:
                pass
    except Exception:
        pass
    return snapshot