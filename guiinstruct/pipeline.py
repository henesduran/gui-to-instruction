import json
import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import types

from .prompts import PROMPTS

load_dotenv()

_client = None


def _get_client() -> genai.Client:
    global _client
    if _client is None:
        _client = genai.Client()
    return _client


def _load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data: dict, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def _read_image(path: str) -> bytes | None:
    try:
        with open(path, "rb") as f:
            return f.read()
    except FileNotFoundError:
        print(f"  [skip] screenshot not found: {path}")
        return None


def _detect_mime(data: bytes) -> str:
    return "image/jpeg" if data[:2] == b"\xff\xd8" else "image/png"


def _call_gemini(image_data: bytes, action_data: dict, phase: int) -> dict:
    client = _get_client()
    image_part = types.Part.from_bytes(data=image_data, mime_type=_detect_mime(image_data))
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        config=types.GenerateContentConfig(
            system_instruction=PROMPTS[phase],
            response_mime_type="application/json",
        ),
        contents=[f"Action Data: {json.dumps(action_data)}", image_part],
    )
    return json.loads(response.text)


def run(
    actions_path: str,
    screenshots_dir: str,
    output_path: str,
    phase: int,
    resume: bool = True,
    delay: float = 15.0,
) -> None:
    """Process all actions in actions_path and write results to output_path."""
    actions = _load_json(actions_path)

    results: dict = {}
    if resume and os.path.exists(output_path):
        try:
            results = _load_json(output_path)
        except json.JSONDecodeError:
            pass

    already_done = set(results.keys())
    pending = [k for k in actions if k not in already_done]

    print(f"Phase {phase} | {len(already_done)} done, {len(pending)} pending")

    for key in pending:
        data = actions[key]
        image_path = os.path.join(screenshots_dir, data["ss"])
        image_data = _read_image(image_path)
        if image_data is None:
            continue

        print(f"  Processing {key}...", end=" ", flush=True)
        try:
            result = _call_gemini(image_data, data, phase)
            results[key] = result
            _save_json(results, output_path)
            print("OK")
            time.sleep(delay)
        except Exception as exc:
            print(f"ERROR — {exc}")
            time.sleep(5)

    print(f"\nDone. Results written to {output_path}")
