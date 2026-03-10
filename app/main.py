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
    folder_path = os.path.join(base_path, "..", "DataProcess", "Unified_Countries")

    # fallback: if the relative path doesn't work try an absolute path
    if not os.path.exists(folder_path):
        folder_path = "DataProcess/Unified_Countries"

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

    # --- Country Selection ---
    st.sidebar.header("Filters")

    if not df.empty:
        # use the unique countries from the loaded DataFrame to populate the selectbox, ensuring that it reflects the actual data available. This also allows for dynamic updates if new country data is added in the future.
        selected_country = st.sidebar.selectbox("Select Country", df['country'].unique())

        # filter by the country
        country_df = df[df['country'] == selected_country]
    else:
        st.sidebar.warning("No data found")
        selected_country = None
        country_df = df

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

if not df.empty:
    # autocomplete search box for places, showing all places from the entire dataset (not just the selected country) to allow users to find specific attractions even if they don't know which country they belong to. The search box will be placed above the category filters for better visibility and accessibility.
    all_place_names = ["-- Search or Select a Place --"] + sorted(df['place'].unique().tolist())

    selected_place_name = st.selectbox(
        "🔍 Search for a specific place (Global):",
        options=all_place_names,
        index=0,
        help="Start typing to find a specific attraction from any country in the database."
    )

    # chose from categories
    categories_list = ['nature', 'adventure', 'culture', 'food', 'romance', 'family', 'cost', 'relaxation']
    selected_cats = st.multiselect(
        "🎯 Filter by Categories",
        options=[c.capitalize() for c in categories_list],
        default=["Nature"]
    )

    # make sliders for each selected category, allowing users to set a minimum rating for each category. This will help them find places that match their preferences more closely. The sliders will only appear if the user has selected at least one category from the multiselect.
    cat_thresholds = {}
    if selected_cats:
        st.write("---")
        st.markdown("##### ⚙️ Set Minimum Rating for Each Category")
        cols = st.columns(3)
        for i, cat in enumerate(selected_cats):
            with cols[i % 3]:
                cat_thresholds[cat.lower()] = st.slider(f"Min {cat}", 0, 10, 5, key=f"slider_{cat}")
        st.write("---")

    # --- filter logic ---
    # check if the user is actively searching for a specific place (i.e., if the selected place name is not the default placeholder). If they are searching, we will bypass the category filters and show only the selected place. If they are not searching, we will apply the category filters to show relevant places based on their preferences.
    is_searching = selected_place_name != "-- Search or Select a Place --"

    if is_searching:
        # if searching for a specific place, we will ignore the category filters and show only the place that matches the selected name. This allows users to quickly find and add a specific attraction without having to adjust the filters.
        filtered_df = df[df['place'] == selected_place_name].copy()
    else:
        # else, filter by the selected country (if any) and then apply the category filters. This will show users a list of attractions that match their preferences based on the categories they selected and the minimum ratings they set.
        filtered_df = df.copy()
        if selected_country:
            filtered_df = filtered_df[filtered_df['country'] == selected_country]

        if selected_cats:
            for cat, threshold in cat_thresholds.items():
                filtered_df = filtered_df[filtered_df[cat] >= threshold]

        # pull the rated categories for the selected place and calculate a combined score based on the average of the selected categories. This will allow us to sort the results by relevance to the user's preferences, showing the most relevant attractions at the top of the list. The combined score will only be calculated if there are results to show and if the user has selected at least one category.
        if not filtered_df.empty and selected_cats:
            available_cats = [c.lower() for c in selected_cats if c.lower() in filtered_df.columns]
            filtered_df['combined_score'] = filtered_df[available_cats].mean(axis=1)
            filtered_df = filtered_df.sort_values(by='combined_score', ascending=False)

    # --- show result ---
    # the label for the results expander will dynamically show the number of places found based on the current filters and search term. This provides immediate feedback to users about how many attractions match their criteria, helping them understand the impact of their selections and encouraging them to adjust filters if they want to see more or fewer results.
    results_label = f"📍 View Results ({len(filtered_df)} found)"

    with st.expander(results_label, expanded=is_searching):
        if not filtered_df.empty:
            for idx, row in filtered_df.iterrows():
                with st.container():
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"### {row['place']} ({row['country']})")
                        st.write(row['description'])

                        # RATING DISPLAY LOGIC:
                        # Specific Search: Show all categories with a score > 0.
                        if is_searching:
                            all_ratings = [f"**{c.capitalize()}:** {row[c]}" for c in categories_list if row[c] > 0]
                            st.markdown(f"⭐ {' | '.join(all_ratings)}")

                        # Filter Mode: Show only the categories explicitly selected by the user.
                        elif selected_cats:
                            ratings_text = " | ".join(
                                [f"**{c.capitalize()}:** {row[c.lower()]}" for c in selected_cats])
                            st.markdown(f"⭐ {ratings_text}")

                        # Default View: No search and no filters selected.
                        # We display all relevant ratings (score > 0) to give the user an immediate overview
                        # of the attraction's characteristics without requiring any interaction.
                        else:
                            default_ratings = [f"**{c.capitalize()}:** {row[c]}" for c in categories_list if row[c] > 0]
                            if default_ratings:
                                st.markdown(f"⭐ {' | '.join(default_ratings)}")

                        st.caption(f"**Summary:** {row['short_summary']}")

                    with c2:
                        day_val = st.number_input("Assign Day", min_value=1, max_value=30, value=1, key=f"day_{idx}")

                    with c3:
                        st.write("##")  # Alignment spacer
                        if st.button("➕ Add", key=f"btn_{idx}", use_container_width=True):
                            new_entry = row.copy()
                            new_entry['day'] = day_val
                            curr_name = st.session_state.current_route
                            st.session_state.all_itineraries[curr_name] = pd.concat(
                                [st.session_state.all_itineraries[curr_name], pd.DataFrame([new_entry])],
                                ignore_index=True
                            )
                            st.toast(f"Added {row['place']} to {curr_name}!")
                    st.divider()
        else:
            st.info("No places match your criteria. Try adjusting the filters or search term.")

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

    curr_itinerary = curr_itinerary.sort_values(by='day')
    edited_df = st.data_editor(
        curr_itinerary,
        column_order=("day", "place", "country", "description"),
        column_config={
            "day": st.column_config.NumberColumn("Day", min_value=1, step=1, required=True),
            "place": st.column_config.TextColumn("Place", disabled=True),
            "description": st.column_config.TextColumn("Description", width="large")
        },
        num_rows="dynamic", use_container_width=True, key="itinerary_editor"
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
                # 1. הכנת שמות הקבצים והנתיבים
                route_name = st.session_state.current_route.replace(" ", "_")
                pdf_filename = f"{route_name}.pdf"
                kml_filename = f"{route_name}.kml"

                pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
                kml_path = os.path.join(OUTPUT_FOLDER, kml_filename)

                # 2. שימוש במחלקת Integrator (כולל ה-KML)
                integrator = GoogleMapsIntegrator(curr_itinerary)

                # יצירת ה-URL למפות
                full_route_url = integrator.generate_directions_url()

                # יצירת קובץ ה-KML ושמירתו בתיקייה
                integrator.create_kml_file(kml_path)

                # 3. יצירת ה-PDF ושמירתו בתיקייה
                df_stations = pd.DataFrame(st.session_state.stations) if st.session_state.stations else None
                maker = pdfMaker(
                    curr_itinerary,
                    customer_name=customer_name,
                    route_url=full_route_url,
                    stations_data=df_stations
                )
                maker.create_pdf(pdf_path)

                st.success(f"✅ Files saved to: `{OUTPUT_FOLDER}/`")

                # 4. כפתורי הורדה למשתמש
                col_pdf, col_kml = st.columns(2)

                with col_pdf:
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "📥 Download PDF",
                            f,
                            file_name=pdf_filename,
                            mime="application/pdf",
                            use_container_width=True
                        )

                with col_kml:
                    with open(kml_path, "r", encoding="utf-8") as f:
                        st.download_button(
                            "🗺️ Download KML (Google Earth)",
                            f,
                            file_name=kml_filename,
                            mime="application/vnd.google-earth.kml+xml",
                            use_container_width=True
                        )

            except Exception as e:
                st.error(f"Error during export: {e}")