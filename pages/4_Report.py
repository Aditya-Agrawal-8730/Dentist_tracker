"""Report: date range -> stats + narrative from confirmed data -> download."""

import datetime
from collections import Counter

import streamlit as st

from lib import auth, db, llm

auth.require_auth()

st.title("📊 Fellowship Report")

col1, col2 = st.columns(2)
with col1:
    period_start = st.date_input(
        "From", value=datetime.date.today() - datetime.timedelta(days=30)
    )
with col2:
    period_end = st.date_input("To", value=datetime.date.today())

if "report_narrative" not in st.session_state:
    st.session_state.report_narrative = None
if "report_stats" not in st.session_state:
    st.session_state.report_stats = None

if st.button("Generate Report", type="primary"):
    if period_start > period_end:
        st.warning("'From' date must be before 'To' date.")
    else:
        procedures, proc_error = db.get_confirmed_procedures_in_range(period_start, period_end)
        if proc_error:
            st.error(proc_error)
        else:
            logs, log_error = db.get_daily_logs_in_range(
                period_start, period_end, confirmed_only=True
            )
            if log_error:
                st.error(log_error)
            elif not procedures:
                st.info("No confirmed procedures in this date range yet.")
            else:
                total = len(procedures)
                by_type = Counter(p["procedure_type"] for p in procedures)
                with_complications = sum(1 for p in procedures if p.get("complications"))
                with_follow_up = sum(1 for p in procedures if p.get("follow_up_needed"))

                stats = {
                    "period_start": str(period_start),
                    "period_end": str(period_end),
                    "total_procedures": total,
                    "procedure_counts_by_type": dict(by_type),
                    "complication_rate": round(with_complications / total, 3) if total else 0,
                    "follow_up_rate": round(with_follow_up / total, 3) if total else 0,
                }

                case_summaries = [
                    l.get("parsed_summary") for l in (logs or []) if l.get("parsed_summary")
                ]

                with st.spinner("Drafting narrative..."):
                    narrative, narrative_error = llm.generate_narrative(stats, case_summaries)

                if narrative_error:
                    st.warning(
                        f"Couldn't generate a narrative automatically ({narrative_error}). "
                        "You can write one manually below using the stats shown."
                    )
                    narrative = ""

                st.session_state.report_stats = stats
                st.session_state.report_narrative = narrative

if st.session_state.report_stats:
    st.divider()
    st.subheader("Stats")
    st.json(st.session_state.report_stats)

    st.subheader("Narrative (editable)")
    edited_narrative = st.text_area(
        "Narrative", value=st.session_state.report_narrative or "", height=250
    )

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Save snapshot"):
            snapshot, save_error = db.save_report_snapshot(
                period_start=period_start,
                period_end=period_end,
                content=edited_narrative,
                stats_json=st.session_state.report_stats,
            )
            if save_error:
                st.error(save_error)
            else:
                st.success("Report snapshot saved.")

    with col2:
        filename = f"fellowship_report_{period_start}_{period_end}.txt"
        st.download_button(
            "Download report",
            data=edited_narrative,
            file_name=filename,
            mime="text/plain",
        )
