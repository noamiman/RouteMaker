import streamlit as st
import json
import os
import pandas as pd
import sys
import time

# --- 1. תיקון נתיבי ייבוא ומבנה פרויקט ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, "../../"))
SCRAPED_DATA_ROOT = os.path.join(project_root, "ScrapedData")

if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from scrappers.agent import LLMManager, find_relevant_posts, extract_data_from_post
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

# --- 3. הגדרות נתיבים לקבצים ---
CONFIG_PATH = os.path.join(project_root, "blogs.json")


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
    with st.expander("📝 Manage Blogs"):
        new_b = st.text_input("New Blog Name", key="add_blog_name_input")
        new_u = st.text_input("Base URL", key="add_blog_url_input")
        if st.button("Add Blog", key="add_blog_btn"):
            if new_b and new_u:
                blog_exists = any(b['blog_name'].lower() == new_b.lower() for b in blogs_config)
                if blog_exists:
                    st.error(f"🚫 Blog '{new_b}' already exists.")
                else:
                    blogs_config.append({"blog_name": new_b, "base_url": new_u, "destinations": []})
                    save_blogs(blogs_config)
                    st.success(f"✅ Added {new_b}")
                    time.sleep(1)
                    st.rerun()

    with st.expander("📍 Manage Destinations"):
        if blogs_config:
            b_target = st.selectbox("Select Blog for Dest", [b['blog_name'] for b in blogs_config])
            d_country = st.text_input("Country")
            d_url = st.text_input("Guide URL")
            if st.button("Add Destination"):
                if d_country and d_url:
                    target_blog = next(b for b in blogs_config if b['blog_name'] == b_target)
                    if any(d['country'].lower() == d_country.lower() for d in target_blog['destinations']):
                        st.error("🚫 Destination already exists.")
                    else:
                        target_blog['destinations'].append({"country": d_country, "category_url": d_url})
                        save_blogs(blogs_config)
                        st.success(f"✅ Added {d_country}")
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

# --- 7. לוגיקת הסריקה (החלק המעודכן) ---
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

            # 1. הכנת נתיבי השמירה מראש
            blog_folder_name = b_name.replace(" ", "_")
            target_dir = os.path.join(SCRAPED_DATA_ROOT, blog_folder_name)
            os.makedirs(target_dir, exist_ok=True)

            clean_country = dest['country'].replace(" ", "_")
            full_path = os.path.join(target_dir, f"travel_data_{clean_country}.csv")

            # 2. טעינת נתונים קיימים למניעת כפילויות
            existing_urls = set()
            if os.path.exists(full_path):
                try:
                    existing_df = pd.read_csv(full_path)
                    if 'source_url' in existing_df.columns:
                        existing_urls = set(existing_df['source_url'].unique())
                        # טוענים את הנתונים הקיימים ל-session_state כדי שהקובץ החדש יכלול גם אותם
                        st.session_state.current_extracted_data = existing_df.to_dict('records')
                except Exception as e:
                    st.error(f"Error loading existing CSV: {e}")

            with col_log:
                st.markdown(f"### 🌍 Processing: {dest['country']}")

                # מציאת פוסטים
                try:
                    if task_key not in st.session_state.found_urls:
                        with st.spinner("Finding articles..."):
                            urls = find_relevant_posts(llm_service, dest['category_url'], dest['country'])
                            st.session_state.found_urls[task_key] = urls
                    else:
                        urls = st.session_state.found_urls[task_key]

                    for url_idx, url in enumerate(urls):
                        # בדיקה אם ה-URL כבר נסרק
                        if url in existing_urls:
                            st.info(f"⏭️ Skipping (Already Scanned): {url}")
                            continue

                        st.write(f"📄 ({url_idx + 1}/{len(urls)}) Scraping: {url}")
                        try:
                            with st.spinner("AI Analysis..."):
                                data = extract_data_from_post(llm_service, url, dest['country'])

                            if data and data.places:
                                for p in data.places:
                                    row = p.model_dump()
                                    row['source_url'] = url
                                    row['blog_source'] = b_name
                                    st.session_state.current_extracted_data.append(row)

                                # --- שמירה מיידית אחרי כל פוסט ---
                                df_to_save = pd.DataFrame(st.session_state.current_extracted_data)
                                df_to_save.to_csv(full_path, index=False, encoding='utf-8-sig')

                                with preview_table.container():
                                    st.write(f"📊 **Live Preview ({dest['country']}):**")
                                    st.dataframe(df_to_save.tail(5), use_container_width=True)

                        except Exception as e:
                            if "429" in str(e) or "limit" in str(e).lower():
                                st.error("🚨 Groq Limit reached! Data up to this point is safe.")
                                if st.button("🔄 Switch to Ollama", type="primary"):
                                    st.session_state.use_local = True
                                    st.rerun()
                                st.stop()
                            else:
                                st.error(f"Error at {url}: {e}")

                except Exception as e:
                    st.error(f"Critical error in search: {e}")

            # איפוס לקראת המדינה הבאה במחזור ה-tasks
            st.session_state.current_extracted_data = []
            progress.progress((i + 1) / len(tasks))

        st.session_state.is_running = False
        st.balloons()