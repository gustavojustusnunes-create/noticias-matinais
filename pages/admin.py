"""
pages/admin.py — Rota Standalone do Cockpit do CPO do All News Journal
"""
import streamlit as st
from cpo_cockpit import render_cpo_cockpit

st.set_page_config(
    page_title="Cockpit CPO — All News Journal",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={'Get Help': None, 'Report a bug': None, 'About': None}
)

render_cpo_cockpit()
