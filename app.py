"""
BeeFriendly — AI-Powered Diagram & Visual Generator
====================================================
Sign in → type any topic → get presentation-ready diagrams AND
AI-generated images. Users stored in SQLite with hashed passwords.

Run with:
    streamlit run app.py
"""

import base64
import os
import pathlib

import streamlit as st

import ai
import auth
import diagrams
from diagrams import EXAMPLES, VISUALS

# ----------------------------------------------------------------------
# Brand assets (permanent logo files shipped with the project)
# ----------------------------------------------------------------------
BASE_DIR = pathlib.Path(__file__).parent
LOGO_PNG = BASE_DIR / "assets" / "logo.png"
LOGO_SVG = BASE_DIR / "assets" / "logo.svg"

HERO_LOGO_B64 = ""
if LOGO_SVG.exists():
    HERO_LOGO_B64 = base64.b64encode(LOGO_SVG.read_bytes()).decode("ascii")

# ----------------------------------------------------------------------
# Page setup + professional styling (pink & blue bee-branded)
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="BeeFriendly | AI Visual Generator",
    page_icon=str(LOGO_PNG) if LOGO_PNG.exists() else "🐝",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Segoe UI', sans-serif;
}
.block-container { padding-top: 1.2rem; max-width: 1200px; }

/* Hero banner — pink & blue */
.bf-hero {
    background: linear-gradient(135deg, #EC4899 0%, #A855F7 48%, #3B82F6 100%);
    border-radius: 18px;
    padding: 1.8rem 2.4rem;
    color: #FFFFFF;
    margin-bottom: 1.4rem;
    box-shadow: 0 10px 30px rgba(236, 72, 153, .28);
}
.bf-hero h1 { font-size: 2rem; font-weight: 800; margin: 0 0 .35rem 0; }
.bf-hero p  { font-size: 1rem; opacity: .95; margin: 0; }
.bf-chip {
    display: inline-block; margin: .85rem .45rem 0 0;
    background: rgba(255,255,255,.16); border: 1px solid rgba(255,255,255,.32);
    padding: .26rem .8rem; border-radius: 999px;
    font-size: .78rem; font-weight: 600;
}

/* 🐝 Loading splash (bee + progress bar) */
#bf-loader {
    position: fixed; inset: 0; z-index: 999999;
    display: flex; flex-direction: column; align-items: center;
    justify-content: center; gap: 16px;
    background: rgba(255, 243, 248, .97);
    backdrop-filter: blur(8px);
    pointer-events: none;
    animation: bfFadeOut .7s ease 2s forwards;
}
#bf-loader img { width: 112px; height: auto; animation: bfFly 1.15s ease-in-out infinite; }
.bf-load-text {
    font-family: 'Inter', sans-serif; font-weight: 800;
    color: #9D174D; font-size: 1.05rem;
}
.bf-loadbar {
    width: 260px; height: 10px; border-radius: 99px;
    background: #FBCFE8; overflow: hidden;
}
.bf-loadbar > div {
    height: 100%; width: 45%; border-radius: 99px;
    background: linear-gradient(90deg, #EC4899, #3B82F6);
    animation: bfSlide 1.5s ease-in-out infinite;
}
@keyframes bfFly {
    0%, 100% { transform: translateY(0) rotate(-5deg); }
    50%      { transform: translateY(-14px) rotate(6deg); }
}
@keyframes bfSlide {
    from { margin-left: -45%; }
    to   { margin-left: 100%; }
}
@keyframes bfFadeOut { to { opacity: 0; visibility: hidden; } }

/* Auth card */
.bf-auth {
    max-width: 430px; margin: 1.5rem auto 0 auto;
    background: #FFFFFF; border-radius: 18px;
    border: 1px solid #F9C7DE; padding: .6rem 1.4rem 1.4rem 1.4rem;
    box-shadow: 0 12px 34px rgba(236, 72, 153, .12);
}

/* Buttons */
.stButton > button { border-radius: 12px; font-weight: 700; }
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #EC4899, #3B82F6);
    border: none; color: #fff;
    box-shadow: 0 6px 18px rgba(236, 72, 153, .35);
}
.stButton > button[kind="primary"]:hover { filter: brightness(1.07); }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0F172A 0%, #172554 100%);
}
[data-testid="stSidebar"] * { color: #E2E8F0 !important; }
[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.15) !important; }
[data-testid="stSidebar"] input, [data-testid="stSidebar"] [data-baseweb="select"] > div {
    background: #1E293B !important; color: #fff !important;
    border: 1px solid #334155 !important;
}

/* Inputs & cards */
div[data-testid="stTextAreaTextarea"], div[data-testid="stTextInput"] input,
div[data-testid="stSelectbox"] > div > div {
    border-radius: 10px;
}
div[data-testid="stExpander"] {
    background: #FFFFFF; border-radius: 14px;
    border: 1px solid #F9C7DE; box-shadow: 0 5px 14px rgba(15,23,42,.06);
}
div[data-testid="stExpander"] summary { font-weight: 600; color: #0F172A; }

.hs-footer {
    text-align: center; color: #9D6B8A; font-size: .8rem;
    padding: 1.4rem 0 .4rem 0;
}

/* Professional section headers */
.bf-kicker {
    font-size: .74rem; font-weight: 800; letter-spacing: .16em;
    text-transform: uppercase; color: #94A3B8; margin: 0 0 .45rem 0;
}
.bf-h {
    display: flex; align-items: center; gap: .55rem;
    font-size: 1.06rem; font-weight: 800; color: #0F172A;
    letter-spacing: -.01em; margin: 0 0 .85rem 0;
}
.bf-h::before {
    content: ""; width: 5px; height: 1.05rem; border-radius: 99px;
    background: linear-gradient(180deg, #EC4899, #3B82F6);
    flex: none;
}
[data-testid="stSidebar"] .bf-h { color: #F1F5F9; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# 🐝 Loading splash — cute bee + progress bar, auto-fades after ~2s
# ----------------------------------------------------------------------
LOADER_HTML = f"""
<div id="bf-loader">
    <img src="data:image/svg+xml;base64,{HERO_LOGO_B64}" alt="BeeFriendly bee"/>
    <div class="bf-loader-text">BeeFriendly</div>
    <div class="bf-loadbar"><div></div></div>
</div>
"""
st.markdown(LOADER_HTML, unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
if "bf_user" not in st.session_state:
    st.session_state["bf_user"] = None


def load_api_key():
    """Priority: secrets.toml → environment variable → manual input."""
    try:
        secret = st.secrets.get("GEMINI_API_KEY", "")
        if secret and str(secret).strip():
            return str(secret).strip(), "secrets"
    except FileNotFoundError:
        pass
    env = os.environ.get("GEMINI_API_KEY", "")
    if env.strip():
        return env.strip(), "env"
    return "", ""


API_KEY, KEY_SOURCE = load_api_key()


# ----------------------------------------------------------------------
# 🔐 Auth view (shown when nobody is signed in)
# ----------------------------------------------------------------------
def render_auth_view() -> None:
    if LOGO_PNG.exists():
        lc1, lc2, lc3 = st.columns([1.2, 1, 1.2])
        with lc2:
            st.image(str(LOGO_PNG), use_container_width=True)

    st.markdown(
        f"""
        <div class="bf-hero">
            {f"<img src='data:image/svg+xml;base64,{HERO_LOGO_B64}' "
             f"style='width:74px;float:left;margin-right:1rem;'/>" if HERO_LOGO_B64 else ""}
            <h1>BeeFriendly</h1>
            <p style="clear:none">Pollinate your ideas — turn plain English into beautiful
            diagrams & images for your presentations.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="bf-auth">', unsafe_allow_html=True)

    tab_login, tab_signup = st.tabs(["🔑 Log In", "📝 Sign Up"])

    with tab_login:
        with st.form("login_form", clear_on_submit=False):
            lu = st.text_input("Username", key="lu")
            lp = st.text_input("Password", type="password", key="lp")
            ok = st.form_submit_button("Log In", type="primary",
                                       use_container_width=True)
        if ok:
            user = auth.authenticate(lu, lp)
            if user:
                st.session_state["bf_user"] = user
                st.rerun()
            else:
                st.error("Wrong username or password. Try again.")

    with tab_signup:
        with st.form("signup_form", clear_on_submit=False):
            su = st.text_input("Choose a username", key="su")
            se = st.text_input("Email (optional)", key="se")
            sp = st.text_input("Password (min 6 chars)", type="password",
                               key="sp")
            sc = st.text_input("Confirm password", type="password", key="sc")
            go = st.form_submit_button("Create Account", type="primary",
                                       use_container_width=True)
        if go:
            if sp != sc:
                st.error("Passwords do not match.")
            else:
                new_user, err = auth.create_user(su, sp, se)
                if new_user:
                    st.session_state["bf_user"] = new_user
                    st.rerun()
                else:
                    st.error(err)

    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='hs-footer'>🐝 BeeFriendly · your ideas deserve "
        "beautiful visuals.</div>",
        unsafe_allow_html=True,
    )


# Gate the whole app behind authentication.
if not st.session_state["bf_user"]:
    render_auth_view()
    st.stop()

CURRENT_USER = st.session_state["bf_user"]

# ----------------------------------------------------------------------
# Sidebar — account, API key, style controls, gallery
# ----------------------------------------------------------------------
with st.sidebar:
    head_l, head_r = st.columns([1, 2.6])
    with head_l:
        if LOGO_PNG.exists():
            st.image(str(LOGO_PNG), use_container_width=True)
        else:
            st.markdown("<h2>🐝</h2>", unsafe_allow_html=True)
    with head_r:
        st.markdown(
            "<h3 style='margin-bottom:0'>BeeFriendly</h3>"
            "<p style='font-size:.8rem;opacity:.75;margin-top:0'>AI Visual Studio</p>",
            unsafe_allow_html=True,
        )

    st.success(f"Signed in as **{CURRENT_USER}**")
    if st.button("Log Out", use_container_width=True):
        st.session_state["bf_user"] = None
        st.rerun()

    st.divider()

    if API_KEY:
        note = "from secrets.toml 🔒" if KEY_SOURCE == "secrets" else "from environment 🔒"
        st.caption(f"API key active ({note})")
    else:
        st.warning("No API key found — enter it below")
        manual_key = st.text_input("Gemini API Key", type="password",
                                   help="https://aistudio.google.com/apikey")
        if manual_key.strip():
            os.environ["GEMINI_API_KEY"] = manual_key.strip()
            API_KEY = manual_key.strip()
            st.rerun()
        st.caption("Tip: paste it into `.streamlit/secrets.toml` once to "
                   "never type it again.")

    st.divider()
    theme_name = st.selectbox(
        "Diagram Theme",
        list(diagrams.PALETTES.keys()) + ["Dark", "Custom…"],
        index=0)

    theme = theme_name
    if theme_name == "Custom…":
        st.caption("Design your own palette")
        cc1, cc2 = st.columns(2)
        cust_fill = cc1.color_picker("Card fill", "#C7D2FE")
        cust_border = cc2.color_picker("Border", "#4F46E5")
        cust_line = cc1.color_picker("Lines / arrows", "#3B82F6")
        cust_text = cc2.color_picker("Text", "#111827")

        import json as _json
        theme = {
            "background": "#FFFFFF", "fontFamily": "Inter, Segoe UI, sans-serif",
            "primaryColor": cust_fill, "primaryBorderColor": cust_border,
            "primaryTextColor": cust_text,
            "secondaryColor": cust_fill, "secondaryBorderColor": cust_border,
            "secondaryTextColor": cust_text,
            "tertiaryColor": "#FFFFFF", "tertiaryBorderColor": cust_border,
            "tertiaryTextColor": cust_text,
            "lineColor": cust_line, "textColor": cust_text,
            "mainBkg": cust_fill, "nodeBorder": cust_border,
            "clusterBkg": cust_fill, "clusterBorder": cust_border,
            "titleColor": cust_text,
            "edgeLabelBackground": cust_fill,
            "noteBkgColor": cust_line, "noteBorderColor": cust_line,
            "fontSize": "16px",
        }
        _json.dumps(theme)  # sanity check

    direction = st.radio("Layout Direction",
                         ["Top-down", "Left-right"], horizontal=True)
    engine = st.radio(
        "Design Engine",
        ["Standard", "Pro Infographic"],
        index=1,
        help="Pro = Napkin-style HTML/CSS designs rendered as PNG "
             "(coloured cards, icons, arrows). Standard = classic Mermaid.",
        horizontal=True,
    )

    st.divider()
    st.markdown('<div class="bf-kicker">Session Gallery</div>',
                unsafe_allow_html=True)

    gallery = st.session_state.get("sf_gallery", [])

    if gallery:
        pick = st.selectbox("Reopen a visual",
                            ["—"] + [g["label"] for g in gallery])
        if pick != "—" and st.session_state.get("sf_current", {}).get("label") != pick:
            for g in gallery:
                if g["label"] == pick:
                    st.session_state["sf_current"] = g
                    st.rerun()

        thumbs = st.columns(min(3, len(gallery)))
        for i, g in enumerate(gallery[:6]):
            with thumbs[i % 3]:
                st.image(g["png"], use_container_width=True)
                if st.button("Open", key=f"g_{i}_{abs(hash(g['label'])) % 99999}",
                             use_container_width=True):
                    st.session_state["sf_current"] = g
                    st.rerun()
    else:
        st.caption("Diagrams you generate will appear here.")

    st.divider()
    st.caption("Streamlit · Gemini · Mermaid.js · Image AI")

# ----------------------------------------------------------------------
# Hero
# ----------------------------------------------------------------------
st.markdown(
    f"""
    <div class="bf-hero">
        {f"<img src='data:image/svg+xml;base64,{HERO_LOGO_B64}' "
         f"style='width:78px;float:left;margin-right:1.2rem;'/>" if HERO_LOGO_B64 else ""}
        <h1>🐝 BeeFriendly — AI Visual Studio</h1>
        <p>Welcome back, <b>{CURRENT_USER}</b>! Diagrams from Mermaid or
        full AI-generated images — all in one place.</p>
        <span class="bf-chip">14 visual types</span>
        <span class="bf-chip">AI image generation</span>
        <span class="bf-chip">Editable code</span>
        <span class="bf-chip">PNG / SVG export</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ======================================================================
# TABS — Diagram Studio | AI Image Studio
# ======================================================================
tab_diag, tab_img = st.tabs(["Diagram Studio", "AI Image Studio"])

# ----------------------------------------------------------------------
# TAB 1 — Diagram Studio (controls left, preview right)
# ----------------------------------------------------------------------
with tab_diag:
    left, right = st.columns([5, 7])

    with left:
        st.markdown('<div class="bf-h">Design Controls</div>',
                    unsafe_allow_html=True)

        visual_type = st.selectbox("Visual Type", list(VISUALS.keys()))
        topic = st.text_input("Topic", placeholder=EXAMPLES[visual_type])
        st.caption(f"Example: **{EXAMPLES[visual_type]}**")

        ref_file = st.file_uploader(
            "Reference image (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            help="Upload a diagram/infographic you like — Gemini studies "
                 "its structure, sections & colours, then recreates "
                 "something similar for your topic.",
        )
        if ref_file is not None:
            st.caption(f"Reference attached: **{ref_file.name}**")

        generate_btn = st.button("Generate Visual",
                                 type="primary", use_container_width=True)

        st.divider()

        current = st.session_state.get("sf_current")

        if current and current["kind"] == "mermaid":
            with st.expander("🛠️ Advanced — edit diagram code"):
                edited = st.text_area("Mermaid source", value=current["source"],
                                      height=240)
                if st.button("🔄 Re-render edited code", use_container_width=True):
                    try:
                        png, svg = diagrams.render_mermaid(edited, theme)
                        updated = {"kind": "mermaid", "label": current["label"],
                                   "source": edited, "png": png, "svg": svg}
                        st.session_state["sf_current"] = updated
                        gallery.insert(0, updated)
                        st.session_state["sf_gallery"] = gallery[:12]
                        st.success("Updated!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Could not render edited code: {exc}")

    with right:
        st.markdown('<div class="bf-h">Preview</div>',
                    unsafe_allow_html=True)

        run = generate_btn
        if run:
            problems = []
            if not API_KEY:
                problems.append("Add your Gemini API key first (sidebar).")
            if not topic.strip():
                problems.append(f"Type a topic, e.g. “{EXAMPLES[visual_type]}”.")
            if problems:
                for p in problems:
                    st.error(p)
                st.stop()

            ai.configure(API_KEY)
            dir_code = "LR" if direction == "Left-right" else "TD"

            enriched_topic = topic.strip()
            if ref_file is not None:
                try:
                    with st.spinner("Studying your reference image…"):
                        ref_desc = ai.describe_reference(
                            API_KEY, ref_file.getvalue(),
                            mime=ref_file.type or "image/png")
                    enriched_topic += (
                        "\n\nREFERENCE BRIEF — recreate a visual with a "
                        f"similar structure, sections and colour mood:\n"
                        f"{ref_desc}"
                    )
                except ai.AIError as exc:
                    st.warning(
                        f"Couldn't analyse the reference image ({exc}). "
                        "Continuing without it."
                    )

            try:
                if engine == "Pro Infographic":
                    with st.spinner("Designing a pro infographic…"):
                        result = diagrams.create_pro_visual(
                            visual_type, enriched_topic, direction=dir_code)
                else:
                    with st.spinner("Designing your visual…"):
                        result = diagrams.create_visual(
                            visual_type, enriched_topic,
                            direction=dir_code, theme=theme)
                st.session_state["sf_current"] = result
                gallery.insert(0, result)
                st.session_state["sf_gallery"] = gallery[:12]
                current = result
            except ai.AIError as exc:
                st.error(f"🤖 AI error: {exc}")
                st.stop()
            except diagrams.DiagramError as exc:
                st.error(f"📐 Rendering failed: {exc}")
                st.stop()

        if current:
            st.markdown(f"**{current['label']}**")

            inner_left, inner_right = st.columns([1, 5])
            with inner_right:
                st.image(current["png"], use_container_width=True)

            dl_png, dl_svg, _ = st.columns([1.2, 1.2, 3])
            dl_png.download_button(
                "Download PNG", data=current["png"],
                file_name=f"{diagrams.slugify(topic or current['label'])}.png",
                mime="image/png",
            )
            if current.get("svg"):
                dl_svg.download_button(
                    "Download SVG", data=current["svg"],
                    file_name=f"{diagrams.slugify(topic or current['label'])}.svg",
                    mime="image/svg+xml",
                )

            with st.expander("View source "
                             f"({{'mermaid' if current['kind'] == 'mermaid' else 'markdown' if current['kind'] == 'table' else 'HTML'}})"):
                st.code(current["source"],
                        language=("mermaid" if current["kind"] == "mermaid"
                                  else "markdown" if current["kind"] == "table"
                                  else "html"))
        elif not run:
            st.info("Pick a visual type, type any topic and hit "
                    "**Generate Visual**.\n\nTry: *“water cycle for class 8”* "
                    "as a Cycle diagram.")

# ----------------------------------------------------------------------
# TAB 2 — AI Image Studio (text → image generation)
# ----------------------------------------------------------------------
IMAGE_STYLES = {
    "As described": "",
    "Photorealistic": "photorealistic, highly detailed, professional photo",
    "Digital Illustration": "modern digital illustration, vibrant colours, clean composition",
    "Cute Cartoon": "cute kawaii cartoon style, soft pastel colours, adorable",
    "3D Render": "polished 3D render, soft studio lighting, clay morphism",
    "Watercolour": "delicate watercolour painting, soft edges, artistic paper texture",
    "Flat Vector": "flat vector design, minimal geometric shapes, modern infographic style",
}
WHITE_BG_SUFFIX = "Plain pure white background."

with tab_img:
    img_left, img_right = st.columns([5, 7])

    with img_left:
        st.markdown('<div class="bf-h">Describe Your Image</div>',
                    unsafe_allow_html=True)
        img_prompt = st.text_area(
            "What should BeeFriendly draw?",
            height=120,
            placeholder="e.g. a friendly mascot bee holding a paintbrush\n"
                        "e.g. poster showing students studying together\n"
                        "e.g. futuristic classroom of the year 2030",
        )
        img_style = st.selectbox("Art Style", list(IMAGE_STYLES.keys()))

        img_ref = st.file_uploader(
            "Reference image (optional)",
            type=["png", "jpg", "jpeg", "webp"],
            key="img_ref",
            help="Attach a picture whose style/composition you love — "
                 "Gemini will paint your prompt in a similar vibe.",
        )
        if img_ref is not None:
            st.caption(f"Style reference: **{img_ref.name}**")

        img_btn = st.button("Generate Image", type="primary",
                            use_container_width=True)

        st.caption("Tip: describe subject + mood + details. "
                   "The white background is added automatically.")

    with img_right:
        st.markdown('<div class="bf-h">Result</div>',
                    unsafe_allow_html=True)

        last_img = st.session_state.get("sf_img")

        if img_btn:
            problems = []
            if not API_KEY:
                problems.append("Add your Gemini API key first (sidebar).")
            if not img_prompt.strip():
                problems.append("Describe the image you want.")
            if problems:
                for p in problems:
                    st.error(p)
                st.stop()

            style_bits = IMAGE_STYLES[img_style]
            final_prompt = f"{img_prompt.strip()}. {style_bits}. {WHITE_BG_SUFFIX}"
            if img_ref is not None:
                final_prompt += (" Match the artistic style, colour mood and "
                                 "composition of the attached reference image.")

            try:
                with st.spinner("Painting your image…"):
                    png = ai.generate_image(
                        API_KEY, final_prompt,
                        ref_bytes=img_ref.getvalue() if img_ref else None,
                        ref_mime=(img_ref.type or "image/png") if img_ref
                        else "image/png",
                    )
                last_img = {"png": png, "prompt": img_prompt.strip()}
                st.session_state["sf_img"] = last_img
            except ai.AIError as exc:
                st.error(f"🤖 Image generation failed: {exc}")
                st.stop()

        if last_img:
            inner_l, inner_r = st.columns([1, 5])
            with inner_r:
                st.image(last_img["png"], use_container_width=True)
            st.download_button(
                "Download Image",
                data=last_img["png"],
                file_name=f"{diagrams.slugify(last_img['prompt'])}.png",
                mime="image/png",
            )
            with st.expander("Prompt used"):
                st.code(last_img["prompt"])
        elif not img_btn:
            st.info("Describe anything you can imagine and hit "
                    "**Generate Image**.\n\nTry: *“a bee teaching students "
                    "in a colourful classroom”*.")

st.markdown(
    "<div class='hs-footer'>🐝 BeeFriendly · pollinate your ideas — type it, "
    "see it, paste it into your slides.</div>",
    unsafe_allow_html=True,
)
