"""
BeeFriendly — ai.py
Thin Gemini client with an automatic model-fallback chain (models get
retired often, so we probe several current names and cache the winner).
"""

import base64
import re
import time
from typing import Optional

import requests

# Verified-current model names (older ones 404 over time).
MODEL_CANDIDATES = [
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-flash-lite-latest",
]

# Image-generation models (probed in order, first responder wins).
IMAGE_MODEL_CANDIDATES = [
    "gemini-3.1-flash-image",
    "gemini-2.5-flash-image",
    "nano-banana-pro-preview",
]

# Remembered after first success so later calls skip probing.
_working_model: Optional[str] = None

MAX_RETRIES = 3


class AIError(Exception):
    """Raised when Gemini fails permanently."""


_API_KEY: Optional[str] = None


def configure(api_key: str) -> None:
    """Store the API key for REST calls (called once per session)."""
    global _API_KEY
    _API_KEY = (api_key or "").strip()


def strip_fences(text: str) -> str:
    """Remove ```lang … ``` wrappers and stray language tags."""
    t = (text or "").strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n?", "", t)
        t = re.sub(r"\n?```$", "", t)
    return t.strip()


def clean_mermaid(raw: str) -> str:
    """Normalise model output into bare Mermaid syntax."""
    t = strip_fences(raw)
    # Some models prefix the code with the word 'mermaid'.
    if t.lower().startswith("mermaid") and "\n" in t:
        first, rest = t.split("\n", 1)
        if first.strip().lower() == "mermaid":
            t = rest.lstrip()
    return t.strip()


def _join_text_parts(parts) -> str:
    """
    Concatenate the real answer text from a parts list, skipping
    "thought" parts that thinking models emit alongside the answer.
    """
    chunks = []
    for part in parts or []:
        if isinstance(part, dict):
            if part.get("thought"):
                continue
            txt = part.get("text") or ""
        else:  # SDK-style protobuf part
            if getattr(part, "thought", False):
                continue
            txt = getattr(part, "text", "") or ""
        if txt:
            chunks.append(txt)
    return "".join(chunks).strip()


def _post_generate(model_name: str, body: dict, timeout: int = 120):
    """POST one generateContent request; returns parsed JSON."""
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{model_name}:generateContent?key={_API_KEY}")
    resp = requests.post(url, json=body, timeout=timeout)
    if resp.status_code != 200:
        raise ValueError(f"HTTP {resp.status_code}: {resp.text[:160]}")
    return resp.json()


def _call_model(system: str, user: str, temperature: float,
                max_tokens: int) -> str:
    """
    Run one text prompt through the model fallback chain with retries.

    Uses direct REST so we can disable "thinking" — newer flash models
    burn max_tokens on hidden reasoning, starving the actual answer
    (this caused blank/truncated HTML before).
    """
    global _working_model

    names = [_working_model] if _working_model else MODEL_CANDIDATES
    last_error = ""

    def build_body(with_thinking_off: bool) -> dict:
        gen_cfg = {"temperature": temperature,
                   "maxOutputTokens": max_tokens}
        if with_thinking_off:
            gen_cfg["thinkingConfig"] = {"thinkingBudget": 0}
        return {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": gen_cfg,
        }

    for name in names:
        allow_think_flag = [True]  # mutable across retry attempts
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                data = _post_generate(
                    name, build_body(allow_think_flag[0]), timeout=120)
                cand = (data.get("candidates") or [{}])[0]
                parts = cand.get("content", {}).get("parts", [])
                text = _join_text_parts(parts)
                if not text:
                    finish = cand.get("finishReason", "?")
                    raise ValueError(f"empty response (finish={finish})")
                _working_model = name          # cache the winner
                return text

            except Exception as exc:
                message = str(exc)
                lowered = message.lower()
                # Fatal — retrying will never help.
                if any(s in lowered for s in ("api key", "api_key",
                                              "401", "403")):
                    raise AIError(f"Invalid Gemini API key — {message}") from exc
                # Some models reject thinkingConfig → retry once without it.
                if "thinking" in lowered or "thinkingconfig" in lowered:
                    allow_think_flag[0] = False
                    continue
                last_error = message
                # Model retired/unavailable → jump straight to next candidate.
                if ("404" in message or "not found" in lowered
                        or "not supported" in lowered):
                    break
                # Rate limits / transient issues → wait then retry.
                time.sleep(3 * attempt)

    raise AIError(f"Gemini failed across all attempts/models — {last_error}")


def generate_text(system: str, user: str, temperature: float = 0.4,
                  max_tokens: int = 2048) -> str:
    """Generic single-shot generation."""
    return _call_model(system, user, temperature, max_tokens)


def generate_mermaid(instruction: str, topic: str) -> str:
    """Ask Gemini for rich, Napkin-style Mermaid code and clean it."""
    system = (
        "You are BeeFriendly, an expert presentation-diagram designer.\n"
        "Your style mimics Napkin.ai: colourful, modern infographic-style "
        "visuals built with Mermaid.js.\n"
        "\n"
        "OUTPUT RULES\n"
        "- Return ONLY raw Mermaid code. No explanations, no markdown "
        "fences, no comments.\n"
        "- First line MUST start with the diagram keyword (flowchart / "
        "mindmap / timeline / graph).\n"
        "- Keep every label under ~5 words so text stays readable.\n"
        "\n"
        "DESIGN RULES (apply to flowchart / graph types)\n"
        "- Use VARIED node shapes like Napkin does:\n"
        "    ([stadium]) for start/end points,\n"
        "    [rounded rectangle] for normal steps,\n"
        "    {diamond} for decisions/comparisons,\n"
        "    ((circle)) for key highlights or milestones.\n"
        "- Colour-code logical groups by defining these classes once:\n"
        "  classDef p1 fill:#FBCFE8,stroke:#DB2777,color:#111827,stroke-width:2px;\n"
        "  classDef p2 fill:#BFDBFE,stroke:#2563EB,color:#111827,stroke-width:2px;\n"
        "  classDef p3 fill:#FDE68A,stroke:#D97706,color:#111827,stroke-width:2px;\n"
        "  classDef p4 fill:#BBF7D0,stroke:#16A34A,color:#111827,stroke-width:2px;\n"
        "  classDef p5 fill:#DDD6FE,stroke:#7C3AED,color:#111827,stroke-width:2px;\n"
        "- Attach the classes (`class n1,n2 p1`) so the diagram mixes all "
        "colours evenly — never render everything in a single shade.\n"
        "- Prefer curved connectors; keep the layout balanced left-right."
    )
    raw = _call_model(system, f"{instruction}\n\nTOPIC: {topic}",
                      temperature=0.4, max_tokens=3072)
    code = clean_mermaid(raw)
    if not code:
        raise AIError("Model returned empty Mermaid code.")
    return code


def repair_mermaid(bad_code: str, error_message: str) -> str:
    """Feed the renderer's error back to Gemini for a one-shot fix."""
    system = (
        "You fix broken Mermaid.js code.\n"
        "Return ONLY the corrected raw Mermaid code — no explanations, "
        "no markdown fences, no comments."
    )
    user = (
        f"The following Mermaid code FAILED to render.\n\n"
        f"RENDERER ERROR:\n{error_message}\n\n"
        f"BROKEN CODE:\n{bad_code}\n\n"
        f"Return the smallest possible fix as raw Mermaid code."
    )
    raw = _call_model(system, user, temperature=0.2, max_tokens=2048)
    return clean_mermaid(raw)


def generate_html_visual(instruction: str, topic: str) -> str:
    """
    Napkin-style pro engine: Gemini designs a complete self-contained
    HTML/CSS infographic (emoji icons, coloured cards, arrows).
    Returns raw HTML string.
    """
    system = (
        "You are BeeFriendly's elite infographic designer. You create "
        "Napkin.ai-style professional visuals as single-file HTML.\n\n"
        "Return ONLY the complete HTML document starting with "
        "<!DOCTYPE html> — no explanations, no markdown fences.\n\n"
        "MANDATORY DESIGN SYSTEM:\n"
        "- <body style=\"margin:24px;background:#FFFFFF;font-family:"
        "'Segoe UI',Arial,sans-serif;color:#111827\"> \n"
        "- Title block: bold 30px heading + one-line grey subtitle "
        "(#6B7280, 15px).\n"
        "- Content built with flexbox/grid of rounded cards:\n"
        "    border-radius:16px; padding:18px 22px;\n"
        "    box-shadow:0 4px 14px rgba(15,23,42,.08);\n"
        "    border:1px solid #EEF2F7; background:#fff;\n"
        "- Rotate these 5 accent styles across cards (coloured left edge):\n"
        "    pink   #FDF2F8 / #EC4899\n"
        "    blue   #EFF6FF / #3B82F6\n"
        "    amber  #FFFBEB / #F59E0B\n"
        "    green  #F0FDF4 / #22C55E\n"
        "    violet #F5F3FF / #8B5CF6\n"
        "- EVERY card shows ONE large relevant emoji icon (~34px), a bold "
        "label (~17px) and a short one-line detail (#6B7280, 13px).\n"
        "- Connect flow with centred ➜ arrow characters (26px, #94A3B8, "
        "bold) placed between cards/rows.\n"
        "- Use small uppercase section kickers (12px letter-spacing 1px, "
        "#9CA3AF) above groups.\n"
        "- Total content height must stay under ~900px and width fills "
        "the page nicely.\n"
        "- NO JavaScript, NO external images/fonts, NO markdown."
    )
    full_prompt = f"{instruction}\n\nTOPIC: {topic}"

    def looks_like_html(text: str) -> bool:
        return ("<html" in text.lower() or "<!doctype" in text.lower())

    html = strip_fences(_call_model(system, full_prompt,
                                    temperature=0.5, max_tokens=8192))

    if not looks_like_html(html):
        # One firm retry — models occasionally answer in prose first.
        firm = ("IMPORTANT: Your previous reply was not usable. Respond "
                "with raw HTML code ONLY. The very first characters must "
                "be <!DOCTYPE html> and the last must be </html>. No "
                "commentary, no markdown.")
        try:
            html = strip_fences(_call_model(system, f"{full_prompt}\n\n{firm}",
                                            temperature=0.3, max_tokens=8192))
        except AIError:
            pass

    if not looks_like_html(html):
        raise AIError(
            "Model did not return an HTML document. Please press "
            "Generate again — occasional retries happen on free-tier."
        )

    # Salvage: if the model wrapped the document in prose/fences, pull out
    # everything from <html…/<!DOCTYPE to </html>.
    if not html.lower().lstrip().startswith(("<!doctype", "<html")):
        match = re.search(
            r"(<!doctype html.*?</html>|<html.*?</html>)",
            html, re.IGNORECASE | re.DOTALL)
        if match:
            html = match.group(1)

    return html


# ----------------------------------------------------------------------
# Vision — analyse an uploaded reference image
# ----------------------------------------------------------------------
def describe_reference(api_key: str, image_bytes: bytes,
                       mime: str = "image/png") -> str:
    """
    Look at a reference diagram/infographic and return a compact brief
    (structure, sections, colours, icons) that can be fed into the
    normal generation pipeline so we recreate something similar.
    """
    url_base = ("https://generativelanguage.googleapis.com/v1beta/models/"
                "{model}:generateContent?key={key}")
    instruction = (
        "You are looking at a diagram or infographic image. Write a "
        "compact recreation brief (max 180 words) covering:\n"
        "1. Layout direction (top-down / left-right / grid / radial)\n"
        "2. Number of sections/cards/nodes and their exact titles\n"
        "3. The connections or flow order between them\n"
        "4. Colour palette used (name the hues)\n"
        "5. Icon style and any notable design elements\n"
        "Be concrete so another designer could rebuild a similar visual."
    )
    body = {
        "contents": [{
            "parts": [
                {"text": instruction},
                {"inline_data": {
                    "mime_type": mime,
                    "data": base64.b64encode(image_bytes).decode(),
                }},
            ]
        }]
    }

    last_error = ""
    for name in MODEL_CANDIDATES:
        try:
            data = _post_generate(name, body, timeout=120)
            cand = (data.get("candidates") or [{}])[0]
            parts = cand.get("content", {}).get("parts", [])
            text = _join_text_parts(parts)
            if not text:
                raise ValueError("empty response")
            return text
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            if any(s in lowered for s in ("api key", "api_key",
                                          "401", "403")):
                raise AIError(f"Invalid Gemini API key — {message}") from exc
            last_error = f"{name}: {message}"

    raise AIError(f"Could not analyse the reference image. "
                  f"Tried all models. Last error: {last_error}")


# ----------------------------------------------------------------------
# AI image generation (text → picture, optional reference image)
# ----------------------------------------------------------------------
def generate_image(api_key: str, prompt: str,
                   ref_bytes: bytes | None = None,
                   ref_mime: str = "image/png") -> bytes:
    """
    Generate an image from a prompt using Gemini's image models.
    If ``ref_bytes`` is given, the reference image is attached so the
    model can match its style/composition. Returns raw image bytes.
    """
    url_base = ("https://generativelanguage.googleapis.com/v1beta/models/"
                "{model}:generateContent?key={key}")
    parts = [{"text": prompt}]
    if ref_bytes:
        parts.append({
            "inline_data": {
                "mime_type": ref_mime,
                "data": base64.b64encode(ref_bytes).decode(),
            }
        })
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
    }

    last_error = ""
    for name in IMAGE_MODEL_CANDIDATES:
        try:
            resp = requests.post(
                url_base.format(model=name, key=api_key.strip()),
                json=body, timeout=180,
            )
            if resp.status_code != 200:
                raise ValueError(f"HTTP {resp.status_code}: {resp.text[:160]}")

            data = resp.json()
            parts = data["candidates"][0]["content"]["parts"]
            for part in parts:
                inline = part.get("inlineData") or part.get("inline_data")
                if inline and inline.get("data"):
                    return base64.b64decode(inline["data"])
            raise ValueError("no image part in response")
        except Exception as exc:
            message = str(exc)
            lowered = message.lower()
            # Fatal — wrong key.
            if any(s in lowered for s in ("api key", "api_key",
                                          "401", "403")):
                raise AIError(f"Invalid Gemini API key — {message}") from exc
            if "429" in message or "quota" in lowered:
                last_error = (
                    "Free-tier IMAGE quota is used up for today "
                    "(resets daily around midnight US Pacific). "
                    "Diagram Studio still works! Options: wait for the "
                    "reset, generate fewer images per day, or enable "
                    "billing on your Google AI Studio key."
                )
                continue  # try next image model
            last_error = message
            continue  # try next image model

    raise AIError(f"Image generation failed on all models — {last_error}")
