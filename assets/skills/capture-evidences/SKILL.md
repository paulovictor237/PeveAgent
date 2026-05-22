---
name: capture-evidences
description: Use when the user asks to capture screenshots, take evidences, document visual scenarios, or record the state of a feature for a branch. Triggers on phrases like "take screenshots", "create evidences", "capture scenarios", "evidence this feature", or any request to visually document UI behavior for a PR or ticket.
---

# Capture Evidences

Playwright-based screenshot workflow for documenting UI feature scenarios. One script per branch, 1920×1080, no dev-tool noise.

## When to Use

- User asks for screenshots or evidences for a branch/ticket
- Need to visually document feature flag states, UI modes, or interaction flows
- Capturing before/after states for a PR

## Workflow

1. **Identify scenarios** — ask user to list them (or infer from the branch/ticket)
2. **Write the script** — one `scripts/capture-evidences.py` per feature, from the template below
3. **Pre-flight checks** — confirm dev server is running, get bearer token
4. **Run** — `python scripts/capture-evidences.py`
5. **Verify** — read each screenshot before reporting done

## Known Pitfalls and Fixes

### Auth — inject via localStorage, not HTTP headers

The app reads `localStorage["token"]` and `localStorage["company"]` on boot. HTTP headers alone won't log the user in. Fetch `/me` first to get the real company object, then inject both via `add_init_script`.

```python
context.add_init_script(f"""
    localStorage.setItem('token', {json.dumps(BEARER)});
    localStorage.setItem('company', {json.dumps(json.dumps(company_data))});
""")
```

### Cookie/tour modals block interactions — pre-dismiss via localStorage

Any overlay with `z-50` will intercept pointer events and cause `Locator.click` timeouts. Suppress known modals before the page loads:

```python
localStorage.setItem('track-consent', 'accepted');   # cookie consent
```

Check `src/infra/interfaces/local-storage.ts` for all `LocalStorageKeys` — each maps to a modal or tour.

### Dev tools panel visible in screenshots — CSS injection

`NEXT_PUBLIC_REACTQUERYDEVTOOLS=1` in `.env.local` means TanStack devtools render in development. Hide them after `networkidle`:

```python
HIDE_DEVTOOLS_CSS = """
    .tsqd-parent-container,
    [data-testid="react-query-devtools-panel"],
    [data-testid="query-devtools-open-btn"] { display: none !important; }
"""
page.add_style_tag(content=HIDE_DEVTOOLS_CSS)
```

### localStorage state survives between page loads — set before reload

When a scenario depends on a stored value (e.g. group-by mode), set it after the first `domcontentloaded` then reload so the app boots with the value already present:

```python
page.goto(URL, wait_until="domcontentloaded")
page.evaluate("([k,v]) => localStorage.setItem(k, JSON.stringify(v))", [KEY, value])
page.reload(wait_until="domcontentloaded")
```

### Feature flags come from the API — intercept the route

Never modify the backend. Use `context.route()` to stub the flag response per scenario:

```python
def handle_flag(route, request):
    if "my_flag_name" in request.url:
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps({"enabled": flag_enabled}))
    else:
        route.continue_()

context.route("**/v1/feature-flags/check**", handle_flag)
```

### Clicking collapsible sections — use specific aria selectors

`[aria-expanded]` matches many things (dropdowns, dialogs). Target the exact component:

```python
# Too broad — may match Radix popovers or dropdowns
page.locator("[aria-expanded]").first

# Precise — targets session group toggles specifically
page.locator("[aria-controls^='session-group-content-']").first
```

### networkidle times out on pages with polling — catch and continue

Some pages have background polling that never fully idles. Wrap in try/except and add a fixed wait:

```python
try:
    page.wait_for_load_state("networkidle", timeout=12000)
except Exception:
    pass
page.wait_for_timeout(1000)
```

### All screenshots must be exactly 1920×1080 — never use `clip`

Always set `viewport={"width": 1920, "height": 1080}` and call `page.screenshot()` with no `clip`. A clipped screenshot has wrong dimensions and looks cut. If a UI element is below the fold, scroll the page or its container so it lands inside the viewport first.

### Capturing a loading spinner inside a scroll container

`page.mouse.wheel()` and `el.scrollTop = el.scrollHeight` won't reliably trigger React scroll listeners in headless mode. The reliable pattern is to **intercept the API and never resolve the next-page request**, so `isFetching` stays `true` permanently. Then scroll the container with mouse wheel until the spinner appears, wait for `[role='loading-component']`, and screenshot at full 1920×1080:

```python
import threading

fetched_once = {"v": False}
block = threading.Event()

def handle(route, request):
    if "your-list-endpoint" in request.url:
        if fetched_once["v"]:
            block.wait(timeout=30)   # hangs — isFetching stays true forever
            return
        fetched_once["v"] = True
    route.continue_()

ctx.route("**/your-list-endpoint**", handle)

# ... open the section, then scroll with mouse wheel ...
box = page.locator("[class*='overflow-y-auto']").first.bounding_box()
page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
for _ in range(10):
    page.mouse.wheel(0, 3000)
    page.wait_for_timeout(200)

page.wait_for_selector("[role='loading-component']", timeout=8000)
# scroll the container to bring spinner into viewport bottom
page.evaluate("""() => {
    const sc = document.querySelector('[class*="overflow-y-auto"]');
    if (sc) sc.scrollTop = sc.scrollHeight;
}""")
page.wait_for_timeout(300)
shot(page, "06-next-page-loading")   # full 1920×1080, no clip
block.set()
```

---

## Auth Patterns

### Bearer token + /me fetch (token already known)

```python
def fetch_me(bearer: str, api_base: str) -> dict:
    req = urllib.request.Request(
        f"{api_base}/v2/company/me",
        headers={"Authorization": f"Bearer {bearer}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())
```

Find `api_base` in `.env.local` → `NEXT_PUBLIC_API_HOST`.  
Find the `/me` path in `src/infra/repositories/auth/index.ts`.

### Credentials (email + password)

```python
def login_with_credentials(page, email: str, password: str):
    page.goto("http://localhost:3000/")
    page.fill('[name="user"]', email)
    page.fill('[name="password"]', password)
    page.click('[type="submit"]')
    page.wait_for_url("**/app/**", timeout=10000)
    token = page.evaluate("() => localStorage.getItem('token')")
    company = json.loads(page.evaluate("() => localStorage.getItem('company')"))
    return token, company
```

---

## Full Template

```python
import json
import subprocess
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

BEARER = "YOUR_BEARER_TOKEN"
BASE_URL = "http://localhost:3000/app/YOUR_PAGE"
API_BASE = "http://localhost:8080/api"
BRANCH = subprocess.check_output(["git", "rev-parse", "--abbrev-ref", "HEAD"]).decode().strip()
EVIDENCES_DIR = Path.home() / "Desktop" / f"screenshots-{BRANCH}"
HEADLESS = True

EVIDENCES_DIR.mkdir(exist_ok=True)

HIDE_DEVTOOLS_CSS = """
    .tsqd-parent-container,
    [data-testid="react-query-devtools-panel"],
    [data-testid="query-devtools-open-btn"] { display: none !important; }
"""

SUPPRESS_MODALS_JS = """
    localStorage.setItem('track-consent', 'accepted');
    // add other LocalStorageKeys here as needed
"""


def fetch_me() -> dict:
    req = urllib.request.Request(
        f"{API_BASE}/v2/company/me",
        headers={"Authorization": f"Bearer {BEARER}", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def make_context(browser, company_data: dict, flag_enabled: bool):
    context = browser.new_context(viewport={"width": 1920, "height": 1080})

    context.add_init_script(f"""
        localStorage.setItem('token', {json.dumps(BEARER)});
        localStorage.setItem('company', {json.dumps(json.dumps(company_data))});
        {SUPPRESS_MODALS_JS}
    """)

    def handle_flag(route, request):
        if "YOUR_FLAG_NAME" in request.url:
            route.fulfill(
                status=200,
                content_type="application/json",
                body=json.dumps({"enabled": flag_enabled}),
            )
        else:
            route.continue_()

    context.route("**/v1/feature-flags/check**", handle_flag)
    return context


def load_page(page, storage_patches: dict | None = None):
    page.goto(BASE_URL, wait_until="domcontentloaded")
    page.wait_for_load_state("domcontentloaded")
    if storage_patches:
        for key, value in storage_patches.items():
            page.evaluate(
                "([k, v]) => localStorage.setItem(k, JSON.stringify(v))",
                [key, value],
            )
        page.reload(wait_until="domcontentloaded")
    try:
        page.wait_for_load_state("networkidle", timeout=12000)
    except Exception:
        pass
    page.add_style_tag(content=HIDE_DEVTOOLS_CSS)
    page.wait_for_timeout(1000)


def shot(page, name: str):
    out = EVIDENCES_DIR / f"{name}.png"
    page.screenshot(path=str(out))
    print(f"Saved: {out}")


def run():
    print("Fetching session data...")
    company = fetch_me()
    print(f"Authenticated as: {company.get('name')} (id={company.get('id')})")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=HEADLESS)

        # --- Scenario 1: Feature flag disabled ---
        with make_context(browser, company, flag_enabled=False) as ctx:
            page = ctx.new_page()
            load_page(page)
            shot(page, "01-flag-disabled")

        # --- Scenario 2: Flag enabled, default state ---
        with make_context(browser, company, flag_enabled=True) as ctx:
            page = ctx.new_page()
            load_page(page)
            shot(page, "02-flag-enabled-default")

        # --- Scenario 3: Flag enabled, custom localStorage state ---
        with make_context(browser, company, flag_enabled=True) as ctx:
            page = ctx.new_page()
            load_page(page, storage_patches={"your-storage-key": "your-value"})
            shot(page, "03-flag-enabled-custom-state")

        # --- Scenario 4: Interaction (open first collapsible) ---
        with make_context(browser, company, flag_enabled=True) as ctx:
            page = ctx.new_page()
            load_page(page)
            toggle = page.locator("[aria-controls^='YOUR-COMPONENT-PREFIX-']").first
            toggle.wait_for(state="visible", timeout=10000)
            if toggle.get_attribute("aria-expanded") == "false":
                toggle.click()
                page.wait_for_timeout(600)
            toggle.scroll_into_view_if_needed()
            page.wait_for_timeout(400)
            shot(page, "04-first-section-open")

        browser.close()

    print(f"\nAll evidences saved to: {EVIDENCES_DIR}")


if __name__ == "__main__":
    run()
```

## Pre-flight Checklist

Before running:
- [ ] Dev server running at `http://localhost:3000`
- [ ] Backend running at `NEXT_PUBLIC_API_HOST` (check `.env.local`)
- [ ] Bearer token valid — test with `curl -H "Authorization: Bearer TOKEN" API_BASE/v2/company/me`
- [ ] `python -c "from playwright.sync_api import sync_playwright; print('ok')"` passes
- [ ] `evidences/` folder will be created automatically

Run: `python scripts/capture-evidences.py`
