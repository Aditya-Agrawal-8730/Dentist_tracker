"""Daily Log: natural language entry -> LLM draft -> review/edit -> confirm -> save."""

import datetime

import streamlit as st

from lib import auth, db, llm

auth.require_auth()

st.title("📝 Daily Log")
st.write("Type up today's case(s) in your own words — English or Hinglish is fine.")

patients, patients_error = db.get_patients()
if patients_error:
    st.error(patients_error)
    patients = []

if "draft_fields" not in st.session_state:
    st.session_state.draft_fields = None
if "draft_raw_input" not in st.session_state:
    st.session_state.draft_raw_input = ""
if "draft_placeholder_map" not in st.session_state:
    st.session_state.draft_placeholder_map = {}
if "extraction_failed" not in st.session_state:
    st.session_state.extraction_failed = False

raw_text = st.text_area(
    "Today's entry",
    height=150,
    placeholder="e.g. Patient 14 ka Class II composite kiya tooth 36 pe, no complications, "
    "follow-up 2 weeks mein...",
)

if st.button("Process", type="primary"):
    if not raw_text.strip():
        st.warning("Please type something first.")
    else:
        with st.spinner("Reading through the entry..."):
            deid = llm.deidentify(raw_text, patients)
            fields, error = llm.extract_case(deid.text)
        st.session_state.draft_raw_input = raw_text
        st.session_state.draft_placeholder_map = deid.placeholder_map
        if error:
            st.session_state.extraction_failed = True
            st.session_state.draft_fields = None
            st.warning(
                f"The AI couldn't process this entry automatically ({error}). "
                "You can still fill in the details below by hand."
            )
        else:
            st.session_state.extraction_failed = False
            st.session_state.draft_fields = fields

show_form = st.session_state.draft_raw_input and (
    st.session_state.draft_fields is not None or st.session_state.extraction_failed
)

if show_form:
    st.divider()
    st.subheader("Review & confirm")

    if st.session_state.extraction_failed:
        st.info("Original text (AI extraction failed — fill in the fields manually):")
        st.code(st.session_state.draft_raw_input)

    fields = st.session_state.draft_fields or {}
    placeholder_map = st.session_state.draft_placeholder_map

    patient_options = ["-- New patient --"] + [p["display_name"] for p in patients]
    default_patient_id = None
    default_index = 0
    if fields.get("patient_placeholder") in placeholder_map:
        default_patient_id = placeholder_map[fields["patient_placeholder"]]
        for i, p in enumerate(patients):
            if p["id"] == default_patient_id:
                default_index = i + 1
                break

    selected_patient_label = st.selectbox("Patient", patient_options, index=default_index)

    new_patient_name = new_patient_age = new_patient_sex = new_patient_notes = None
    if selected_patient_label == "-- New patient --":
        st.write("This entry references a new patient — create their record:")
        col1, col2, col3 = st.columns(3)
        with col1:
            new_patient_name = st.text_input(
                "Display name (local identifier only, e.g. 'Patient 14' or initials)"
            )
        with col2:
            new_patient_age = st.number_input("Age", min_value=0, max_value=120, value=0)
        with col3:
            new_patient_sex = st.selectbox("Sex", ["", "M", "F", "Other"])
        new_patient_notes = st.text_input("Notes (optional)")

    col1, col2 = st.columns(2)
    with col1:
        procedure_type = st.text_input(
            "Procedure type", value=fields.get("procedure_type", "")
        )
        tooth = st.text_input("Tooth", value=fields.get("tooth") or "")
    with col2:
        procedure_date = st.date_input("Date", value=datetime.date.today())
        complications = st.text_input(
            "Complications (leave blank if none)", value=fields.get("complications") or ""
        )

    description = st.text_area("Description", value=fields.get("description", ""))

    follow_up_needed = st.checkbox(
        "Follow-up needed", value=bool(fields.get("follow_up_needed", False))
    )
    follow_up_date = None
    if follow_up_needed:
        default_fu_date = datetime.date.today()
        if fields.get("follow_up_date"):
            try:
                default_fu_date = datetime.date.fromisoformat(fields["follow_up_date"])
            except ValueError:
                pass
        follow_up_date = st.date_input("Follow-up date", value=default_fu_date)

    can_save = bool(procedure_type.strip()) and (
        selected_patient_label != "-- New patient --" or bool((new_patient_name or "").strip())
    )

    if st.button("Confirm & Save", type="primary", disabled=not can_save):
        try:
            if selected_patient_label == "-- New patient --":
                new_patient, patient_error = db.create_patient(
                    display_name=new_patient_name.strip(),
                    age=int(new_patient_age) or None,
                    sex=new_patient_sex or None,
                    notes=new_patient_notes or None,
                )
                if patient_error:
                    st.error(patient_error)
                    st.stop()
                patient_id = new_patient["id"]
            else:
                idx = patient_options.index(selected_patient_label) - 1
                patient_id = patients[idx]["id"]

            procedure, proc_error = db.create_procedure(
                patient_id=patient_id,
                date=procedure_date,
                procedure_type=procedure_type.strip(),
                tooth=tooth or None,
                description=description or None,
                complications=complications or None,
                follow_up_needed=follow_up_needed,
                follow_up_date=follow_up_date,
                status="confirmed",
                raw_input=st.session_state.draft_raw_input,
            )
            if proc_error:
                st.error(proc_error)
                st.stop()

            log, log_error = db.create_daily_log(
                date=procedure_date,
                raw_input=st.session_state.draft_raw_input,
                parsed_summary=description or procedure_type,
                linked_procedure_ids=[procedure["id"]],
                status="confirmed",
            )
            if log_error:
                st.error(log_error)
                st.stop()

            st.success("Saved! This case is now part of the confirmed record.")
            st.session_state.draft_fields = None
            st.session_state.draft_raw_input = ""
            st.session_state.draft_placeholder_map = {}
            st.session_state.extraction_failed = False
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Something went wrong while saving. Details: {exc}")
