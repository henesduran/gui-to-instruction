import json
import os
from pathlib import Path

import streamlit as st
from PIL import Image

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GUI → Instruction Pipeline",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Gemini setup ───────────────────────────────────────────────────────────────
try:
    from google import genai
    from google.genai import types as genai_types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False

API_KEY = os.getenv("GEMINI_API_KEY", "")
LIVE_INFERENCE = GENAI_AVAILABLE and bool(API_KEY)

SYSTEM_PROMPT = """\
You are a GUI interaction analyzer. Your task is to generate a structured JSON description of a user action based on a screenshot and a bounding box, strictly distinguishing between standard interactions, dropdowns, and date pickers.

INPUTS:
1. A screenshot with a red bounding box marking the element.
2. An action JSON (e.g., {"action": "click"} or {"action": "entry", "argument": "VAL"}).

GOAL:
Output ONLY a valid JSON object with the following fields:
- "instruction": The natural language description of the single atomic action.
- "compiled_instruction": The final compiled description if the action completes a sequence. Otherwise, null.
- "intent": The categorical intent of the action.

INTENT CATEGORIZATION LOGIC:
1. "openDatePicker": User clicks a date field to open the calendar popup.
2. "increaseMonth": User clicks the navigation icon (e.g., right arrow) inside the calendar.
3. "selectDay": User clicks a specific day number inside an open calendar.
4. "expandDropDown": User clicks the trigger/header of a dropdown menu.
5. "selectFromDropDown": User clicks a specific item/option inside an open dropdown list.
6. "click": Standard button/link click not related to dropdowns or date pickers.
7. "entry": User types text into an input field.

INSTRUCTION TEMPLATES:
- click / expandDropDown / openDatePicker / increaseMonth: "Click on <label>."
- selectFromDropDown: "Click on <label>." + compiled: "Enter <option> as <field_name>."
- selectDay: "Click on <day>." + compiled: "Enter <day> <month> <year> as <field_name>."
- entry: "Enter <argument> as the <label>."

CONTEXT RULE — Execute this for EVERY instruction before writing it:
1. SCAN: Look across the entire visible screenshot for any other element sharing the same label text as the bounding-box element.
2. DECIDE:
   - Duplicates found → identify the nearest enclosing container that uniquely locates THIS element: a card title, panel heading, form section label, column header, or group name visible directly above or beside the element. Use that text as <context> and prepend: "Within the context of <context>, ..."
   - No duplicates → write the instruction without any context prefix.
3. VERIFY: The <context> text must be literally visible on the screen. Do not invent or infer section names.
LABEL RULES: Use exact visible text. Convert ALL CAPS to Natural Case. Do not invent labels.
STRICT OUTPUT RULES: Return ONLY JSON. No markdown. No explanations.
"""


_genai_client = None


def _get_genai_client():
    global _genai_client
    if _genai_client is None and LIVE_INFERENCE:
        _genai_client = genai.Client(api_key=API_KEY)
    return _genai_client


def call_gemini(image_bytes: bytes, action_data: dict) -> dict:
    client = _get_genai_client()
    image_part = genai_types.Part.from_bytes(data=image_bytes, mime_type="image/png")
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=genai_types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
        ),
        contents=[f"Action Data: {json.dumps(action_data)}", image_part],
    )
    return json.loads(response.text)


# ── Curated examples ───────────────────────────────────────────────────────────
# Each entry: {phase, intent, description, screenshot_path, action, output}
EXAMPLES = [
    {
        "phase": "Phase I",
        "intent": "click (with context)",
        "description": "Same button label on multiple product cards — model identifies the product title as disambiguating context.",
        "screenshot": "examples/action1.png",
        "action": {"action": "click", "type": "click"},
        "output": {
            "instruction": "Within the context of Rotring Jel Kalem 0.7 mm, Siyah - 2114436, click on Sepete ekle.",
            "intent": "click",
        },
    },
    {
        "phase": "Phase I",
        "intent": "click (no context needed)",
        "description": "Unique button label — no context phrase required.",
        "screenshot": "examples/action6.png",
        "action": {"action": "click", "type": "click"},
        "output": {"instruction": "Click on Order Now.", "intent": "click"},
    },
    {
        "phase": "Phase I",
        "intent": "entry (with context)",
        "description": "Same field label in multiple sections — section title used as context.",
        "screenshot": "examples/action21.png",
        "action": {"action": "entry", "argument": "Istanbul"},
        "output": {
            "instruction": "Within the context of Shipping Address, enter Istanbul as the City.",
            "intent": "entry",
        },
    },
    {
        "phase": "Phase I",
        "intent": "entry (no context)",
        "description": "Unique field label — direct entry instruction.",
        "screenshot": "examples/action20.png",
        "action": {"action": "entry", "argument": "PROJ 201"},
        "output": {"instruction": "Enter PROJ 201 as the Search Courses.", "intent": "entry"},
    },
    {
        "phase": "Phase I",
        "intent": "entry (ALL CAPS normalization)",
        "description": "Label appears as ALL CAPS on screen — model normalizes to Natural Case.",
        "screenshot": "examples/action19.png",
        "action": {"action": "entry", "argument": "120,000"},
        "output": {"instruction": "Enter 120,000 as the Tutar.", "intent": "entry"},
    },
    {
        "phase": "Phase I",
        "intent": "entry (no context)",
        "description": "Unique numeric field — minimal action data, correct label extraction.",
        "screenshot": "examples/action10.png",
        "action": {"action": "entry", "argument": "1000"},
        "output": {"instruction": "Enter 1000 as the From.", "intent": "entry"},
    },
]

INTENT_COLORS = {
    "click": "#4A90D9",
    "entry": "#7BB86F",
    "expandDropDown": "#E07B39",
    "selectFromDropDown": "#E07B39",
    "openDatePicker": "#9B59B6",
    "increaseMonth": "#9B59B6",
    "selectDay": "#9B59B6",
}


def intent_badge(intent: str) -> str:
    color = INTENT_COLORS.get(intent, "#888888")
    return f'<span style="background:{color};color:white;padding:2px 10px;border-radius:12px;font-size:0.8em;font-weight:600">{intent}</span>'


# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🖥️ GUI → Instruction")
    st.markdown(
        "Converts GUI screenshots + action metadata into **structured natural language instructions** "
        "using **Gemini 2.5 Flash Lite**."
    )
    st.divider()
    st.markdown("**Results**")
    col_a, col_b = st.columns(2)
    col_a.metric("Samples", "70")
    col_b.metric("Accuracy", "~80%")
    col_a.metric("Phases", "3")
    col_b.metric("Intents", "7")
    st.divider()
    st.markdown(
        "**Intent types**\n"
        "- `click` · `entry`\n"
        "- `expandDropDown`\n"
        "- `selectFromDropDown`\n"
        "- `openDatePicker`\n"
        "- `increaseMonth`\n"
        "- `selectDay`"
    )
    st.divider()
    if LIVE_INFERENCE:
        st.success("Live inference enabled", icon="✅")
    else:
        st.info("Gallery mode (no API key)", icon="ℹ️")
    st.markdown("[GitHub](https://github.com/henesduran/gui-instruction)", unsafe_allow_html=True)


# ── Main ───────────────────────────────────────────────────────────────────────
st.title("GUI → Natural Language Instruction Pipeline")
st.caption(
    "Upload a GUI screenshot with a bounding box marking the interacted element. "
    "The model generates a structured instruction ready for downstream test automation."
)

tab_demo, tab_gallery, tab_metrics, tab_about = st.tabs(["▶ Live Demo", "📂 Results Gallery", "📊 Metrics", "ℹ About"])


# ── Tab 1: Live Demo ───────────────────────────────────────────────────────────
with tab_demo:
    if not LIVE_INFERENCE:
        st.warning(
            "Live inference requires a `GEMINI_API_KEY`. "
            "Set it as an environment variable or Hugging Face Space Secret. "
            "Browse pre-computed results in the **Results Gallery** tab.",
            icon="⚠️",
        )

    col_left, col_right = st.columns([1, 1], gap="large")

    with col_left:
        st.subheader("Input")
        uploaded = st.file_uploader(
            "Screenshot (PNG/JPG) with bounding box marking the element",
            type=["png", "jpg", "jpeg"],
            disabled=not LIVE_INFERENCE,
        )
        if uploaded is not None:
            st.session_state["file_bytes"] = uploaded.getvalue()

        file_bytes = st.session_state.get("file_bytes")

        action_type = st.selectbox(
            "Action type",
            ["click", "entry"],
            disabled=not LIVE_INFERENCE,
            help="'click' for any button/link/calendar/dropdown. 'entry' when the user typed text.",
        )

        argument = ""
        if action_type == "entry":
            argument = st.text_input(
                "Typed value",
                placeholder="e.g. Istanbul",
                disabled=not LIVE_INFERENCE,
            )

        run_btn = st.button(
            "Generate Instruction",
            type="primary",
            disabled=not LIVE_INFERENCE or file_bytes is None,
        )

    with col_right:
        st.subheader("Output")

        if run_btn and file_bytes:
            action_data: dict = {"action": action_type}
            if argument:
                action_data["argument"] = argument

            with st.spinner("Calling Gemini 2.5 Flash Lite…"):
                try:
                    result = call_gemini(file_bytes, action_data)
                    intent = result.get("intent", "")
                    st.markdown(
                        f"**Intent:** {intent_badge(intent)}",
                        unsafe_allow_html=True,
                    )
                    st.markdown("**Instruction:**")
                    st.info(result.get("instruction", ""))
                    compiled = result.get("compiled_instruction")
                    if compiled:
                        st.markdown("**Compiled instruction** *(full sequence summary)*:")
                        st.success(compiled)
                    with st.expander("Raw JSON"):
                        st.json(result)
                except Exception as exc:
                    st.error(f"API error: {exc}")
        else:
            st.markdown(
                '<div style="color:#888;margin-top:2rem">Output will appear here after inference.</div>',
                unsafe_allow_html=True,
            )

    if file_bytes:
        with col_left:
            st.image(file_bytes, caption="Uploaded screenshot", use_container_width=True)


# ── Tab 2: Results Gallery ─────────────────────────────────────────────────────
with tab_gallery:
    st.subheader("Pre-computed Results")
    st.caption(f"{len(EXAMPLES)} curated examples from the 70-sample benchmark dataset.")

    phase_filter = st.selectbox("Filter by phase", ["All", "Phase I"])

    filtered = [e for e in EXAMPLES if phase_filter == "All" or e["phase"] == phase_filter]

    for i, ex in enumerate(filtered):
        with st.container(border=True):
            col1, col2 = st.columns([1, 1], gap="large")

            with col1:
                ss_path = Path(ex["screenshot"])
                if ss_path.exists():
                    st.image(str(ss_path), use_container_width=True)
                else:
                    st.markdown(
                        '<div style="background:#f7f7f7;border:1px dashed #ccc;padding:3rem 1rem;'
                        'text-align:center;border-radius:8px;color:#999;font-size:0.85em">'
                        "📷 Screenshot not available in this environment"
                        "</div>",
                        unsafe_allow_html=True,
                    )

            with col2:
                phase_badge = (
                    f'<span style="background:#e8e8e8;padding:2px 8px;border-radius:8px;font-size:0.75em">'
                    f'{ex["phase"]}</span>'
                )
                st.markdown(
                    f'{phase_badge} &nbsp; {intent_badge(ex["output"]["intent"])}',
                    unsafe_allow_html=True,
                )
                st.markdown(f"**{ex['intent']}**")
                st.caption(ex["description"])

                st.markdown("**Action input:**")
                st.code(json.dumps(ex["action"], ensure_ascii=False), language="json")

                out = ex["output"]
                st.markdown("**Instruction:**")
                st.info(out["instruction"])

                compiled = out.get("compiled_instruction")
                if compiled:
                    st.markdown("**Compiled instruction:**")
                    st.success(compiled)

        if i < len(filtered) - 1:
            st.markdown("---")


# ── Tab 3: Metrics ─────────────────────────────────────────────────────────────
with tab_metrics:
    st.subheader("Evaluation Metrics — Phase I")
    st.caption("Computed from output.json · 25 samples · Phase I (click + entry)")

    from guiinstruct.eval import evaluate

    OUTPUT_PATH = "output.json"
    if not os.path.exists(OUTPUT_PATH):
        st.warning("output.json not found. Run the pipeline first.")
    else:
        m = evaluate(OUTPUT_PATH)
        n = m["total_samples"]

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Samples", n)
        col2.metric(
            "Context Disambiguation",
            f"{m['context_disambiguation']['count']} / {n}",
            f"{m['context_disambiguation']['rate'] * 100:.0f}%",
        )
        col3.metric("Compiled Instructions", m["compiled_instructions"]["count"])
        col4.metric("Avg Instruction Length", f"{m['avg_instruction_length_chars']} chars")

        st.divider()
        st.markdown("**Intent Distribution**")
        for intent, count in sorted(m["intent_distribution"].items(), key=lambda x: -x[1]):
            pct = count / n * 100
            col_a, col_b, col_c = st.columns([2, 1, 7])
            col_a.markdown(
                f'<span style="background:{INTENT_COLORS.get(intent, "#888")};color:white;'
                f'padding:2px 8px;border-radius:8px;font-size:0.8em">{intent}</span>',
                unsafe_allow_html=True,
            )
            col_b.write(f"{count} ({pct:.0f}%)")
            col_c.progress(pct / 100)


# ── Tab 4: About ───────────────────────────────────────────────────────────────
with tab_about:
    st.subheader("About This Project")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(
            """
### The Problem

Modern GUI test automation requires translating visual interactions into executable test steps.
Current approaches need human testers to manually describe what they did — this project automates that step.

### How It Works

A screenshot is captured after each user interaction, with a **red bounding box** drawn around the
interacted element. This image, paired with a minimal action descriptor
(`{"action": "click"}` or `{"action": "entry", "argument": "value"}`),
is sent to **Gemini 2.5 Flash Lite** with a structured prompt.

The model reads the screen, identifies the element label, determines the interaction type
(one of 7 intents), handles ambiguity by identifying surrounding context, and outputs a
precise natural language instruction.

### The Bigger Picture

This project produces the **natural language instruction layer** — structured,
human-readable descriptions of what happened on screen. That output is directly
consumable by any system that takes natural language steps and converts them to
executable test code, completing a full GUI → test automation pipeline with no
manual annotation.

### Three-Phase Evaluation

| Phase | Adds | Samples |
|-------|------|---------|
| I | Click & entry with/without context disambiguation | 25 |
| II | Dropdown expand + select sequences | 20 |
| III | Date picker sequences with compiled instructions | 30 |

### Accuracy

~80% overall across 70 samples and 7 intent types (manual evaluation against hand-labeled ground truth).
Phase I reaches ~88%; Phases II and III stabilize at ~80% due to increased interaction complexity.
            """
        )

    with col2:
        st.markdown("**Pipeline diagram**")
        st.code(
            """\
Screenshot + Action JSON
        │
        ▼
Gemini 2.5 Flash Lite
  (vision + structured
   output mode)
        │
        ▼
{
  "instruction": "...",
  "intent": "...",
  "compiled_instruction": "..."
}
        │
        ▼
  Downstream test
  generation step
""",
            language=None,
        )

        st.markdown("**Tech stack**")
        st.markdown(
            "- Google Gemini 2.5 Flash Lite\n"
            "- `google-genai` Python SDK\n"
            "- Streamlit\n"
            "- Python 3.10+"
        )
