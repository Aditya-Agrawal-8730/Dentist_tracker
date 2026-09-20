"""Shared auth guard used by every page (Streamlit multipage nav can jump
directly to a page's URL, bypassing app.py, so each page must check too)."""

import streamlit as st


def require_auth():
    if not st.session_state.get("authenticated"):
        st.error("Please log in from the main page first.")
        st.stop()

    with st.sidebar:
        if st.button("Log out"):
            st.session_state.clear()
            st.rerun()
