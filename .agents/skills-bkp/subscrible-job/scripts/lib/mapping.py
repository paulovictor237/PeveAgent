"""Field-to-profile mapping rules."""
import re
from typing import Any


def normalize(text: str) -> str:
    """Normalize text for comparison: lowercase, remove accents, strip punctuation."""
    if not text:
        return ""
    import unicodedata
    normalized = unicodedata.normalize("NFD", text)
    normalized = re.sub(r"[̀-ͯ]", "", normalized)
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9\s]", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    return normalized


def field_text(field: dict) -> str:
    """Join all searchable text from a field."""
    parts = [field.get("label", ""), field.get("placeholder", ""),
             field.get("ariaLabel", ""), field.get("name", ""), field.get("id", "")]
    return normalize(" ".join(p for p in parts if p))


def has_any(text: str, keywords: list[str]) -> bool:
    """Check if any keyword appears in text."""
    ntext = normalize(text)
    return any(normalize(k) in ntext for k in keywords)


def first_name(name: str) -> str:
    return name.split()[0] if name else ""


def last_name(name: str) -> str:
    parts = name.split()
    return " ".join(parts[1:]) if len(parts) > 1 else ""


def format_date_iso(br: str) -> str:
    """Convert DD/MM/YYYY to YYYY-MM-DD."""
    parts = br.split("/")
    if len(parts) == 3:
        d, m, y = parts
        return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
    return br


def salary_expectation(profile: dict) -> str:
    """Build salary expectation string from PJ and CLT ranges."""
    pj = profile.get("job_preferences", {}).get("primary", {}).get("salary_range", {})
    clt = profile.get("job_preferences", {}).get("secondary", {}).get("salary_range", {})
    parts = []
    if pj:
        parts.append(f"PJ: R$ {pj.get('min', 0):,} ~ R$ {pj.get('max', 0):,}")
    if clt:
        parts.append(f"CLT: R$ {clt.get('min', 0):,} ~ R$ {clt.get('max', 0):,}")
    return " / ".join(parts)


def languages(profile: dict) -> str:
    return ", ".join(f"{l.get('language','')} ({l.get('level','')})" for l in profile.get("languages", []))


def skills(profile: dict) -> str:
    return ", ".join(profile.get("skills", []))


def education_short(profile: dict) -> str:
    top = profile.get("education", [{}])[0] if profile.get("education") else {}
    if not top:
        return ""
    year = top.get("end", "").split("-")[0] if top.get("end") else ""
    year_part = f" ({year})" if year else ""
    return f"{top.get('degree','')} em {top.get('field','')} — {top.get('institution','')}{year_part}"


def top_experience(profile: dict) -> str:
    exp = profile.get("experience", [{}])[0] if profile.get("experience") else {}
    if not exp:
        return ""
    role = exp.get("roles", [{}])[0] if exp.get("roles") else {}
    duration = exp.get("total_duration", "")
    company = exp.get("company", "")
    title = role.get("title", "")
    parts = [p for p in [duration, "na" if company and duration else "", company, "como" if title else "", title] if p]
    return " ".join(parts).strip()


def graduation_month(profile: dict) -> str | None:
    end = profile.get("education", [{}])[0].get("end", "") if profile.get("education") else ""
    if not end:
        return None
    month_num = int(end.split("-")[1]) if "-" in end else 0
    months = ["Janeiro","Fevereiro","Março","Abril","Maio","Junho",
              "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
    return months[month_num - 1] if 1 <= month_num <= 12 else str(month_num)


def graduation_year(profile: dict) -> str | None:
    end = profile.get("education", [{}])[0].get("end", "") if profile.get("education") else ""
    return end.split("-")[0] if end and "-" in end else None


def education_status(profile: dict, field: dict) -> str:
    end = profile.get("education", [{}])[0].get("end", "") if profile.get("education") else ""
    if not end:
        return "Cursando"
    year = int(end.split("-")[0]) if "-" in end else 0
    current_year = 2026
    status = "Completo" if (year > 0 and year <= current_year) else "Cursando"
    options = field.get("options", [])
    if options:
        normalized_status = normalize(status)
        for opt in options:
            if normalize(opt) == normalized_status:
                return opt
    return status


def select_best_option(field: dict, value: str) -> str | None:
    """Find best matching option in dropdown."""
    options = field.get("options", [])
    if not options:
        return value
    nv = normalize(value)
    for opt in options:
        if normalize(opt) == nv:
            return opt
    for opt in options:
        if normalize(opt) in nv or nv in normalize(opt):
            return opt
    return None


def best_selector(field: dict) -> str:
    """Build CSS selector for field."""
    tag = field.get("tag", "input")
    name = field.get("name", "")
    id_ = field.get("id", "")
    aria = field.get("ariaLabel", "")
    placeholder = field.get("placeholder", "")
    type_ = field.get("type", "")

    def esc(s: str) -> str:
        return s.replace('"', '\\"')

    if name:
        return f'{tag}[name="{esc(name)}"]'
    if id_:
        return f'#{esc(id_)}'
    if aria:
        return f'{tag}[aria-label*="{esc(aria)}"]'
    if placeholder:
        return f'{tag}[placeholder*="{esc(placeholder)}"]'
    if type_:
        return f'{tag}[type="{type_}"]'
    return tag


def css_escape(s: str) -> str:
    return s.replace('"', '\\"')


# ── RULES ────────────────────────────────────────────────────────────────────
# Ordered from most specific to most generic — first match wins.

RULES: list[dict] = [
    # Identidade
    {"keywords": ["full name", "nome completo"], "resolve": lambda p, f: p.get("name")},
    {"keywords": ["last name", "sobrenome", "surname", "ultimo nome"], "resolve": lambda p, f: last_name(p.get("name", ""))},
    {"keywords": ["first name", "primeiro nome", "given name"], "resolve": lambda p, f: first_name(p.get("name", ""))},

    # Contato
    {"keywords": ["e mail", "email", "correio"], "resolve": lambda p, f: p.get("email")},
    {"keywords": ["telefone", "celular", "phone", "whatsapp", "fone"], "resolve": lambda p, f: p.get("phone")},
    {"keywords": ["cpf"], "resolve": lambda p, f: p.get("cpf")},
    {"keywords": ["rg", "documento de identidade", "numero do rg"], "resolve": lambda p, f: p.get("rg")},

    # Nascimento
    {
        "keywords": ["data de nascimento", "nascimento", "birth", "aniversario", "birthday", "date of birth"],
        "resolve": lambda p, f: format_date_iso(p.get("birth_date", "")) if f.get("type") == "date" else p.get("birth_date"),
    },

    # Links
    {"keywords": ["linkedin"], "resolve": lambda p, f: p.get("linkedin")},
    {"keywords": ["github", "portfolio"], "resolve": lambda p, f: p.get("github")},

    # Endereço
    {"keywords": ["cidade", "city", "municipio"], "resolve": lambda p, f: p.get("address", {}).get("city")},
    {"keywords": ["estado", "state", "uf"], "resolve": lambda p, f: (
        select_best_option(f, p.get("address", {}).get("state", "") or "")
        or select_best_option(f, p.get("address", {}).get("state_abbr", "") or "")
        or p.get("address", {}).get("state")
    )},
    {"keywords": ["cep", "zip", "postal code"], "resolve": lambda p, f: p.get("extra_fields", {}).get("cep")},
    {"keywords": ["bairro", "neighborhood", "district"], "resolve": lambda p, f: p.get("extra_fields", {}).get("bairro")},
    {"keywords": ["endereco", "rua", "street", "logradouro"], "resolve": lambda p, f: (
        f'{p.get("address", {}).get("street", "")}, {p.get("address", {}).get("number", "")}' if p.get("address") else None
    )},
    {"keywords": ["pais", "country", "nacao"], "resolve": lambda p, f: p.get("address", {}).get("country")},

    # Educação
    {
        "keywords": ["nome da universidade", "nome da instituicao", "instituicao de ensino", "nome da escola",
                     "universidade", "faculdade", "institution", "school name", "college"],
        "resolve": lambda p, f: p.get("education", [{}])[0].get("institution") if p.get("education") else None,
    },
    {"keywords": ["status da formacao", "qual status", "situacao da formacao", "concluiu", "completou"],
     "resolve": lambda p, f: education_status(p, f)},
    {
        "keywords": ["nivel de ensino", "nivel ensino", "formacao superior", "nivel de escolaridade",
                    "education level", "grau de escolaridade", "nivel superior"],
        "resolve": lambda p, f: select_best_option(f, p.get("education", [{}])[0].get("degree", "") or "") or (
            p.get("education", [{}])[0].get("degree") if p.get("education") else None
        ),
    },
    {"keywords": ["grau", "degree", "titulo academico"],
     "resolve": lambda p, f: select_best_option(f, p.get("education", [{}])[0].get("degree", "") or "") or (
         p.get("education", [{}])[0].get("degree") if p.get("education") else None
     )},
    {"keywords": ["disciplina", "curso de graduacao", "area de formacao", "campo de estudo", "field of study", "major"],
     "resolve": lambda p, f: p.get("education", [{}])[0].get("field") if p.get("education") else None},
    {"keywords": ["ano de conclusao", "ano conclusao", "graduation year", "ano formacao", "ano de termino"],
     "resolve": lambda p, f: graduation_year(p)},
    {"keywords": ["mes de conclusao", "mes conclusao", "graduation month", "mes de termino"],
     "resolve": lambda p, f: graduation_month(p)},
    {"keywords": ["formacao", "escolaridade", "graduacao", "education"], "resolve": education_short},

    # Experiência
    {"keywords": ["empresa atual", "empresa anterior", "nome da empresa", "current company", "employer", "onde trabalha"],
     "resolve": lambda p, f: p.get("experience", [{}])[0].get("company") if p.get("experience") else None},
    {"keywords": ["cargo atual", "posicao atual", "current role", "titulo atual", "current position"],
     "resolve": lambda p, f: p.get("current_role")},
    {"keywords": ["experiencia", "anos de experiencia", "tempo de experiencia"], "resolve": top_experience},

    # Salário / Contrato
    {"keywords": ["salario", "pretensao", "remuneracao", "expectativa salarial", "salary", "pacote salarial"],
     "resolve": salary_expectation},
    {"keywords": ["contrato", "regime", "tipo de contrato", "contract type"],
     "resolve": lambda p, f: select_best_option(f, p.get("job_preferences", {}).get("primary", {}).get("contract", "") or "")},

    # Disponibilidade
    {
        "keywords": ["disponibilidade para trabalhar no modelo hibrido", "disponivel para hibrido",
                    "disponibilidade hibrido", "modelo hibrido"],
        "resolve": lambda p, f: (
            select_best_option(f, "Sim" if "hibrido" in normalize(p.get("job_preferences", {}).get("primary", {}).get("modality", "")) else "Nao")
            or ("Sim" if "hibrido" in normalize(p.get("job_preferences", {}).get("primary", {}).get("modality", "")) else "Nao")
        ),
    },
    {"keywords": ["modalidade", "modelo de trabalho", "work model"],
     "resolve": lambda p, f: select_best_option(f, p.get("job_preferences", {}).get("primary", {}).get("modality", "") or "")},
    {"keywords": ["disponibilidade", "quando pode comecar", "start date", "notice period"],
     "resolve": lambda p, f: f'{round((p.get("job_preferences", {}).get("availability_days") or 30) / 30)} mes'},
    {"keywords": ["viagem", "travel", "disponivel para viagens"],
     "resolve": lambda p, f: (
        select_best_option(f, "Sim" if p.get("job_preferences", {}).get("willing_to_travel") else "Nao")
        or ("Sim" if p.get("job_preferences", {}).get("willing_to_travel") else "Nao")
    )},
    {"keywords": ["mudanca", "relocate", "relocation", "disponivel para mudanca"],
     "resolve": lambda p, f: (
        select_best_option(f, "Sim" if p.get("job_preferences", {}).get("willing_to_relocate") else "Nao")
        or ("Sim" if p.get("job_preferences", {}).get("willing_to_relocate") else "Nao")
    )},

    # Diversidade
    {"keywords": ["pcd", "deficiencia", "disability", "portador", "tipo de deficiencia"],
     "resolve": lambda p, f: (
         select_best_option(f, "Sim" if p.get("pcd") else "Nao")
         or ("Sim" if p.get("pcd") else "Nao")
     )},
    {"keywords": ["genero", "gender", "sexo"],
     "resolve": lambda p, f: select_best_option(f, p.get("gender") or "") or p.get("gender")},
    {"keywords": ["pronome"], "resolve": lambda p, f: select_best_option(f, p.get("pronoun") or "") or p.get("pronoun")},
    {"keywords": ["raca", "etnia", "cor", "race", "ethnicity"],
     "resolve": lambda p, f: select_best_option(f, p.get("ethnicity") or "") or p.get("ethnicity")},

    # Recrutamento
    {"keywords": ["parentesco", "parente", "familiar", "funcionario btg", "conhece funcionario"],
     "resolve": lambda p, f: select_best_option(f, "Nao") or "Nao"},
    {"keywords": ["como ficou sabendo", "como soube", "como conheceu", "como nos encontrou",
                  "source", "indicacao", "canal", "referral"],
     "resolve": lambda p, f: p.get("job_preferences", {}).get("job_source")},

    # Outros
    {"keywords": ["idioma", "lingua", "language"], "resolve": languages},
    {"keywords": ["sobre voce", "resumo", "summary", "apresentacao pessoal", "bio"],
     "resolve": lambda p, f: p.get("summary")},
    {"keywords": ["habilidade", "skill", "competencia", "tecnologia"], "resolve": skills},

    # nome genérico — deve ficar por último
    {"keywords": ["nome"], "resolve": lambda p, f: p.get("name")},
]


def map_field(field: dict, profile: dict, pdf_path: str) -> dict:
    """Map a field to an action or report unmapped."""
    # Skip recaptcha and hidden
    if field.get("name") == "g-recaptcha-response":
        return {"kind": "skip", "reason": "recaptcha"}
    if field.get("type") == "hidden":
        return {"kind": "skip", "reason": "hidden"}

    text = field_text(field)

    # File upload
    if field.get("tag") == "input" and field.get("type") == "file":
        selector = best_selector(field)
        return {
            "kind": "action",
            "action": {"kind": "upload", "selector": selector, "path": pdf_path},
            "description": f"Upload: {pdf_path.split('/')[-1]}",
        }

    # Try rules
    for rule in RULES:
        if not has_any(text, rule["keywords"]):
            continue

        kind = rule.get("kind", "")
        if kind == "cover_letter":
            return {"kind": "cover_letter", "field": field}
        if kind == "upload":
            selector = best_selector(field)
            return {
                "kind": "action",
                "action": {"kind": "upload", "selector": selector, "path": pdf_path},
                "description": f"Upload: {pdf_path.split('/')[-1]}",
            }

        resolver = rule["resolve"]
        value = resolver(profile, field)
        if value is None or value == "":
            return {"kind": "unmapped", "field": field, "reason": "valor ausente no profile"}

        return _build_action(field, value)

    # Checkbox without keyword match
    if field.get("type") == "checkbox":
        return {"kind": "unmapped", "field": field, "reason": "checkbox sem keyword"}

    return {"kind": "unmapped", "field": field, "reason": "nenhuma keyword correspondeu"}


def _build_action(field: dict, value: str) -> dict:
    """Build an action from a field and resolved value."""
    selector = best_selector(field)
    tag = field.get("tag", "")
    ftype = field.get("type", "")

    if tag == "select":
        return {
            "kind": "action",
            "action": {"kind": "select", "selector": selector, "label": value},
            "description": f"Select: {value}",
        }
    if ftype in ("checkbox", "radio"):
        truthy = re.match(r"^(sim|yes|true|1|on)$", value.strip(), re.IGNORECASE)
        if not truthy:
            return {"kind": "skip", "reason": f'checkbox/radio "{value}" → nao marcar'}
        return {
            "kind": "action",
            "action": {"kind": "check", "selector": selector},
            "description": "Check",
        }
    if ftype == "date":
        return {
            "kind": "action",
            "action": {"kind": "fill", "selector": selector, "value": value},
            "description": f"Date: {value}",
        }
    return {
        "kind": "action",
        "action": {"kind": "fill", "selector": selector, "value": value},
        "description": f"Fill: {value}",
    }