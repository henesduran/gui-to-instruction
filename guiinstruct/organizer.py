"""
Organizes pipeline output into a structured directory tree.

Phase 1 & 2: groups are consecutive pairs  (action1+action2 → group1/, etc.)
Phase 3:     groups are consecutive triples (action1+action2+action3 → group1/)
             Each action is placed in an intent-named sub-folder.
"""

import json
import os
import shutil


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _sorted_keys(data: dict) -> list[str]:
    return sorted(data.keys(), key=lambda k: int(k.replace("action", "")))


def _write_json(obj: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=4, ensure_ascii=False)


def _copy_screenshot(src_dir: str, ss_name: str | None, dest: str) -> None:
    if not ss_name:
        return
    src = os.path.join(src_dir, ss_name)
    if os.path.exists(src):
        shutil.copy(src, dest)
    else:
        print(f"  [warn] screenshot not found: {src}")


def _save_action_files(
    key: str,
    dest_dir: str,
    actions: dict,
    outputs: dict,
    screenshots_dir: str,
    filename: str = "output.json",
) -> None:
    os.makedirs(dest_dir, exist_ok=True)
    _write_json(outputs.get(key, {}), os.path.join(dest_dir, filename))
    _write_json(actions.get(key, {}), os.path.join(dest_dir, "action.json"))
    _copy_screenshot(
        screenshots_dir,
        actions.get(key, {}).get("ss"),
        os.path.join(dest_dir, "ss.png"),
    )


# ---------- Phase 1 / 2 ----------

def organize_paired(
    actions_path: str,
    output_path: str,
    screenshots_dir: str,
    dest_dir: str,
    group_size: int = 2,
) -> None:
    """Groups actions into consecutive groups of `group_size`."""
    actions = _load_json(actions_path)
    outputs = _load_json(output_path)
    os.makedirs(dest_dir, exist_ok=True)

    keys = _sorted_keys(actions)
    for i in range(0, len(keys), group_size):
        group_id = i // group_size + 1
        group_keys = keys[i : i + group_size]
        for sub_idx, key in enumerate(group_keys, start=1):
            dest = os.path.join(dest_dir, str(group_id), str(sub_idx))
            _save_action_files(key, dest, actions, outputs, screenshots_dir)
        print(f"  Group {group_id}: {group_keys}")

    print(f"\nOrganized {len(keys)} actions into {dest_dir}/")


# ---------- Phase 3 ----------

INTENT_DIRS = {
    "openDatePicker":    "Open_Date_Picker",
    "increaseMonth":     "Increase_Month",
    "selectDay":         "Day_Selection",
    "expandDropDown":    "Expand_Dropdown",
    "selectFromDropDown":"Select_From_Dropdown",
    "click":             "Click",
    "entry":             "Entry",
}


def organize_phase3(
    actions_path: str,
    output_path: str,
    screenshots_dir: str,
    dest_dir: str,
    group_size: int = 3,
) -> None:
    actions = _load_json(actions_path)
    outputs = _load_json(output_path)
    os.makedirs(dest_dir, exist_ok=True)

    keys = _sorted_keys(actions)
    for i in range(0, len(keys), group_size):
        group_id = i // group_size + 1
        group_keys = keys[i : i + group_size]
        group_dir = os.path.join(dest_dir, str(group_id))
        os.makedirs(group_dir, exist_ok=True)

        for key in group_keys:
            out = outputs.get(key, {})
            intent = out.get("intent", "click")
            sub_dir_name = INTENT_DIRS.get(intent, intent)
            dest = os.path.join(group_dir, sub_dir_name)
            _save_action_files(key, dest, actions, outputs, screenshots_dir)

            # write compiled instruction at group level if present
            compiled = out.get("compiled_instruction")
            if compiled:
                _write_json(
                    {"instruction": compiled, "intent": "compiled"},
                    os.path.join(group_dir, "compiled.json"),
                )

        print(f"  Group {group_id}: {group_keys}")

    print(f"\nOrganized {len(keys)} actions into {dest_dir}/")
