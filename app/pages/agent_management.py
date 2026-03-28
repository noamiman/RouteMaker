import streamlit as st
import json
import os
import pandas as pd
import sys
import time

# --- 1. תיקון נתיבי ייבוא ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from scrappers.chkAgent import LLMManager, find_relevant_posts, extract_data_from_post
except ImportError:
    st.error("Module 'scrappers' not found. Check folder structure.")
    st.stop()

# --- 2. ניהול מצב (Session State) ---
if 'use_local' not in st.session_state:
    st.session_state.use_local = False
if 'is_running' not in st.session_state:
    st.session_state.is_running = False
if 'found_urls' not in st.session_state:
    st.session_state.found_urls = {}
if 'current_extracted_data' not in st.session_state:
    st.session_state.current_extracted_data = []

# --- 3. הגדרות נתיבים ---
CONFIG_PATH = os.path.join(project_root, "blogs.json")
OUTPUT_FOLDER = os.path.join(project_root, "scrappers")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def load_blogs():
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    return []


def save_blogs(data):
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# --- 4. ממשק המשתמש (UI) ---
st.set_page_config(page_title="Agent Management", page_icon="🤖", layout="wide")

# CSS קטן לשיפור הנראות של הכפתורים
st.markdown("""
    <style>
    .stButton>button[kind="primary"] { background-color: #ff4b4b; border-color: #ff4b4b; }
    .stButton>button[kind="secondary"] { background-color: #3d4452; }
    </style>
    """, unsafe_allow_html=True)

st.title("🤖 AI Travel Agent Control Panel")

blogs_config = load_blogs()

# --- 5. Sidebar: ניהול מקורות והגדרות ---
with st.sidebar:
    st.header("⚙️ Control Center")

    # כפתור כיבוי מערכת - STOP
    if st.session_state.is_running:
        if st.button("🛑 STOP SYSTEM", type="primary", use_container_width=True, key="stop_btn"):
            st.session_state.is_running = False
            st.session_state.found_urls = {}
            st.session_state.current_extracted_data = []
            st.warning("System stopped by user.")
            st.rerun()

    st.divider()

    st.session_state.use_local = st.toggle("Force Ollama (Local Mode)", value=st.session_state.use_local,
                                           key="model_toggle")

    if st.button("🧹 Clear Logs & Cache", key="clear_cache_btn"):
        st.session_state.found_urls = {}
        st.session_state.current_extracted_data = []
        st.rerun()

    st.divider()

    # הוספה/מחיקה של בלוג
    with st.expander("📝 Manage Blogs"):
        new_b = st.text_input("New Blog Name", key="add_blog_name_input")
        new_u = st.text_input("Base URL", key="add_blog_url_input")

        if st.button("Add Blog", key="add_blog_btn"):
            if new_b and new_u:
                # בדיקה אם הבלוג קיים
                blog_exists = any(b['blog_name'].lower() == new_b.lower() for b in blogs_config)
                if blog_exists:
                    st.error(f"🚫 Blog '{new_b}' already exists.")
                else:
                    blogs_config.append({"blog_name": new_b, "base_url": new_u, "destinations": []})
                    save_blogs(blogs_config)
                    st.success(f"✅ Added {new_b}")
                    time.sleep(1)
                    st.rerun()

        st.write("---")
        if blogs_config:
            b_del = st.selectbox("Delete Blog", [b['blog_name'] for b in blogs_config], key="selectbox_del_blog")
            if st.button("🗑️ Delete Selected Blog", type="secondary", key="del_blog_btn"):
                blogs_config = [b for b in blogs_config if b['blog_name'] != b_del]
                save_blogs(blogs_config)
                st.success(f"🗑️ Deleted {b_del}")
                time.sleep(1)
                st.rerun()

    # הוספה/מחיקה של יעד
    with st.expander("📍 Manage Destinations"):
        if blogs_config:
            b_target = st.selectbox("Select Blog for Dest", [b['blog_name'] for b in blogs_config],
                                    key="selectbox_target_blog_dest")
            d_country = st.text_input("Country", key="add_dest_country_input")
            d_url = st.text_input("Guide URL", key="add_dest_url_input")

            if st.button("Add Destination", key="add_dest_btn"):
                if d_country and d_url:
                    # מציאת הבלוג
                    target_blog = next(b for b in blogs_config if b['blog_name'] == b_target)
                    # בדיקת כפילות יעד
                    dest_exists = any(d['country'].lower() == d_country.lower() for d in target_blog['destinations'])

                    if dest_exists:
                        st.error(f"🚫 Destination '{d_country}' already exists in {b_target}.")
                    else:
                        for b in blogs_config:
                            if b['blog_name'] == b_target:
                                b['destinations'].append({"country": d_country, "category_url": d_url})
                                break
                        save_blogs(blogs_config)
                        st.success(f"✅ Added {d_country} to {b_target}")
                        time.sleep(1)
                        st.rerun()

            st.write("---")
            curr_b = next(b for b in blogs_config if b['blog_name'] == b_target)
            if curr_b['destinations']:
                # כאן הוספנו KEY ייחודי כדי לפתור את השגיאה שקיבלת
                d_del = st.selectbox("Delete Dest", [d['country'] for d in curr_b['destinations']],
                                     key="selectbox_del_dest_key")
                if st.button("🗑️ Delete Dest", key="del_dest_btn"):
                    for b in blogs_config:
                        if b['blog_name'] == b_target:
                            b['destinations'] = [d for d in b['destinations'] if d['country'] != d_del]
                    save_blogs(blogs_config)
                    st.success(f"🗑️ Removed {d_del}")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Add a blog source first.")

# --- 6. בחירה והרצה ---
col_ctrl, col_log = st.columns([1, 2])

with col_ctrl:
    st.subheader("🚀 Run Scraper")
    blog_names = ["All"] + [b['blog_name'] for b in blogs_config]
    selected_blog = st.selectbox("Select Blog", blog_names)

    countries = ["All"]
    if selected_blog != "All":
        target = next(b for b in blogs_config if b['blog_name'] == selected_blog)
        countries += [d['country'] for d in target['destinations']]
    selected_country = st.selectbox("Select Country", countries)

    if st.button("▶️ Start Scraping", use_container_width=True, disabled=st.session_state.is_running):
        st.session_state.is_running = True
        st.session_state.current_extracted_data = []
        st.rerun()

# --- 7. לוגיקת הסריקה ---
if st.session_state.is_running:
    llm_service = LLMManager(use_local=st.session_state.use_local)
    tasks = []
    for b in blogs_config:
        if selected_blog == "All" or b['blog_name'] == selected_blog:
            for d in b['destinations']:
                if selected_country == "All" or d['country'] == selected_country:
                    tasks.append((b['blog_name'], d))

    if not tasks:
        st.warning("No tasks found.")
        st.session_state.is_running = False
    else:
        progress = st.progress(0)
        preview_table = st.empty()

        for i, (b_name, dest) in enumerate(tasks):
            task_key = f"{b_name}_{dest['country']}"
            with col_log:
                st.markdown(f"### 🌍 Processing: {dest['country']}")

                try:
                    # מציאת פוסטים
                    if task_key not in st.session_state.found_urls:
                        with st.spinner("Finding articles..."):
                            urls = find_relevant_posts(llm_service, dest['category_url'], dest['country'])
                            st.session_state.found_urls[task_key] = urls
                    else:
                        urls = st.session_state.found_urls[task_key]

                    for url_idx, url in enumerate(urls):
                        st.write(f"📄 ({url_idx + 1}/{len(urls)}) Scraping: {url}")
                        try:
                            with st.spinner("AI Analysis in progress..."):
                                data = extract_data_from_post(llm_service, url, dest['country'])

                            if data and data.places:
                                for p in data.places:
                                    row = p.model_dump()
                                    row['source_url'] = url
                                    row['blog_source'] = b_name
                                    st.session_state.current_extracted_data.append(row)

                                # עדכון תצוגה
                                with preview_table.container():
                                    st.write("📊 **Live Preview (Last 5):**")
                                    st.dataframe(pd.DataFrame(st.session_state.current_extracted_data).tail(5),
                                                 use_container_width=True)

                        except Exception as e:
                            # תפיסה מדויקת של שגיאת המכסה
                            if "GROQ_LIMIT_REACHED" in str(e) or "429" in str(e):
                                st.error("🚨 Groq Limit Reached!")
                                if st.button("🔄 Switch to Ollama and Continue", type="primary", key=f"fall_{url_idx}"):
                                    st.session_state.use_local = True
                                    st.rerun()
                                st.stop()
                            else:
                                st.error(f"Error at {url}: {e}")

                    # שמירה
                    if st.session_state.current_extracted_data:
                        df_res = pd.DataFrame(st.session_state.current_extracted_data)
                        csv_name = f"travel_data_{dest['country'].replace(' ', '_')}.csv"
                        df_res.to_csv(os.path.join(OUTPUT_FOLDER, csv_name), index=False, encoding='utf-8-sig')
                        st.success(f"✅ Saved {dest['country']}!")
                        st.session_state.current_extracted_data = []

                except Exception as e:
                    # אם זה קרה בשלב החיפוש
                    if "GROQ_LIMIT_REACHED" in str(e) or "429" in str(e):
                        st.error("🚨 Groq Limit Reached during search!")
                        if st.button("🔄 Switch to Ollama to Find Posts", type="primary", key="search_fall"):
                            st.session_state.use_local = True
                            st.rerun()
                        st.stop()
                    else:
                        st.error(f"Critical error: {e}")

            progress.progress((i + 1) / len(tasks))

        st.session_state.is_running = False
        st.balloons()