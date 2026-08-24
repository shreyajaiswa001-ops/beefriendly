"""
BeeFriendly — diagrams.py
Turns plain-English topics into presentation-ready images.
- Mermaid visuals are rendered through https://mermaid.ink
- Comparison tables are rendered locally with matplotlib
- Includes theme injection and a Gemini-powered auto-repair loop
"""

import base64
import io
import os
import re

import requests

import ai

INK_URL = "https://mermaid.ink/img/"


class DiagramError(Exception):
    """Raised when a visual cannot be generated or rendered."""


# ----------------------------------------------------------------------
# Visual catalogue — each type carries its Mermaid instruction.
# {dir} is replaced with TD (top-down) or LR (left-right).
# ----------------------------------------------------------------------
VISUALS = {
    "Flowchart": {
        "kind": "mermaid",
        "instruction": ("a clean step-by-step flowchart using `flowchart {dir}`. "
                        "Use rounded rectangles for steps and diamonds for "
                        "decisions. Maximum 14 nodes."),
    },
    "Mind Map": {
        "kind": "mermaid",
        "instruction": ("a `mindmap` diagram rooted at the topic with 5-7 main "
                        "branches; each branch has 2-4 short sub-points "
                        "(max 4 words each), written with indentation."),
    },
    "SWOT Analysis": {
        "kind": "mermaid",
        "instruction": ("a `flowchart {dir}` representing a SWOT analysis: four "
                        "subgraphs titled Strengths, Weaknesses, Opportunities "
                        "and Threats, each containing exactly 3 short nodes."),
    },
    "Timeline": {
        "kind": "mermaid",
        "instruction": ("a `timeline` diagram with `title` plus 4-6 periods, "
                        "each holding one short event description."),
    },
    "Comparison Table": {
        "kind": "table",
        "instruction": ("a markdown comparison table for the topic. First row "
                        "is the header. Use | pipes | as separators. Include "
                        "3-5 criteria rows and keep every cell under 6 words."),
    },
    "Cycle / Process Diagram": {
        "kind": "mermaid",
        "instruction": ("a `flowchart {dir}` describing a cyclical process where "
                        "the LAST node connects back to the FIRST, forming a "
                        "closed loop. Maximum 10 nodes."),
    },
    "Architecture Diagram": {
        "kind": "mermaid",
        "instruction": ("a `flowchart {dir}` showing layered architecture using "
                        "subgraphs for layers (e.g. Client / Application / Data) "
                        "with labelled arrows between components."),
    },
    "Concept Tree": {
        "kind": "mermaid",
        "instruction": ("a `graph {dir}` shaped like a tree: one root concept, "
                        "3-4 category branches and 2-3 leaf items per branch."),
    },
    "Fishbone (Cause & Effect)": {
        "kind": "mermaid",
        "instruction": ("a `flowchart {dir}` fishbone diagram: a central spine "
                        "ending at the effect node, with 4-6 diagonal cause "
                        "branches grouped into categories."),
    },
    "Decision Tree": {
        "kind": "mermaid",
        "instruction": ("a `graph {dir}` decision tree starting from one choice "
                        "node, branching through diamond decision nodes with "
                        "Yes/No or option labels on every edge, ending in "
                        "outcome nodes. Maximum 11 nodes."),
    },
    "Org Chart / Hierarchy": {
        "kind": "mermaid",
        "instruction": ("a `graph {dir}` hierarchy chart: one root role/team at "
                        "the top, 2-4 second-level units, 2-3 members under each."),
    },
    "Kanban Board": {
        "kind": "mermaid",
        "instruction": ("a `flowchart {dir}` kanban board: four subgraphs titled "
                        "To Do, In Progress, Review and Done, each holding 2-3 "
                        "task card nodes connected left to right."),
    },
    "Journey Roadmap": {
        "kind": "mermaid",
        "instruction": ("a `flowchart LR` journey roadmap: 5-6 milestone nodes "
                        "in order, each with a phase label and one-line outcome, "
                        "connected by labelled arrows."),
    },
    "Layered Pyramid": {
        "kind": "mermaid",
        "instruction": ("a `flowchart TD` pyramid: 4 stacked level subgraphs "
                        "from widest base level to narrowest top level, each "
                        "level containing 1-3 items."),
    },
}

EXAMPLES = {
    "Flowchart": "user login flow of our app",
    "Mind Map": "machine learning for beginners",
    "SWOT Analysis": "starting a food delivery startup",
    "Timeline": "evolution of Indian cinema",
    "Comparison Table": "iPhone vs Android",
    "Cycle / Process Diagram": "water cycle for class 8",
    "Architecture Diagram": "netflix video streaming architecture",
    "Concept Tree": "parts of speech in English grammar",
    "Fishbone (Cause & Effect)": "why students fail exams",
    "Decision Tree": "should I study abroad or in India",
    "Org Chart / Hierarchy": "structure of a startup company",
    "Kanban Board": "final year project workflow",
    "Journey Roadmap": "learning data science from zero to job",
    "Layered Pyramid": "levels of human needs",
}

# Theme palettes injected as a Mermaid init directive.
# NOTE: every theme forces a pure WHITE image background.
PALETTES = {
    "Candy (Pink & Blue)": {
        "primaryColor": "#F9A8D4", "primaryTextColor": "#111827",
        "primaryBorderColor": "#DB2777", "lineColor": "#3B82F6",
        "secondaryColor": "#BFDBFE", "tertiaryColor": "#FFF5F8",
        "clusterBkg": "#FFF0F6", "clusterBorder": "#F9A8D4",
        "edgeLabelBackground": "#FFFFFF", "background": "#FFFFFF"},
    "Honey": {"primaryColor": "#FEF3C7", "primaryTextColor": "#0F172A",
              "primaryBorderColor": "#B45309", "lineColor": "#B45309",
              "secondaryColor": "#FFFBEB", "tertiaryColor": "#F8FAFC",
              "edgeLabelBackground": "#FFFFFF", "background": "#FFFFFF"},
    "Blue": {"primaryColor": "#DBEAFE", "primaryTextColor": "#0F172A",
             "primaryBorderColor": "#2E5EAA", "lineColor": "#2E5EAA",
             "secondaryColor": "#EFF6FF", "tertiaryColor": "#F8FAFC",
             "edgeLabelBackground": "#FFFFFF", "background": "#FFFFFF"},
    "Teal": {"primaryColor": "#CCFBF1", "primaryTextColor": "#0F172A",
             "primaryBorderColor": "#0E7C66", "lineColor": "#0E7C66",
             "secondaryColor": "#F0FDFA", "tertiaryColor": "#F8FAFC",
             "edgeLabelBackground": "#FFFFFF", "background": "#FFFFFF"},
    "Purple": {"primaryColor": "#EDE9FE", "primaryTextColor": "#0F172A",
               "primaryBorderColor": "#6D28D9", "lineColor": "#6D28D9",
               "secondaryColor": "#F5F3FF", "tertiaryColor": "#F8FAFC",
               "edgeLabelBackground": "#FFFFFF", "background": "#FFFFFF"},
}


def apply_theme(code: str, theme) -> str:
    """
    Strip any existing init directive and inject our palette.
    ``theme`` is either a palette NAME (string) or a custom palette dict
    built from the user's colour pickers.
    """
    body = "\n".join(
        line for line in code.splitlines()
        if not line.lstrip().startswith("%%{init")
    ).strip()

    import json

    if isinstance(theme, dict):
        # Custom palette — force pure white canvas like every other theme.
        variables = json.dumps({**theme, "background": "#FFFFFF"})
        directive = ("%%{init: {'theme':'base','themeVariables':"
                     f"{variables}}}%%")
    elif theme == "Dark":
        # Dark keeps its dark canvas (white would hide light text),
        directive = "%%{init: {'theme':'dark'}}%%"
    else:
        variables = json.dumps(PALETTES.get(theme, PALETTES["Candy (Pink & Blue)"]))
        directive = ("%%{init: {'theme':'base','themeVariables':"
                     f"{variables}}}%%")
    return f"{directive}\n{body}"


# ----------------------------------------------------------------------
# mermaid.ink rendering
# ----------------------------------------------------------------------
def _fetch(fmt: str, themed_code: str, dark: bool) -> bytes:
    b64 = base64.urlsafe_b64encode(themed_code.encode("utf-8")).decode("ascii")
    url = f"{INK_URL}{b64}?type={fmt}"
    if dark:
        url += "&theme=dark"
    try:
        resp = requests.get(url, timeout=60)
    except requests.RequestException as exc:
        raise DiagramError(f"Could not reach mermaid.ink — check your "
                           f"internet connection ({exc})") from exc

    content_type = resp.headers.get("content-type", "")
    if resp.status_code != 200 or "json" in content_type or "text/html" in content_type:
        snippet = ""
        if "json" in content_type or "text" in content_type:
            snippet = resp.text[:180]
        raise DiagramError(f"Mermaid renderer returned HTTP "
                           f"{resp.status_code}. {snippet}")
    return resp.content


def render_mermaid(code: str, theme: str):
    """Return (png_bytes, svg_bytes) for a piece of Mermaid code."""
    themed = apply_theme(code, theme)
    png = _fetch("png", themed, dark=(theme == "Dark"))
    svg = None
    try:
        svg = _fetch("svg", themed, dark=(theme == "Dark"))
    except DiagramError:
        pass  # PNG is the critical output; SVG is best-effort.
    return png, svg


# ----------------------------------------------------------------------
# Comparison-table rendering (matplotlib)
# ----------------------------------------------------------------------
def render_table_png(markdown_table: str, accent: str = "#B45309") -> bytes:
    """Convert a markdown pipe-table into a styled PNG image."""
    rows = []
    for line in markdown_table.strip().splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        # Skip separator rows like |---|---|
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c != ""):
            continue
        rows.append(cells)

    if len(rows) < 2:
        raise DiagramError("The model did not return a valid table to render.")

    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]

    import matplotlib
    matplotlib.use("Agg")           # headless rendering
    import matplotlib.pyplot as plt

    n_rows, n_cols = len(rows), width
    fig_w = min(2.2 * n_cols + 2, 14)
    fig_h = min(0.62 * n_rows + 1.2, 12)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis("off")

    table = ax.table(cellText=rows[1:], colLabels=rows[0],
                     cellLoc="center", loc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(11)
    table.scale(1, 1.9)

    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor("#CBD5E1")
        if r == 0:                                # header row
            cell.set_facecolor(accent)
            cell.set_text_props(color="white", fontweight="bold")
        elif r % 2 == 0:                          # zebra striping
            cell.set_facecolor("#FDF3DF")
        else:
            cell.set_facecolor("white")

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight",
                facecolor="white")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


# ----------------------------------------------------------------------
# Public pipeline
# ----------------------------------------------------------------------
def create_visual(visual_type: str, topic: str,
                  direction: str = "TD", theme: str = "Honey") -> dict:
    """
    Generate one visual end-to-end.

    Returns dict: kind ('mermaid'|'table'), label, source (code/markdown),
                  png bytes, svg bytes-or-None.
    Raises DiagramError / ai.AIError on failure.
    """
    cfg = VISUALS[visual_type]

    # ---- Comparison tables -------------------------------------------------
    if cfg["kind"] == "table":
        system = ("You create concise, accurate markdown tables. "
                  "Return ONLY the table — no explanations.")
        raw = ai.generate_text(system,
                               cfg["instruction"] + f"\n\nTOPIC: {topic}",
                               temperature=0.4, max_tokens=1024)
        md = ai.strip_fences(raw)
        try:
            png = render_table_png(md)
        except DiagramError:
            # One repair attempt for malformed tables.
            fixed = ai.generate_text(
                system,
                f"Fix this markdown table (keep pipes, proper header row):\n{md}\n"
                f"Topic was: {topic}. Return ONLY the corrected table.",
                temperature=0.2, max_tokens=1024)
            md = ai.strip_fences(fixed)
            png = render_table_png(md)
        label = f"{visual_type}: {topic[:34]}"
        return {"kind": "table", "label": label,
                "source": md, "png": png, "svg": None}

    # ---- Mermaid visuals ---------------------------------------------------
    direction = "LR" if direction == "LR" else "TD"
    instruction = cfg["instruction"].replace("{dir}", direction)

    code = ai.generate_mermaid(instruction, topic)

    try:
        png, svg = render_mermaid(code, theme)
    except DiagramError as first_error:
        # ---- auto-repair loop: feed the error back to Gemini once ------
        try:
            fixed = ai.repair_mermaid(code, str(first_error))
        except ai.AIError:
            raise DiagramError(str(first_error)) from None
        try:
            png, svg = render_mermaid(fixed, theme)
            code = fixed                       # repaired successfully
        except DiagramError as second_error:
            raise DiagramError(
                f"Rendering failed even after AI repair: {second_error}"
            ) from second_error

    label = f"{visual_type}: {topic[:34]}"
    return {"kind": "mermaid", "label": label,
            "source": code, "png": png, "svg": svg}


def slugify(text: str) -> str:
    """Filesystem-safe fragment for download filenames."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:32] or "beefriendly_visual"


# ----------------------------------------------------------------------
# ✨ Pro engine — HTML/CSS infographics screenshot to PNG via Edge/Chrome
# ----------------------------------------------------------------------
def find_browser():
    """Locate a Chromium browser for headless screenshots (Edge ships
    preinstalled on every Windows 10/11 PC)."""
    candidates = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def html_to_png(html: str, width: int = 1400, height: int = 1000) -> bytes:
    """
    Screenshot an HTML string to PNG using headless Edge/Chrome.

    Robustness notes (learned the hard way):
    - A UNIQUE --user-data-dir is mandatory. Without it, msedge/chrome
      attach to the user's already-running browser and never screenshot.
    - --run-all-compositor-stages-before-draw forces a full paint before
      capture; --virtual-time-budget lets fonts/layout settle.
    - If the result is missing or suspiciously tiny (≈ pure white), we
      retry once with legacy --headless and a longer budget.
    """
    import subprocess
    import tempfile
    from pathlib import Path

    browser = find_browser()
    if not browser:
        raise DiagramError(
            "Pro engine needs Microsoft Edge or Chrome installed "
            "(not found). Use the Standard engine instead."
        )

    tmpdir = tempfile.mkdtemp(prefix="beefriendly_")
    html_file = os.path.join(tmpdir, "visual.html")
    png_file = os.path.join(tmpdir, "visual.png")
    profile_dir = os.path.join(tmpdir, "profile")
    with open(html_file, "w", encoding="utf-8") as fh:
        fh.write(html)

    def shoot(headless_mode: str, budget: int) -> None:
        cmd = [
            browser,
            headless_mode,
            f"--user-data-dir={profile_dir}",   # unique → no attach-to-existing
            "--disable-gpu",
            "--no-sandbox",
            "--disable-extensions",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-background-networking",
            "--hide-scrollbars",
            f"--screenshot={png_file}",
            f"--window-size={width},{height}",
            "--default-background-color=FFFFFFFF",
            "--run-all-compositor-stages-before-draw",
            f"--virtual-time-budget={budget}",
            Path(html_file).as_uri(),
        ]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
        except subprocess.TimeoutExpired as exc:
            raise DiagramError("Browser screenshot timed out.") from exc

    # Attempt 1 — modern headless.
    try:
        shoot("--headless=new", budget=12000)
    except DiagramError:
        pass

    def is_suspicious() -> bool:
        """Missing file or tiny file (a blank white 1400x1000 PNG
        compresses to only a few KB)."""
        return (not os.path.exists(png_file)
                or os.path.getsize(png_file) < 12_000)

    # Attempt 2 — legacy headless fallback for older/quirky builds.
    if is_suspicious():
        try:
            shoot("--headless", budget=20000)
        except DiagramError:
            pass

    if not os.path.exists(png_file):
        raise DiagramError(
            "Browser did not produce a screenshot. Try switching to "
            "the Standard engine, or update Microsoft Edge."
        )

    with open(png_file, "rb") as fh:
        data = fh.read()

    # Clean temp files (keep tmpdir itself — harmless).
    for f in (html_file, png_file):
        try:
            os.remove(f)
        except OSError:
            pass

    if len(data) < 12_000:
        # Both attempts produced a near-blank image — surface a clear error
        # instead of showing the user an empty picture.
        raise DiagramError(
            "The rendered infographic came out blank (browser issue). "
            "Please update Microsoft Edge, or switch to the Standard "
            "engine for this visual."
        )
    return data


def create_pro_visual(visual_type: str, topic: str,
                      direction: str = "TD") -> dict:
    """
    Napkin-style pipeline: Gemini writes styled HTML → headless browser
    screenshots it → professional PNG.
    """
    instruction = VISUALS[visual_type]["instruction"].replace("{dir}", direction)
    layout_hint = (
        "Lay the content out left-to-right in horizontal flow."
        if direction == "LR" else
        "Lay the content out top-to-bottom in vertical flow."
    )
    html = ai.generate_html_visual(f"{instruction}\n{layout_hint}", topic)
    png = html_to_png(html)
    label = f"✨ {visual_type}: {topic[:34]}"
    return {"kind": "pro", "label": label,
            "source": html, "png": png, "svg": None}
