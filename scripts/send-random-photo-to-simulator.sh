#!/usr/bin/env bash
# Gera N imagens aleatórias com variação e envia para a galeria do simulador iOS
# Uso: ./send-random-photo-to-simulator.sh [quantidade]

set -e

COUNT=${1:-1}

if ! [[ "$COUNT" =~ ^[0-9]+$ ]] || [ "$COUNT" -lt 1 ]; then
  echo "Uso: $0 [quantidade]  (padrao: 1)"
  exit 1
fi

# ── Detectar simulador booted ────────────────────────────────────────────────
SIMULATOR_UDID=$(xcrun simctl list devices booted 2>/dev/null \
  | grep -oE '[A-F0-9]{8}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{4}-[A-F0-9]{12}' \
  | head -1)

if [ -z "$SIMULATOR_UDID" ]; then
  echo "Nenhum simulador iOS iniciado. Abra um simulador primeiro."
  exit 1
fi

SIMULATOR_NAME=$(xcrun simctl list devices booted 2>/dev/null \
  | grep "(Booted)" | sed 's/ (Booted)//' | sed 's/^[[:space:]]*//' | head -1)

echo "Simulador: $SIMULATOR_NAME ($SIMULATOR_UDID)"
echo "Gerando $COUNT imagem(ns)..."

TEMP_DIR=$(mktemp -d)

for i in $(seq 1 "$COUNT"); do
  OUTPUT="$TEMP_DIR/photo_${i}_$(date +%s%N).jpg"
  echo -n "[$i/$COUNT] "

# ── Gerar imagem com Python + Pillow ──────────────────────────────────────────
python3 - "$OUTPUT" <<'PYEOF'
import sys, random, math
from PIL import Image, ImageDraw, ImageFilter

SEED = random.randint(0, 2**32 - 1)
rng  = random.Random(SEED)

W, H = 1080, 1080

# Paleta: 2-3 cores dominantes com pequena variação aleatória
def rand_color():
    h = rng.uniform(0, 360)
    s = rng.uniform(0.4, 0.9)
    v = rng.uniform(0.5, 0.95)
    # HSV → RGB
    c = v * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = v - c
    sector = int(h / 60) % 6
    rgb = [(c,x,0),(x,c,0),(0,c,x),(0,x,c),(x,0,c),(c,0,x)][sector]
    return tuple(int((ch + m) * 255) for ch in rgb)

bg   = rand_color()
col1 = rand_color()
col2 = rand_color()
col3 = rand_color()

img  = Image.new("RGB", (W, H), bg)
draw = ImageDraw.Draw(img, "RGBA")

# ── Formas geométricas aleatórias ────────────────────────────────────────────
num_shapes = rng.randint(12, 25)

for _ in range(num_shapes):
    shape = rng.choice(["ellipse", "rectangle", "polygon"])
    color = rng.choice([col1, col2, col3])
    alpha = rng.randint(60, 200)
    rgba  = (*color, alpha)

    cx = rng.randint(0, W)
    cy = rng.randint(0, H)
    rx = rng.randint(40, 350)
    ry = rng.randint(40, 350)

    if shape == "ellipse":
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=rgba)

    elif shape == "rectangle":
        angle = rng.uniform(0, 90)  # simulated via polygon
        corners = [
            (cx - rx, cy - ry),
            (cx + rx, cy - ry),
            (cx + rx, cy + ry),
            (cx - rx, cy + ry),
        ]
        # rotate corners
        cos_a = math.cos(math.radians(angle))
        sin_a = math.sin(math.radians(angle))
        rotated = [
            (cx + (px - cx) * cos_a - (py - cy) * sin_a,
             cy + (px - cx) * sin_a + (py - cy) * cos_a)
            for px, py in corners
        ]
        draw.polygon(rotated, fill=rgba)

    else:  # polygon
        sides = rng.randint(3, 8)
        pts = [
            (cx + rx * math.cos(2 * math.pi * i / sides + rng.uniform(-0.3, 0.3)),
             cy + ry * math.sin(2 * math.pi * i / sides + rng.uniform(-0.3, 0.3)))
            for i in range(sides)
        ]
        draw.polygon(pts, fill=rgba)

# ── Variação: leve blur + ajuste de brilho via overlay ───────────────────────
blur_radius = rng.uniform(0.5, 2.5)
img = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))

# Overlay sutil com cor randômica para mudar o "tom" da imagem
overlay_color = rand_color()
overlay_alpha = rng.randint(15, 45)
overlay = Image.new("RGBA", (W, H), (*overlay_color, overlay_alpha))
img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")

# ── Salvar ────────────────────────────────────────────────────────────────────
out_path = sys.argv[1]
img.save(out_path, "JPEG", quality=92)
print(f"Seed: {SEED} | Blur: {blur_radius:.2f} | Overlay alpha: {overlay_alpha}")
PYEOF

  xcrun simctl addmedia "$SIMULATOR_UDID" "$OUTPUT"
  echo "Enviada!"
done

echo "Concluido! $COUNT imagem(ns) adicionada(s) a galeria."

# ── Limpeza ───────────────────────────────────────────────────────────────────
rm -rf "$TEMP_DIR"
