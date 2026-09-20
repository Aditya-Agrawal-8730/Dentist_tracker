"""Appointments: list grouped by date + status, simple add/edit form."""

import datetime

import streamlit as st

from lib import auth, db

auth.require_auth()

st.title("📅 Appointments")

patients, patients_error = db.get_patients()
if patients_error:
    st.error(patients_error)
    patients = []

with st.expander("➕ Add appointment"):
    if not patients:
        st.info("Add a patient first (on the Patients page) before scheduling an appointment.")
    else:
        with st.form("add_appointment_form", clear_on_submit=True):
            patient_name = st.selectbox("Patient", [p["display_name"] for p in patients])
            col1, col2 = st.columns(2)
            with col1:
                appt_date = st.date_input("Date", value=datetime.date.today())
            with col2:
                appt_time = st.time_input("Time", value=datetime.time(10, 0))
            purpose = st.text_input("Purpose")
            status = st.selectbox("Status", ["scheduled", "completed", "cancelled", "no_show"])
            submitted = st.form_submit_button("Add appointment")
            if submitted:
                patient = next(p for p in patients if p["display_name"] == patient_name)
                dt = datetime.datetime.combine(appt_date, appt_time)
                new_appt, create_error = db.create_appointment(
                    patient_id=patient["id"], dt=dt, purpose=purpose or None, status=status
                )
                if create_error:
                    st.error(create_error)
                else:
                    st.success("Appointment added.")
                    st.rerun()

st.divider()

status_filter = st.multiselect(
    "Filter by status",
    ["scheduled", "completed", "cancelled", "no_show"],
    default=["scheduled", "completed", "cancelled", "no_show"],
)

appointments, error = db.get_appointments()
if error:
    st.error(error)
    appointments = []

filtered = [a for a in appointments if a["status"] in status_filter]

if not filtered:
    st.info("No appointments match this filter.")
else:
    grouped: dict[str, list] = {}
    for appt in filtered:
        day = appt["datetime"][:10]
        grouped.setdefault(day, []).append(appt)

    for day in sorted(grouped.keys()):
        st.subheader(day)
        for appt in grouped[day]:
            patient_info = appt.get("patients") or {}
            patient_name = patient_info.get("display_name", "Unknown patient")
            time_str = appt["datetime"][11:16]
            col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
            with col1:
                st.write(time_str)
            with col2:
                st.write(f"{patient_name} — {appt.get('purpose') or ''}")
            with col3:
                st.write(appt["status"])
            with col4:
                new_status = st.selectbox(
                    "Update",
                    ["scheduled", "completed", "cancelled", "no_show"],
                    index=["scheduled", "completed", "cancelled", "no_show"].index(
                        appt["status"]
                    ),
                    key=f"status_{appt['id']}",
                    label_visibility="collapsed",
                )
                if new_status != appt["status"]:
                    _, update_error = db.update_appointment(appt["id"], status=new_status)
                    if update_error:
                        st.error(update_error)
                    else:
                        st.rerun()
