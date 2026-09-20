"""Patients: searchable list, per-patient procedure history, add new patient."""

import streamlit as st

from lib import auth, db

auth.require_auth()

st.title("🧑‍⚕️ Patients")

search = st.text_input("Search by name")
patients, error = db.search_patients(search)
if error:
    st.error(error)
    patients = []

with st.expander("➕ Add new patient"):
    with st.form("add_patient_form", clear_on_submit=True):
        display_name = st.text_input(
            "Display name (local identifier only, e.g. 'Patient 14' or initials)"
        )
        col1, col2 = st.columns(2)
        with col1:
            age = st.number_input("Age", min_value=0, max_value=120, value=0)
        with col2:
            sex = st.selectbox("Sex", ["", "M", "F", "Other"])
        notes = st.text_area("Notes (optional)")
        submitted = st.form_submit_button("Add patient")
        if submitted:
            if not display_name.strip():
                st.warning("Display name is required.")
            else:
                new_patient, create_error = db.create_patient(
                    display_name=display_name.strip(),
                    age=int(age) or None,
                    sex=sex or None,
                    notes=notes or None,
                )
                if create_error:
                    st.error(create_error)
                else:
                    st.success(f"Added {display_name.strip()}.")
                    st.rerun()

st.divider()

if not patients:
    st.info("No patients found yet.")
else:
    names = [p["display_name"] for p in patients]
    selected_name = st.selectbox("Select a patient to view history", names)
    selected_patient = next(p for p in patients if p["display_name"] == selected_name)

    st.subheader(selected_patient["display_name"])
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Age:** {selected_patient.get('age') or '—'}")
    with col2:
        st.write(f"**Sex:** {selected_patient.get('sex') or '—'}")
    if selected_patient.get("notes"):
        st.write(f"**Notes:** {selected_patient['notes']}")

    st.write("**Confirmed procedure history:**")
    procedures, proc_error = db.get_procedures_for_patient(
        selected_patient["id"], confirmed_only=True
    )
    if proc_error:
        st.error(proc_error)
    elif not procedures:
        st.write("No confirmed procedures yet.")
    else:
        st.dataframe(
            [
                {
                    "Date": p["date"],
                    "Procedure": p["procedure_type"],
                    "Tooth": p.get("tooth") or "",
                    "Complications": p.get("complications") or "",
                    "Follow-up": "Yes" if p.get("follow_up_needed") else "No",
                }
                for p in procedures
            ],
            use_container_width=True,
        )

    st.divider()
    st.write("**All patients:**")
    st.dataframe(
        [
            {
                "Name": p["display_name"],
                "Age": p.get("age") or "",
                "Sex": p.get("sex") or "",
            }
            for p in patients
        ],
        use_container_width=True,
    )
