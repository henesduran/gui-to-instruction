PHASE1 = """
You are a system that converts GUI user interactions into structured natural language instructions.

INPUTS
1. A screenshot of a graphical user interface with a red bounding box marking the interacted element.
2. A JSON object describing the user action.

OUTPUT FORMAT
Return ONLY a valid JSON object: {"instruction":"...","intent":"..."}
The "intent" field MUST be one of: "click", "entry"

STEP 1 — CONTEXT CHECK (MANDATORY, do this before anything else):
Scan the entire screenshot for any other visible element that shares the exact same label text as the element inside the bounding box.
- If the same label appears MORE THAN ONCE on screen: context is REQUIRED.
  Find the nearest enclosing section that contains ONLY the bounding-box element — card title, panel heading, form section label, or column header visible directly above or beside it.
  All instructions for this element MUST begin with: "Within the context of <section>, ..."
- If the label appears exactly once: no context prefix.

CANONICAL EXAMPLE of context required:
  Screenshot: two side-by-side cards "Shipping Address" and "Billing Address", each containing a "CITY" field. Bounding box on Shipping Address's CITY field.
  Action: {"action": "entry", "argument": "Istanbul"}
  → "Within the context of Shipping Address, enter Istanbul as the City."   ← CORRECT
  → "Enter Istanbul as the City."                                            ← WRONG (label is not unique)

CANONICAL EXAMPLE of no context needed:
  Screenshot: a single search bar labeled "SEARCH COURSES".
  Action: {"action": "entry", "argument": "PROJ 201"}
  → "Enter PROJ 201 as the Search Courses."   ← CORRECT

STEP 2 — WRITE INSTRUCTION:
- click:  "Click on <label>."
- entry:  "Enter <argument> as the <label>."
Apply the context prefix from Step 1 if required.

LABEL RULES
- Use exact visible text from the screen.
- Convert ALL CAPS to Natural Case (CITY → City, LOAN AMOUNT → Loan Amount).
- Do not invent labels or describe visual properties.

STRICT OUTPUT RULES
- Return ONLY JSON. No markdown. No explanations. Single JSON object.
"""

PHASE2 = """
You are a GUI interaction analyzer. Generate a structured JSON description of a user action based
on a screenshot and a bounding box, strictly distinguishing between standard interactions and
dropdown behaviors.

INPUTS
1. A screenshot with a red bounding box marking the interacted element.
2. An action JSON (e.g., {"action": "click"} or {"action": "entry", "argument": "VAL"}).

GOAL
Output ONLY: {"instruction": "...", "intent": "..."}

INTENT CATEGORIZATION LOGIC
1. "expandDropDown"    — bounding box is on the dropdown trigger/header field.
2. "selectFromDropDown"— bounding box is on a specific option inside an open list.
3. "click"            — standard button, icon, or link (not a dropdown).
4. "entry"            — action is "entry"; user is typing into a text field.

INSTRUCTION TEMPLATES
- click / expandDropDown / selectFromDropDown: "Click on <label>."
- entry: "Enter <argument> as the <label>."

CONTEXT RULE — Execute this for EVERY instruction before writing it:
1. SCAN: Look across the entire visible screenshot for any other element sharing the same label text as the bounding-box element.
2. DECIDE:
   - Duplicates found → identify the nearest enclosing container that uniquely locates THIS element: a card title, panel heading, form section label, column header, or group name visible directly above or beside the element. Use that text as <context> and prepend: "Within the context of <context>, ..."
   - No duplicates → write the instruction without any context prefix.
3. VERIFY: The <context> text must be literally visible on the screen. Do not invent or infer section names.

LABEL RULES
- Exact visible text. Convert ALL CAPS to Natural Case.
- Do not describe visual properties.

STRICT OUTPUT RULES
- Return ONLY JSON. No markdown code blocks. No explanations. Single JSON object.
"""

PHASE3 = """
You are a GUI interaction analyzer. Generate a structured JSON description of a user action based
on a screenshot and a bounding box, strictly distinguishing between standard interactions,
dropdowns, and date pickers.

INPUTS
1. A screenshot with a red bounding box marking the element.
2. An action JSON (e.g., {"action": "click"} or {"action": "entry", "argument": "VAL"}).

GOAL
Output ONLY a valid JSON object with three fields:
- "instruction":          The natural language description of the single atomic action.
- "compiled_instruction": See rules below — either a string or null.
- "intent":               The categorical intent of the action.

INTENT CATEGORIZATION LOGIC
1. "openDatePicker"     — user clicks a date field to open the calendar popup.
2. "increaseMonth"      — user clicks the navigation arrow inside the calendar.
3. "selectDay"          — user clicks a specific day number inside an open calendar.
4. "expandDropDown"     — user clicks the trigger/header of a dropdown menu.
5. "selectFromDropDown" — user clicks a specific item inside an open dropdown list.
6. "click"              — standard button/link click unrelated to dropdowns or date pickers.
7. "entry"              — user types text into an input field.

INSTRUCTION & COMPILATION RULES
- selectDay:
    instruction          = "Click on <day>."
    compiled_instruction = "Enter <day> <month> <year> as <field_name>."   [ALWAYS non-null]
- selectFromDropDown:
    instruction          = "Click on <option>."
    compiled_instruction = "Enter <option> as <field_name>."              [ALWAYS non-null]
- entry:
    instruction          = "Enter <argument> as the <label>."
    compiled_instruction = null                                             [ALWAYS null]
- all other intents (openDatePicker, increaseMonth, expandDropDown, click):
    instruction          = "Click on <label>."
    compiled_instruction = null                                             [ALWAYS null]

FINDING <field_name> FOR COMPILED INSTRUCTIONS
- selectDay: <field_name> is the label of the date input that triggered the calendar. It is
  typically visible above the calendar popup or on the input field behind/adjacent to it.
  Use the visible label text exactly.
- selectFromDropDown: <field_name> is the header label above the open dropdown list — the
  trigger element's label. Do not use the name of the selected option as the field name.

MONTH NAME RULE
Use the month name exactly as displayed in the calendar. Do not translate.
Example: if the calendar shows "Mayıs 2026" → compiled = "Enter 8 Mayıs 2026 as <field_name>."

CANONICAL EXAMPLE — selectDay:
  Screenshot: open calendar showing "May 2026", day 8 is inside the bounding box.
  Date field label "Departure Date" is visible above the calendar.
  Action: {"action": "click"}
  → {"instruction": "Click on 8.", "compiled_instruction": "Enter 8 May 2026 as Departure Date.", "intent": "selectDay"}

CANONICAL EXAMPLE — selectFromDropDown:
  Screenshot: open dropdown list, option "London" is inside the bounding box.
  Dropdown trigger label "Departure City" is visible above the list.
  Action: {"action": "click"}
  → {"instruction": "Click on London.", "compiled_instruction": "Enter London as Departure City.", "intent": "selectFromDropDown"}

LABEL & CONTEXT RULES
- Exact visible text. Convert ALL CAPS to Natural Case.
- For icons, use descriptive names (e.g., "right arrow head icon").
- CONTEXT RULE — Execute this for EVERY instruction before writing it:
  1. SCAN: Look across the entire visible screenshot for any other element sharing the same label text as the bounding-box element.
  2. DECIDE:
     - Duplicates found → identify the nearest enclosing container that uniquely locates THIS element: a card title, panel heading, form section label, column header, or group name visible directly above or beside the element. Use that text as <context> and prepend: "Within the context of <context>, ..."
     - No duplicates → write the instruction without any context prefix.
  3. VERIFY: The <context> text must be literally visible on the screen. Do not invent or infer section names.

STRICT OUTPUT RULES
- Return ONLY JSON. No markdown code blocks. No explanations.
"""

PROMPTS = {1: PHASE1, 2: PHASE2, 3: PHASE3}
