"""Supabase client init and all CRUD query functions.

Every function catches its own exceptions and returns (data, error) so that
page code can show a friendly st.error(...) instead of a raw traceback.
"""

from __future__ import annotations

import streamlit as st
from supabase import create_client, Client


class DbError(Exception):
    pass


@st.cache_resource(show_spinner=False)
def get_client() -> Client:
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def _run(fn):
    """Run a Supabase call, returning (data, None) or (None, friendly_error_str)."""
    try:
        result = fn()
        return result.data, None
    except Exception as exc:  # noqa: BLE001 - deliberately broad, surfaced as friendly error
        return None, f"Could not complete that database action. Details: {exc}"


# ---------------------------------------------------------------------------
# patients
# ---------------------------------------------------------------------------

def get_patients():
    client = get_client()
    return _run(lambda: client.table("patients").select("*").order("display_name").execute())


def get_patient(patient_id: str):
    client = get_client()
    data, error = _run(
        lambda: client.table("patients").select("*").eq("id", patient_id).limit(1).execute()
    )
    if error:
        return None, error
    if not data:
        return None, "Patient not found."
    return data[0], None


def search_patients(query: str):
    client = get_client()
    if not query:
        return get_patients()
    return _run(
        lambda: client.table("patients")
        .select("*")
        .ilike("display_name", f"%{query}%")
        .order("display_name")
        .execute()
    )


def create_patient(display_name: str, age=None, sex=None, notes=None):
    client = get_client()
    payload = {"display_name": display_name, "age": age, "sex": sex, "notes": notes}
    data, error = _run(lambda: client.table("patients").insert(payload).execute())
    if error:
        return None, error
    return data[0], None


# ---------------------------------------------------------------------------
# procedures
# ---------------------------------------------------------------------------

def create_procedure(
    patient_id: str,
    date,
    procedure_type: str,
    tooth=None,
    description=None,
    complications=None,
    follow_up_needed: bool = False,
    follow_up_date=None,
    status: str = "confirmed",
    raw_input: str = None,
):
    client = get_client()
    payload = {
        "patient_id": patient_id,
        "date": str(date),
        "procedure_type": procedure_type,
        "tooth": tooth,
        "description": description,
        "complications": complications,
        "follow_up_needed": follow_up_needed,
        "follow_up_date": str(follow_up_date) if follow_up_date else None,
        "status": status,
        "raw_input": raw_input,
    }
    data, error = _run(lambda: client.table("procedures").insert(payload).execute())
    if error:
        return None, error
    return data[0], None


def get_procedures_for_patient(patient_id: str, confirmed_only: bool = True):
    client = get_client()
    query = client.table("procedures").select("*").eq("patient_id", patient_id)
    if confirmed_only:
        query = query.eq("status", "confirmed")
    return _run(lambda: query.order("date", desc=True).execute())


def get_confirmed_procedures_in_range(period_start, period_end):
    client = get_client()
    return _run(
        lambda: client.table("procedures")
        .select("*")
        .eq("status", "confirmed")
        .gte("date", str(period_start))
        .lte("date", str(period_end))
        .order("date")
        .execute()
    )


# ---------------------------------------------------------------------------
# daily_logs
# ---------------------------------------------------------------------------

def create_daily_log(
    date,
    raw_input: str,
    parsed_summary: str = None,
    linked_procedure_ids=None,
    status: str = "confirmed",
):
    client = get_client()
    payload = {
        "date": str(date),
        "raw_input": raw_input,
        "parsed_summary": parsed_summary,
        "linked_procedure_ids": linked_procedure_ids or [],
        "status": status,
    }
    data, error = _run(lambda: client.table("daily_logs").insert(payload).execute())
    if error:
        return None, error
    return data[0], None


def get_daily_logs_in_range(period_start, period_end, confirmed_only: bool = True):
    client = get_client()
    query = (
        client.table("daily_logs")
        .select("*")
        .gte("date", str(period_start))
        .lte("date", str(period_end))
    )
    if confirmed_only:
        query = query.eq("status", "confirmed")
    return _run(lambda: query.order("date").execute())


# ---------------------------------------------------------------------------
# appointments
# ---------------------------------------------------------------------------

def get_appointments():
    client = get_client()
    return _run(
        lambda: client.table("appointments").select("*, patients(display_name)").order("datetime").execute()
    )


def create_appointment(patient_id: str, dt, purpose: str = None, status: str = "scheduled"):
    client = get_client()
    payload = {
        "patient_id": patient_id,
        "datetime": dt.isoformat() if hasattr(dt, "isoformat") else str(dt),
        "purpose": purpose,
        "status": status,
    }
    data, error = _run(lambda: client.table("appointments").insert(payload).execute())
    if error:
        return None, error
    return data[0], None


def update_appointment(appointment_id: str, **fields):
    client = get_client()
    if "datetime" in fields and hasattr(fields["datetime"], "isoformat"):
        fields["datetime"] = fields["datetime"].isoformat()
    data, error = _run(
        lambda: client.table("appointments").update(fields).eq("id", appointment_id).execute()
    )
    if error:
        return None, error
    return data[0] if data else None, None


# ---------------------------------------------------------------------------
# report_snapshots
# ---------------------------------------------------------------------------

def save_report_snapshot(period_start, period_end, content: str, stats_json: dict):
    client = get_client()
    payload = {
        "period_start": str(period_start),
        "period_end": str(period_end),
        "content": content,
        "stats_json": stats_json,
    }
    data, error = _run(lambda: client.table("report_snapshots").insert(payload).execute())
    if error:
        return None, error
    return data[0], None
