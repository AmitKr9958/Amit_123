"""Conservative form assistance; never clicks buttons or fills sensitive fields."""
import re
from urllib.parse import urlsplit

SENSITIVE_TERMS = (
    "date of birth", "dob", "pan number", "pan card", "aadhaar", "aadhar",
    "passport", "bank account", "ifsc", "father name", "mother name",
    "marital status", "gender", "blood group", "emergency contact",
    "phone", "mobile", "email", "e-mail", "address", "pin code", "postal code",
    "driving licence", "driving license", "voter id", "social security",
)


def is_naukri_host(url: str) -> bool:
    host = (urlsplit(url or "").hostname or "").lower()
    return host == "naukri.com" or host.endswith(".naukri.com")


def is_sensitive_label(label: str) -> bool:
    text = re.sub(r"[^a-z0-9]+", " ", (label or "").lower()).strip()
    return any(term in text for term in SENSITIVE_TERMS)


def answer_candidates(cfg: dict) -> list[tuple[tuple[str, ...], str]]:
    p = cfg.get("applicant", {})
    answers = []
    if p.get("total_experience_years") is not None:
        answers.append((("total experience", "years of experience", "experience in years", "work experience"), str(p["total_experience_years"])))
    if p.get("notice_period_text"):
        answers.append((("notice period",), str(p["notice_period_text"])))
    if p.get("current_city"):
        answers.append((("current city", "current location", "preferred location"), str(p["current_city"])))
    if p.get("current_employer"):
        answers.append((("current employer", "current company", "present company"), str(p["current_employer"])))
    if p.get("current_title"):
        answers.append((("current designation", "current job title", "current title"), str(p["current_title"])))
    if p.get("qualification"):
        answers.append((("highest qualification", "highest education", "qualification"), str(p["qualification"])))
    if str(p.get("ctc_disclosure", "ask")).lower() == "numbers":
        if p.get("current_ctc_lpa") is not None:
            answers.append((("current ctc", "current salary", "present ctc", "present salary"), str(p["current_ctc_lpa"])))
        if p.get("expected_ctc_lpa") is not None:
            answers.append((("expected ctc", "expected salary", "expected compensation"), str(p["expected_ctc_lpa"])))
    return answers


def field_label(field) -> str:
    return field.evaluate("""el => {
      const parts = [];
      for (const attr of ['aria-label', 'placeholder', 'name', 'id']) {
        const value = el.getAttribute(attr);
        if (value) parts.push(value);
      }
      const id = el.getAttribute('id');
      if (id) {
        const label = document.querySelector('label[for="' + CSS.escape(id) + '"]');
        if (label) parts.push(label.innerText || label.textContent || '');
      }
      const wrapped = el.closest('label');
      if (wrapped) parts.push(wrapped.innerText || wrapped.textContent || '');
      return parts.join(' ').replace(/\\s+/g, ' ').trim().slice(0, 220);
    }""")


def prefill_known_fields(page, cfg: dict) -> list[str]:
    """Only fill blank, visible, ordinary text inputs with strongly matched labels.

    No selects/radios/checkboxes are changed. No Apply/Submit/Send control is
    clicked. External job portals and sensitive fields are never touched.
    """
    if not is_naukri_host(page.url):
        return []
    answers = answer_candidates(cfg)
    if not answers:
        return []
    fields = page.locator('input:not([type="hidden"]):not([type="password"]):not([type="checkbox"]):not([type="radio"]):not([type="file"]), textarea')
    filled = []
    for index in range(min(fields.count(), 100)):
        field = fields.nth(index)
        try:
            if not field.is_visible(timeout=250) or not field.is_enabled(timeout=250):
                continue
            tag = field.evaluate("el => el.tagName.toLowerCase()")
            typ = (field.get_attribute("type") or "text").lower()
            if typ in {"email", "tel", "url"} or (typ not in {"text", "number", "search"} and tag != "textarea"):
                continue
            if (field.input_value(timeout=250) or "").strip():
                continue
            label = field_label(field)
            lowered = label.lower()
            if not lowered or is_sensitive_label(label):
                continue
            for triggers, value in answers:
                if not any(trigger in lowered for trigger in triggers):
                    continue
                if typ == "number" and not re.fullmatch(r"\d+(?:\.\d+)?", value):
                    continue
                field.fill(value, timeout=700)
                filled.append(label[:80])
                break
        except Exception:
            continue
    return filled
