import streamlit as st
import pandas as pd
import os

from output.pdf_maker import pdfMaker, GoogleMapsIntegrator

OUTPUT_FOLDER = "saved_itineraries"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# --- Default Stations Database ---
DEFAULT_STATIONS = {
    "Thailand": [
        {
            "name": "Tourist Police (English)",
            "desc": "Available 24/7 for tourists, speaks English.",
            "phone": "1155",
            "link": "https://www.google.com/maps/search/Tourist+Police"
        },
        {
            "name": "Bumrungrad International Hospital",
            "desc": "Top-tier medical care in Bangkok.",
            "phone": "+66 2 066 8888",
            "link": "https://goo.gl/maps/xyz"
        }
    ],
    "Vietnam": [
        {
            "name": "Tourist Police (English)",
            "desc": "Available 24/7 for tourists, speaks English.",
            "phone": "1155",
            "link": "https://www.google.com/maps/search/Tourist+Police"
        },
        {
            "name": "Bumrungrad International Hospital",
            "desc": "Top-tier medical care in Bangkok.",
            "phone": "+66 2 066 8888",
            "link": "https://goo.gl/maps/xyz"
        }
    ],
    "Israel": [
        {
            "name": "Magen David Adom",
            "desc": "Emergency Medical Services",
            "phone": "101",
            "link": "https://www.google.com/maps/search/MDA"
        }
    ]
}

# --- Page Configuration ---
st.set_page_config(
    page_title="Travel Planner Pro",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
    <style>
    h1, h2, h3, span, label, .stMarkdown p { color: #ffffff !important; }
    .stExpander {
        background-color: #1e2129 !important;
        border: 1px solid #3d4452 !important;
        border-radius: 12px !important;
        margin-bottom: 10px !important;
    }
    input, textarea, [data-baseweb="select"] > div {
        background-color: #0e1117 !important;
        color: #ffffff !important;
        border: 1px solid #3d4452 !important;
    }
    .stButton>button { border-radius: 8px !important; font-weight: bold !important; }
    section[data-testid="stSidebar"] { background-color: #0e1117 !important; }
    
    .back-to-top {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background-color: #3d4452;
        color: white !important;
        padding: 10px 15px;
        border-radius: 50px;
        text-decoration: none;
        font-weight: bold;
        z-index: 1000;
        border: 1px solid #ffffff33;
        transition: 0.3s;
    }
    .back-to-top:hover {
        background-color: #1e2129;
        transform: scale(1.1);
    }
    </style>
    """, unsafe_allow_html=True)


# --- Data Loading (Multi-Country Support) ---

@st.cache_data
def load_all_countries_data():
    """
    load and unify all country CSV files into a single DataFrame. It looks for CSV files in the specified folder,
     reads them, and concatenates them into one DataFrame.
      If the folder or files are not found, it returns an empty DataFrame and shows an error message.
    :return:
    """
    base_path = os.path.dirname(__file__)
    # define the path to the folder containing the unified country CSVs, relative to this file
    # folder_path = os.path.join(base_path, "..", "DataProcess", "Unified_Countries")
    folder_path = os.path.join(base_path, "..", "scrappers")


    # fallback: if the relative path doesn't work try an absolute path
    if not os.path.exists(folder_path):
        folder_path = "../scrappers"
        # folder_path = "../DataProcess/Unified_Countries"

    all_dfs = []

    try:
        if os.path.exists(folder_path):
            # list all CSV files in the folder
            files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]

            if not files:
                st.error(f"No CSV files found in {folder_path}")
                return pd.DataFrame()

            for file in files:
                file_full_path = os.path.join(folder_path, file)
                temp_df = pd.read_csv(file_full_path)
                all_dfs.append(temp_df)

            # concatenate all DataFrames into one
            full_df = pd.concat(all_dfs, ignore_index=True)
            print(full_df.head(5))
            return full_df
        else:
            st.error(f"Directory not found: {folder_path}")
            return pd.DataFrame()

    except Exception as e:
        st.error(f"Error loading multiple countries: {e}")
        return pd.DataFrame()


# call the function to load all data at once
df = load_all_countries_data()

# --- Session State Management (Multi-Route) ---
if 'all_itineraries' not in st.session_state:
    # initializing with a default route to ensure the app has something to work with on first load. Users can create new routes or delete this one as needed.
    st.session_state.all_itineraries = {"My First Trip": pd.DataFrame(columns=df.columns.tolist() + ['day'])}
if 'current_route' not in st.session_state:
    st.session_state.current_route = "My First Trip"
if 'stations' not in st.session_state:
    st.session_state.stations = []

# --- Sidebar: Settings & Emergency ---
with st.sidebar:
    st.title("⚙️ Trip Settings")
    customer_name = st.text_input("Traveler Name", "Avi Ron")

    # --- Country & Region Selection ---
    st.sidebar.header("Filters")

    if not df.empty:
        # 1. בחירת מדינה
        # המרה לסטרינג וסינון ערכים ריקים לפני המיון
        countries = sorted([str(c) for c in df['country'].unique() if pd.notna(c)])
        selected_country = st.sidebar.selectbox("Select Country", countries)

        # פילטר ראשוני לפי המדינה שנבחרה כדי לקבל את האזורים הרלוונטיים
        country_df = df[df['country'] == selected_country]

        # 2. בחירת Region (דינמי לפי המדינה)
        # מוציאים את כל האזורים הייחודיים, מסירים ערכי NaN וממיינים
        available_regions = country_df['region'].dropna().unique().tolist()
        available_regions = sorted([str(r) for r in available_regions if str(r).strip() != ""])

        # הוספת אופציית "All Regions" כברירת מחדל
        region_options = ["All Regions"] + available_regions

        selected_region = st.sidebar.selectbox(
            "Select Region",
            options=region_options,
            help=f"Available regions in {selected_country}"
        )

        # פילטר סופי של ה-DataFrame לפי המדינה והאזור
        if selected_region != "All Regions":
            filtered_country_df = country_df[country_df['region'] == selected_region]
        else:
            filtered_country_df = country_df

        # עדכון המשתנה country_df שבו משתמשים בהמשך הקוד (בלוגיקת הסינון המרכזית)
        country_df = filtered_country_df

    else:
        st.sidebar.warning("No data found")
        selected_country = None
        selected_region = "All Regions"
        country_df = df
    # --- Route Management ---
    st.divider()
    st.subheader("🗺️ Manage Routes")

    # check if session state has the necessary keys, if not initialize them with default values. This ensures that the app can handle multiple routes and that there's always at least one route available for the user to interact with.
    if 'all_itineraries' not in st.session_state:
        st.session_state.all_itineraries = {"Default Trip": pd.DataFrame(columns=df.columns.tolist() + ['day'])}
    if 'current_route' not in st.session_state:
        st.session_state.current_route = list(st.session_state.all_itineraries.keys())[0]

    route_list = list(st.session_state.all_itineraries.keys())

    # choice and deletion of active route
    col_sel, col_del_route = st.columns([4, 1])
    with col_sel:
        st.session_state.current_route = st.selectbox(
            "Active Route:",
            options=route_list,
            index=route_list.index(st.session_state.current_route)
        )

    with col_del_route:
        st.write("##")
        if st.button("🗑️", help="Delete current route", key="del_active_route"):
            if len(route_list) > 1:
                del st.session_state.all_itineraries[st.session_state.current_route]
                st.session_state.current_route = list(st.session_state.all_itineraries.keys())[0]
                st.rerun()
            else:
                st.warning("Cannot delete the only route.")

    # creation and duplication of routes
    with st.expander("➕ Create / Duplicate"):
        new_name = st.text_input("New Route Name:")
        c_new, c_dup = st.columns(2)
        if c_new.button("New Empty", use_container_width=True):
            if new_name and new_name not in st.session_state.all_itineraries:
                st.session_state.all_itineraries[new_name] = pd.DataFrame(columns=df.columns.tolist() + ['day'])
                st.session_state.current_route = new_name
                st.rerun()
        if c_dup.button("Duplicate", use_container_width=True):
            if new_name and new_name not in st.session_state.all_itineraries:
                st.session_state.all_itineraries[new_name] = st.session_state.all_itineraries[
                    st.session_state.current_route].copy()
                st.session_state.current_route = new_name
                st.rerun()

    # Merge routes into a new one
    with st.expander("🔗 Merge Routes"):
        st.caption("Combine two routes into a new one")
        route_a = st.selectbox("First Route", options=route_list, key="merge_a")
        route_b = st.selectbox("Second Route", options=route_list, key="merge_b")
        merged_name = st.text_input("Merged Route Name:", placeholder="Combined Trip")

        if st.button("Merge Now", use_container_width=True, type="primary"):
            if merged_name and merged_name not in st.session_state.all_itineraries:
                df_a = st.session_state.all_itineraries[route_a]
                df_b = st.session_state.all_itineraries[route_b]
                combined_df = pd.concat([df_a, df_b], ignore_index=True)
                st.session_state.all_itineraries[merged_name] = combined_df
                st.session_state.current_route = merged_name
                st.success(f"Merged into {merged_name}!")
                st.rerun()
            else:
                st.error("Please provide a unique name.")


    # --- 3. Key Stations & Emergency ---
    st.subheader("🏥 Key Stations & Emergency")

    if st.session_state.stations:
        if st.button("🗑️ Clear All Saved Stations", type="secondary", use_container_width=True):
            st.session_state.stations = []
            st.rerun()

    if selected_country and selected_country in DEFAULT_STATIONS:
        if st.checkbox(f"Use Defaults for {selected_country}", key="use_defaults"):
            for ds in DEFAULT_STATIONS[selected_country]:
                if not any(s['station name'] == ds['name'] for s in st.session_state.stations):
                    st.session_state.stations.append({
                        'station name': ds['name'],
                        'description': ds['desc'],
                        'phone': ds['phone'],
                        'google maps link': ds['link']
                    })
            st.caption(f"✅ Loaded {selected_country} defaults")

    with st.expander("➕ Add Custom Station"):
        with st.form("add_station_form", clear_on_submit=True):
            s_name = st.text_input("Station Name")
            s_desc = st.text_area("Description")
            s_phone = st.text_input("Phone")
            s_link = st.text_input("Maps Link")

            col_add, col_reset = st.columns(2)
            submit_add = col_add.form_submit_button("➕ Add", use_container_width=True)
            submit_clear = col_reset.form_submit_button("🧹 Clear", use_container_width=True)

            if submit_add:
                if s_name:
                    st.session_state.stations.append({
                        'station name': s_name,
                        'description': s_desc,
                        'phone': s_phone,
                        'google maps link': s_link
                    })
                    st.toast(f"Added {s_name}!")
                    st.rerun()
                else:
                    st.error("Please enter a name")

    # manage existing stations
    if st.session_state.stations:
        st.write("---")
        for i, s in enumerate(st.session_state.stations):
            col_txt, col_btn = st.columns([4, 1])
            col_txt.caption(f"{i + 1}. {s['station name']}")
            if col_btn.button("🗑️", key=f"del_st_{i}"):
                st.session_state.stations.pop(i)
                st.rerun()
# --- Main Area: Discovery ---
st.title(f"🌍 Editing: {st.session_state.current_route}")
st.markdown("<div id='top'></div>", unsafe_allow_html=True)

if not df.empty:
    # 1. Autocomplete Search
    all_place_names = ["-- Search or Select a Place --"] + sorted(df['place'].unique().tolist())
    selected_place_name = st.selectbox(
        "🔍 Search for a specific place (Global):",
        options=all_place_names,
        index=0,
        help="Start typing to find a specific attraction from any country in the database."
    )

    # 2. Category Filters
    categories_list = ['nature', 'adventure', 'culture', 'food', 'romance', 'family', 'cost', 'relaxation']
    selected_cats = st.multiselect(
        "🎯 Filter by Categories",
        options=[c.capitalize() for c in categories_list],
        default=[],
        help="Select categories to filter results"
    )

    # 3. Filter by Place Type
    all_types = sorted(df['place_type'].astype(str).unique().tolist())
    selected_types = st.multiselect(
        "🏘️ Filter by Place Type",
        options=all_types,
        default=None,
        help="Select specific types of places like Hotels, Museums, Parks, etc."
    )

    # 4. Dynamic Sliders (מציג סליידרים רק אם נבחרו קטגוריות)
    cat_thresholds = {}
    if selected_cats:
        st.write("---")
        st.markdown("##### ⚙️ Set Minimum Rating for Each Category")
        cols = st.columns(3)
        for i, cat in enumerate(selected_cats):
            with cols[i % 3]:
                cat_thresholds[cat.lower()] = st.slider(f"Min {cat}", 0, 10, 5, key=f"slider_{cat}")
        st.write("---")

    # --- FILTER LOGIC ---
    is_searching = selected_place_name != "-- Search or Select a Place --"

    if is_searching:
        # אם מחפשים מקום ספציפי - מתעלמים משאר הפילטרים
        filtered_df = df[df['place'] == selected_place_name].copy()
    else:
        # מתחילים עם עותק של הנתונים
        filtered_df = df.copy()

        # 1. סינון לפי מדינה
        if selected_country:
            filtered_df = filtered_df[filtered_df['country'] == selected_country]

        # 2. סינון לפי Region (התוספת החדשה!)
        # אנחנו בודקים אם נבחר region ספציפי (שהוא לא "All Regions")
        if 'selected_region' in locals() and selected_region != "All Regions":
            filtered_df = filtered_df[filtered_df['region'] == selected_region]

        # 3. סינון לפי סוג מקום
        if selected_types:
            filtered_df = filtered_df[filtered_df['place_type'].astype(str).isin(selected_types)]

        # 4. סינון לפי קטגוריות ודירוג מינימלי
        if selected_cats:
            for cat in selected_cats:
                cat_lower = cat.lower()
                threshold = cat_thresholds.get(cat_lower, 0)
                filtered_df = filtered_df[filtered_df[cat_lower] >= threshold]

            # מיון לפי הציון הממוצע של הקטגוריות שנבחרו
            if not filtered_df.empty:
                available_cats = [c.lower() for c in selected_cats if c.lower() in filtered_df.columns]
                filtered_df['combined_score'] = filtered_df[available_cats].mean(axis=1)
                filtered_df = filtered_df.sort_values(by='combined_score', ascending=False)
    # --- SHOW RESULTS ---
    results_label = f"📍 View Results ({len(filtered_df)} found)"

    with st.expander(results_label, expanded=is_searching):
        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container():
                    col_info, col_action = st.columns([3.5, 1.5])

                    with col_info:
                        p_type = row.get('place_type', 'General')
                        st.markdown(f"### {row['place']}  `{p_type}`")

                        location_line = f"📍 **{row['country']}**"
                        region_val = row.get('region')
                        if pd.notna(region_val) and str(region_val).strip() != "":
                            location_line += f" | {region_val}"
                        st.markdown(location_line)

                        # כפתור מפה
                        maps_url = row.get('google_maps_url')
                        if pd.notna(maps_url) and maps_url != "":
                            btn_col, _ = st.columns([1.2, 2])
                            with btn_col:
                                st.link_button("🌐 Open Maps", maps_url, use_container_width=True)

                        st.write(row['description'])

                        # הצגת דירוגים
                        if is_searching:
                            ratings = [f"**{c.capitalize()}:** {row[c]}" for c in categories_list if row[c] > 0]
                            st.markdown(f"⭐ {' • '.join(ratings)}")
                        elif selected_cats:
                            ratings_text = " • ".join(
                                [f"**{c.capitalize()}:** {row[c.lower()]}" for c in selected_cats])
                            st.markdown(f"⭐ {ratings_text}")
                        else:
                            default_ratings = [f"**{c.capitalize()}:** {row[c]}" for c in categories_list if row[c] > 0]
                            if default_ratings:
                                st.markdown(f"⭐ {' • '.join(default_ratings)}")

                    with col_action:
                        st.write("##")
                        day_val = st.number_input("Assign Day", min_value=1, max_value=30, value=1, key=f"day_{idx}")
                        if st.button("➕ Add to Trip", key=f"btn_{idx}", use_container_width=True, type="primary"):
                            new_entry = row.copy()
                            new_entry['day'] = day_val
                            curr_name = st.session_state.current_route
                            st.session_state.all_itineraries[curr_name] = pd.concat(
                                [st.session_state.all_itineraries[curr_name], pd.DataFrame([new_entry])],
                                ignore_index=True
                            )
                            st.toast(f"Added **{row['place']}**!", icon="✅")

                    st.divider()
        else:
            st.info("No places match your criteria.")

# --- Itinerary Management ---
    st.header(f"📝 {st.session_state.current_route} Itinerary")
    curr_itinerary = st.session_state.all_itineraries[st.session_state.current_route]

    if not curr_itinerary.empty:
        col_info, col_clear = st.columns([4, 1])
        with col_info:
            st.info(f"Editing **{st.session_state.current_route}**. Change 'Day' and save to re-sort.")
        with col_clear:
            if st.button("🗑️ Clear This Route", type="secondary", use_container_width=True):
                st.session_state.all_itineraries[st.session_state.current_route] = pd.DataFrame(
                    columns=df.columns.tolist() + ['day'])
                st.rerun()

        # מיון לפי יום
        curr_itinerary = curr_itinerary.sort_values(by='day')

        # עריכת הטבלה עם עמודת קישור
        edited_df = st.data_editor(
            curr_itinerary,
            # הוספנו את google_maps_url לסדר העמודות
            column_order=("day", "place", "country", "region", "place_type", "description", "google_maps_url"),
            column_config={
                "day": st.column_config.NumberColumn("Day", min_value=1, step=1, required=True),
                "place": st.column_config.TextColumn("Place", disabled=True),
                "region": st.column_config.TextColumn("Region", disabled=True),
                "place_type": st.column_config.TextColumn("Place_Type", disabled=True),
                "country": st.column_config.TextColumn("Country", disabled=True),
                "description": st.column_config.TextColumn("Description", width="medium", disabled=True),
                # הגדרת עמודת הקישור ככפתור לחיץ
                "google_maps_url": st.column_config.LinkColumn(
                    "Maps Link",
                    help="Click to open in Google Maps",
                    validate=r"^https://.*",
                    display_text="📍 Open Map",
                    disabled=True
                )
            },
            num_rows="dynamic",
            use_container_width=True,
            key="itinerary_editor"
        )

        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            st.session_state.all_itineraries[st.session_state.current_route] = edited_df.sort_values(by='day')
            st.success("Changes saved!")
            st.rerun()

        st.write("---")
        # --- PDF & KML Export Section ---
        st.subheader("📤 Export Your Guide & Map")

        if st.button("🚀 Generate PDF & KML Map", use_container_width=True):
            with st.spinner("Processing files..."):
                try:
                    # --- שלב קריטי: ניקוי הנתונים לפני ייצוא ---
                    # 1. מסירים שורות שאין בהן שם מקום (שורות ריקות מהעורך)
                    clean_itinerary = curr_itinerary.dropna(subset=['place']).copy()

                    # 2. מוודאים שעמודת היום היא מספר שלם (int) וממלאים חסרים ב-1
                    clean_itinerary['day'] = pd.to_numeric(clean_itinerary['day'], errors='coerce').fillna(1).astype(
                        int)

                    # 3. ניקוי ערכי NaN כלליים בטקסט כדי שלא יופיע "nan" ב-PDF
                    clean_itinerary = clean_itinerary.fillna("")

                    if clean_itinerary.empty:
                        st.error("The itinerary is empty. Add some places first!")
                        st.stop()
                    # -------------------------------------------

                    # 1. הכנת שמות הקבצים והנתיבים
                    route_name = st.session_state.current_route.replace(" ", "_")
                    pdf_filename = f"{route_name}.pdf"
                    kml_filename = f"{route_name}.kml"

                    pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
                    kml_path = os.path.join(OUTPUT_FOLDER, kml_filename)

                    # 2. שימוש במחלקת Integrator עם הנתונים הנקיים
                    integrator = GoogleMapsIntegrator(clean_itinerary)

                    # יצירת ה-URL למפות
                    full_route_url = integrator.generate_directions_url()

                    # יצירת קובץ ה-KML
                    integrator.create_kml_file(kml_path)

                    # 3. יצירת ה-PDF עם הנתונים הנקיים
                    df_stations = pd.DataFrame(st.session_state.stations).fillna(
                        "") if st.session_state.stations else None

                    maker = pdfMaker(
                        clean_itinerary,  # משתמשים בגרסה הנקייה
                        customer_name=customer_name,
                        route_url=full_route_url,
                        stations_data=df_stations
                    )
                    maker.create_pdf(pdf_path)

                    st.success(f"✅ Files saved to: `{OUTPUT_FOLDER}/`")

                    # 4. כפתורי הורדה (נשאר ללא שינוי)
                    col_pdf, col_kml = st.columns(2)
                    with col_pdf:
                        with open(pdf_path, "rb") as f:
                            st.download_button("📥 Download PDF", f, file_name=pdf_filename, mime="application/pdf",
                                               use_container_width=True)
                    with col_kml:
                        with open(kml_path, "rb") as f:  # שיניתי ל-"rb" ליתר ביטחון
                            st.download_button("🗺️ Download KML", f, file_name=kml_filename,
                                               mime="application/vnd.google-earth.kml+xml", use_container_width=True)

                except Exception as e:
                    st.error(f"Error during export: {e}")