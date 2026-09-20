"""De-identification, extraction prompt, and OpenAI calls.

Hard rule: the LLM never sees patient names/identifiers. Callers must use
deidentify() before building any prompt, and reattach_patient() after getting
a response back.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

import streamlit as st
from openai import OpenAI

MODEL = "gpt-5.6-sol"

# Structured-output schema for extraction, passed to the Responses API via
# text.format (json_schema, strict mode) — see llm_client.py's
# call_llm_structured() for the reference pattern this follows. Strict mode
# requires every property listed in "required" and "additionalProperties": false;
# nullable fields use a ["type", "null"] union instead of a bare type.
EXTRACTION_SCHEMA = {
    "type": "object",
    "properties": {
        "patient_placeholder": {
            "type": "string",
            "description": (
                "The placeholder token referenced (e.g. 'PATIENT_A'), or 'NEW_PATIENT' if the "
                "entry describes someone not in the placeholder list, or 'UNKNOWN' if unclear."
            ),
        },
        "procedure_type": {
            "type": "string",
            "description": "e.g. 'Class II composite', 'extraction', 'RCT'.",
        },
        "tooth": {"type": ["string", "null"], "description": "e.g. '36'."},
        "description": {"type": "string", "description": "Concise clinical description."},
        "complications": {"type": ["string", "null"], "description": "Null if none mentioned."},
        "follow_up_needed": {"type": "boolean"},
        "follow_up_date": {
            "type": ["string", "null"],
            "description": "ISO date YYYY-MM-DD if mentioned, else null.",
        },
    },
    "required": [
        "patient_placeholder",
        "procedure_type",
        "tooth",
        "description",
        "complications",
        "follow_up_needed",
        "follow_up_date",
    ],
    "additionalProperties": False,
}

EXTRACTION_SYSTEM_PROMPT = """You are a clinical note structuring assistant for a dentist's fellowship logbook.

The input text may be in Hinglish (code-mixed Hindi and English, written in Latin script), \
plain English, or a mix of both within the same entry. Treat this as normal, expected input — \
do not assume pure English, and do not ask for clarification. Extract the clinical meaning \
regardless of language mixing, spelling variation, or informal phrasing.

Patient identifiers in the text have already been replaced with placeholder tokens like \
PATIENT_A, PATIENT_B, etc. Never invent a real name. If the text mentions someone who does not \
match any known placeholder, use "NEW_PATIENT" for patient_placeholder.
"""


@dataclass
class DeidentifiedText:
    text: str
    placeholder_map: dict = field(default_factory=dict)  # placeholder -> patient_id


def deidentify(raw_text: str, patients: list[dict]) -> DeidentifiedText:
    """Replace known patient display_names with neutral placeholders.

    patients: list of dicts with at least 'id' and 'display_name'.
    """
    text = raw_text
    placeholder_map: dict[str, str] = {}
    for idx, patient in enumerate(patients):
        name = patient.get("display_name", "")
        if not name:
            continue
        placeholder = f"PATIENT_{chr(65 + (idx % 26))}{idx // 26 if idx >= 26 else ''}"
        pattern = re.compile(re.escape(name), re.IGNORECASE)
        if pattern.search(text):
            text = pattern.sub(placeholder, text)
            placeholder_map[placeholder] = patient["id"]
    return DeidentifiedText(text=text, placeholder_map=placeholder_map)


def resolve_patient_id(placeholder: str, placeholder_map: dict) -> str | None:
    """Reattach a real patient_id locally from the LLM's placeholder reference."""
    return placeholder_map.get(placeholder)


@st.cache_resource(show_spinner=False)
def get_client() -> OpenAI:
    return OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def extract_case(deidentified_text: str) -> tuple[dict | None, str | None]:
    """Call the LLM to extract structured fields from de-identified case text.

    Returns (fields_dict, None) on success, or (None, error_message) on failure
    so the caller can fall back to a manual form.
    """
    try:
        client = get_client()
        response = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": deidentified_text},
            ],
            store=False,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "case_extraction",
                    "strict": True,
                    "schema": EXTRACTION_SCHEMA,
                }
            },
        )
        fields = json.loads(response.output_text)
        return fields, None
    except json.JSONDecodeError:
        return None, "The AI's response wasn't in the expected format."
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not reach the AI service. Details: {exc}"


NARRATIVE_SYSTEM_PROMPT = """You are helping a dentist write a narrative summary for a clinical \
fellowship report, based only on the confirmed statistics and case summaries provided. \
Do not invent any procedures, numbers, or complications that are not present in the data given. \
Write in a professional but concise tone, 2-4 short paragraphs, suitable for inclusion in a \
fellowship progress report."""


def generate_narrative(stats: dict, case_summaries: list[str]) -> tuple[str | None, str | None]:
    """Generate a narrative report summary from confirmed stats + case summaries."""
    try:
        client = get_client()
        user_content = (
            "Stats (JSON):\n"
            + json.dumps(stats, indent=2)
            + "\n\nCase summaries:\n"
            + "\n".join(f"- {s}" for s in case_summaries)
        )
        response = client.responses.create(
            model=MODEL,
            input=[
                {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            store=False,
        )
        return response.output_text, None
    except Exception as exc:  # noqa: BLE001
        return None, f"Could not reach the AI service. Details: {exc}"
