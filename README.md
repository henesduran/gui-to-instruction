---
title: GUI Instruction Pipeline
emoji: 🖱️
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.41.0
app_file: app.py
pinned: false
---

# gui-to-instruction

Given a GUI screenshot and two fields of action metadata, this pipeline outputs a structured natural language instruction — precise enough to drive any downstream test automation system.

```json
Input:  {"action": "entry", "argument": "Istanbul"}
Output: {"instruction": "Within the context of Shipping Address, enter Istanbul as the City.", "intent": "entry"}
```

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://python.org)
[![Model](https://img.shields.io/badge/Model-Gemini%202.5%20Flash%20Lite-orange?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Live Demo](https://img.shields.io/badge/🤗%20Live%20Demo-Hugging%20Face-yellow)](https://huggingface.co/spaces/henesduran/gui-instruction-pipeline)

---

## Try It Live

Upload any GUI screenshot with a red bounding box → get a structured instruction in seconds.

👉 [**Open the demo on Hugging Face Spaces**](https://huggingface.co/spaces/henesduran/gui-instruction-pipeline)

---

## The Problem

Every GUI test framework that works from natural language step descriptions depends on someone writing those descriptions manually. For a 60-step test flow, that means 60 hand-written sentences describing what was clicked, what was typed, and in which context. This project automates that annotation step.

---

## How It Works

Each GUI interaction is captured as a screenshot with a red bounding box drawn around the element the user interacted with. This image, paired with a minimal machine-recorded action descriptor, is sent to Gemini 2.5 Flash Lite with a structured system prompt.

The model reads the screen, extracts the visible element label, classifies the interaction type into one of seven intents, checks whether the label is unique on screen, and outputs a precise natural language instruction.

```
Screenshot (PNG) + Action JSON
        │
        ▼
Gemini 2.5 Flash Lite
  · extracts visible element label
  · classifies intent (7 types)
  · resolves label ambiguity via section context
  · structured JSON output mode
        │
        ▼
{
  "instruction":          "Within the context of Shipping Address, enter Istanbul as the City.",
  "intent":               "entry",
  "compiled_instruction": null
}
```

---

## Results

| Phase | Interaction Types | Samples | Accuracy |
|-------|------------------|---------|----------|
| I | Click and text entry, with/without context disambiguation | 25 | ~88% |
| II | Dropdown expand + option select sequences | 20 | ~80% |
| III | Date picker sequences with compiled multi-step instructions | 30 | ~80% |
| **Total** | **7 intent types** | **70** | **~80%** |

Evaluation was manual: each generated instruction compared against a hand-labeled ground truth, judged on intent correctness, label accuracy, and presence/absence of context phrase.

---

## Intent Classification

| Intent | Trigger | Example Output |
|--------|---------|----------------|
| `click` | Standard button or link | `"Click on Apply Now."` |
| `entry` | Text field input | `"Enter 50000 as the Annual Income $."` |
| `expandDropDown` | Clicking the dropdown trigger area | `"Click on Departure."` |
| `selectFromDropDown` | Clicking an item inside an open list | `"Click on London."` + compiled: `"Enter London as Departure."` |
| `openDatePicker` | Clicking a date field | `"Click on Gidiş Tarihi."` |
| `increaseMonth` | Clicking the calendar navigation arrow | `"Click on right arrow head icon."` |
| `selectDay` | Clicking a day number inside the calendar | `"Click on 8."` + compiled: `"Enter 8 May 2026 as Kalkış."` |

For multi-step sequences (open calendar → navigate month → select day), the model emits an atomic `instruction` for each step and a `compiled_instruction` on the final step that summarizes the full intent as a single test action.

---

## Context Disambiguation

Many GUI forms repeat the same field label in multiple sections — "City", "Zip Code", "Full Name" appear in both billing and shipping blocks. Without disambiguation, the instruction `"Enter Istanbul as the City."` is ambiguous and unroutable by any test system.

The pipeline handles this by requiring the model to check whether the target label is unique on the visible screen. If not, the instruction must include the nearest section title:

```json
{"instruction": "Within the context of Shipping Address, enter Istanbul as the City.", "intent": "entry"}
```

Phase I accuracy on context-requiring samples: correct context phrase produced in ~88% of cases.

---

## Example Outputs

**Click with context disambiguation** — "Sepete ekle" (Add to Cart) appears on every product card; model anchors on the product name:
```json
{"action": "click"}
→ {"instruction": "Within the context of Rotring Jel Kalem 0.7 mm, Siyah - 2114436, click on Sepete ekle.", "intent": "click"}
```

**Entry, no context** — unique search field:
```json
{"action": "entry", "argument": "PROJ 201"}
→ {"instruction": "Enter PROJ 201 as the Search Courses.", "intent": "entry"}
```

**ALL CAPS label normalization** — visible label is "TUTAR"; model normalizes to natural case:
```json
{"action": "entry", "argument": "120,000"}
→ {"instruction": "Enter 120,000 as the Tutar.", "intent": "entry"}
```

**Date picker sequence** — 3 atomic steps collapse into 1 compiled instruction:
```json
Step 1: {"instruction": "Click on Gidiş Tarihi.",        "intent": "openDatePicker",  "compiled_instruction": null}
Step 2: {"instruction": "Click on right arrow head icon.", "intent": "increaseMonth",   "compiled_instruction": null}
Step 3: {"instruction": "Click on 8.",                    "intent": "selectDay",        "compiled_instruction": "Enter 8 May 2026 as Kalkış."}
```

---

## Setup

```bash
git clone https://github.com/henesduran/gui-to-instruction
cd gui-to-instruction
pip install -r requirements.txt
cp .env.example .env   # add your GEMINI_API_KEY
```

Requires Python 3.10+ and a [Google AI Studio API key](https://aistudio.google.com/apikey).

---

## Usage

**Run the pipeline:**
```bash
python run_tests.py --phase 1
python run_tests.py --phase 1 --resume   # skip already-processed actions
python run_tests.py --phase 3 --delay 10
```

**Launch the Streamlit demo:**
```bash
streamlit run app.py
```

**Evaluate results programmatically:**
```python
from guiinstruct.eval import evaluate, report

metrics = evaluate("output.json")
print(metrics)

report({"Phase I": "output.json", "Phase II": "output2.json", "Phase III": "output5.json"})
```

---

## Repository Structure

```
gui-to-instruction/
├── app.py               # Streamlit demo — live inference, results gallery, metrics
├── run_tests.py         # CLI pipeline runner (argparse, phases 1–3)
├── requirements.txt
├── actions.json         # Phase I action descriptors (25 samples)
├── output.json          # Phase I pipeline outputs
├── examples/            # 6 annotated screenshots for the demo gallery
│   ├── action1.png      # click with context disambiguation
│   ├── action6.png      # click without context
│   ├── action10.png     # entry without context
│   ├── action19.png     # entry with ALL CAPS label normalization
│   ├── action20.png     # entry without context
│   └── action21.png     # entry with context disambiguation
└── guiinstruct/         # Core package
    ├── pipeline.py      # Inference engine: loads actions → calls Gemini → saves results
    ├── prompts.py       # System prompts for phases I, II, III
    ├── organizer.py     # Groups results into structured directory trees
    └── eval.py          # Evaluation metrics: intent distribution, context rate, avg length
```

---

## Roadmap

- [x] Phase I: click and entry with context disambiguation (25 samples, ~88%)
- [x] Phase II: dropdown expand/select sequences (20 samples, ~80%)
- [x] Phase III: date picker sequences with compiled instructions (30 samples, ~80%)
- [ ] Multi-model comparison: Gemini 2.5 Flash Lite vs GPT-4o vs Claude 3.5 Sonnet on the same dataset
- [ ] Expand dataset to 200+ samples with formal inter-annotator agreement scoring
- [ ] JSON output adapter aligned to a standard step-definition schema

---

## License

MIT
