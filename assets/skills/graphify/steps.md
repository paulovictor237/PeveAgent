Step 1 — Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

Step 2 — Install Graphify
uv tool install graphifyy

Step 3 — Register with your AI assistant
graphify install

Step 4 — Run it on your project from claude skill
/graphify .

Outputs -> graphify-out/ folder (HTML viz + markdown report + JSON graph).

Step 5 — Auto-rebuild on commits
graphify hook install

Outputs -> Rebuilds the graph automatically on every git commit.
