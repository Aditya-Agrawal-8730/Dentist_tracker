"""Entry point: password auth gate + intro page."""

import streamlit as st

st.set_page_config(page_title="Fellowship Tracker", page_icon="🦷", layout="wide")


def check_password() -> bool:
    if st.session_state.get("authenticated"):
        return True

    st.title("🦷 Fellowship Tracker")
    st.write("Enter the app password to continue.")

    password = st.text_input("Password", type="password")
    if st.button("Log in"):
        try:
            correct_password = st.secrets["APP_PASSWORD"]
        except Exception:
            st.error(
                "The app password hasn't been set up yet. Ask whoever set up this app "
                "to add APP_PASSWORD in the app's secrets."
            )
            return False

        if password == correct_password:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("That password isn't correct. Please try again.")

    return False


if not check_password():
    st.stop()

with st.sidebar:
    st.success("Logged in")
    if st.button("Log out"):
        st.session_state.clear()
        st.rerun()

st.title("🦷 Fellowship Tracker")
st.write(
    """
Welcome! Use the pages on the left to:

- **Daily Log** — type up today's cases in your own words (English or Hinglish is fine),
  review what the AI extracted, and confirm it.
- **Patients** — see your patient list and each patient's confirmed history.
- **Appointments** — keep track of upcoming and past appointments.
- **Report** — generate a narrative report for your fellowship over any date range.
"""
)
