import streamlit as st

st.set_page_config(
    page_title="Travel Planner Pro",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ADMIN_MODE controls whether the Add Review and Agent Management pages appear.
# Set ADMIN_MODE = true in .streamlit/secrets.toml for local development.
# On the live Streamlit Cloud deployment, do not set this secret (defaults to False).
is_admin = st.secrets.get("ADMIN_MODE", False)

pages = [st.Page("pages/planner.py", title="Plan My Trip", default=True)]
if is_admin:
    pages += [
        st.Page("admin_pages/add_review.py", title="Add Review"),
        st.Page("admin_pages/agent_management.py", title="Agent Management"),
    ]

pg = st.navigation(pages)
pg.run()
