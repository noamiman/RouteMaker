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
    folder_path = os.path.join(base_path, "..", "finalData")

    # fallback: if the relative path doesn't work try an absolute path
    if not os.path.exists(folder_path):
        folder_path = "../finalData"

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
if 'confirm_delete_route' not in st.session_state:
    st.session_state.confirm_delete_route = False
if 'confirm_clear_route' not in st.session_state:
    st.session_state.confirm_clear_route = False

# --- Sidebar: Settings & Emergency ---
with st.sidebar:
    st.title("⚙️ Trip Settings")
    customer_name = st.text_input("Traveler Name", "Avi Ron")

    # --- Country & Region Selection ---
    st.sidebar.header("Filters")

    if not df.empty:

        countries = sorted([str(c) for c in df['country'].unique() if pd.notna(c)])
        selected_country = st.sidebar.selectbox("Select Country", countries)

        # initial filtering of the DataFrame to the selected country to determine available regions for that country. This ensures that the region dropdown is dynamically populated based on the user's country selection, providing a more relevant and streamlined filtering experience.
        country_df = df[df['country'] == selected_country]

        # dinamic region dropdown based on the selected country, ensuring that users can only select regions that are relevant to their chosen country. This enhances the user experience by preventing irrelevant options and making the filtering process more intuitive.
        if 'region' in country_df.columns:
            available_regions = country_df['region'].dropna().unique().tolist()
        else:
            available_regions = []
        available_regions = sorted([str(r) for r in available_regions if str(r).strip() != ""])

        # all regions dropdown includes an "All Regions" option at the top, allowing users to easily reset the region filter and view all attractions within the selected country without having to manually deselect specific regions. This provides a convenient way for users to explore the full range of options available in that country.
        region_options = ["All Regions"] + available_regions

        selected_region = st.sidebar.selectbox(
            "Select Region",
            options=region_options,
            help=f"Available regions in {selected_country}"
        )

        # filter the country_df based on the selected region, ensuring that the main DataFrame used for displaying attractions is updated according to the user's region selection. If "All Regions" is selected, the filter is not applied, allowing users to see all attractions within the selected country regardless of region.
        if selected_region != "All Regions":
            filtered_country_df = country_df[country_df['region'] == selected_region]
        else:
            filtered_country_df = country_df

        # update the main DataFrame to be used for displaying attractions based on the selected country and region, ensuring that the app's content is relevant to the user's choices. This filtered DataFrame will be used in the main area of the app to show attractions that match the selected criteria.
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
                if st.session_state.get('confirm_delete_route', False):
                    del st.session_state.all_itineraries[st.session_state.current_route]
                    st.session_state.current_route = list(st.session_state.all_itineraries.keys())[0]
                    st.session_state.confirm_delete_route = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete_route = True
                    st.warning(f"⚠️ Click again to confirm deleting '{st.session_state.current_route}'")
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
    if 'place_type' in df.columns:
        all_types = sorted(df['place_type'].astype(str).unique().tolist())
    else:
        all_types = []
    selected_types = st.multiselect(
        "🏘️ Filter by Place Type",
        options=all_types,
        default=None,
        help="Select specific types of places like Hotels, Museums, Parks, etc."
    )

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
        filtered_df = df[df['place'] == selected_place_name].copy()
    else:
        filtered_df = df.copy()

        if selected_country:
            filtered_df = filtered_df[filtered_df['country'] == selected_country]

        if 'selected_region' in locals() and selected_region != "All Regions":
            filtered_df = filtered_df[filtered_df['region'] == selected_region]

        if selected_types:
            filtered_df = filtered_df[filtered_df['place_type'].astype(str).isin(selected_types)]

        if selected_cats:
            for cat in selected_cats:
                cat_lower = cat.lower()
                threshold = cat_thresholds.get(cat_lower, 0)
                filtered_df = filtered_df[filtered_df[cat_lower] >= threshold]

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

                        # Show description source metadata
                        desc_count = row.get('description_count', 1)
                        if pd.notna(desc_count) and desc_count > 0:
                            desc_count = int(desc_count)
                            st.caption(f"📊 Based on {desc_count} description{'s' if desc_count != 1 else ''}")

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
                            curr_name = st.session_state.current_route
                            curr_itinerary = st.session_state.all_itineraries[curr_name]
                            # Check for duplicates
                            if not curr_itinerary.empty and (curr_itinerary['place'] == row['place']).any():
                                st.warning(f"⚠️ '{row['place']}' is already in this trip!")
                            else:
                                new_entry = row.copy()
                                new_entry['day'] = day_val
                                st.session_state.all_itineraries[curr_name] = pd.concat(
                                    [curr_itinerary, pd.DataFrame([new_entry])],
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
        # Trip Overview Statistics
        with st.container():
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("📅 Total Days", int(curr_itinerary['day'].max()))
            with col2:
                st.metric("📍 Places", len(curr_itinerary))
            with col3:
                countries_count = curr_itinerary['country'].nunique()
                st.metric("🌍 Countries", countries_count)
            with col4:
                if 'place_type' in curr_itinerary.columns:
                    types_count = curr_itinerary['place_type'].nunique()
                    st.metric("🏘️ Types", types_count)
            with col5:
                if 'description_count' in curr_itinerary.columns:
                    avg_desc = curr_itinerary['description_count'].mean()
                    st.metric("📊 Avg Sources", f"{avg_desc:.1f}")
        st.divider()
        
        col_info, col_clear = st.columns([4, 1])
        with col_info:
            st.info(f"Editing **{st.session_state.current_route}**. Change 'Day' and save to re-sort.")
        with col_clear:
            if st.button("🗑️ Clear This Route", type="secondary", use_container_width=True):
                if st.session_state.get('confirm_clear_route', False):
                    st.session_state.all_itineraries[st.session_state.current_route] = pd.DataFrame(
                        columns=df.columns.tolist() + ['day'])
                    st.session_state.confirm_clear_route = False
                    st.rerun()
                else:
                    st.session_state.confirm_clear_route = True
                    st.warning(f"⚠️ Click again to confirm clearing '{st.session_state.current_route}'")

        # sort the itinerary by 'day' before displaying
        curr_itinerary = curr_itinerary.sort_values(by='day')

        # Timeline View
        with st.expander("📅 Timeline View", expanded=False):
            days = sorted(curr_itinerary['day'].unique())
            for day in days:
                day_places = curr_itinerary[curr_itinerary['day'] == day]
                st.markdown(f"### Day {int(day)} ({len(day_places)} places)")
                for _, place_row in day_places.iterrows():
                    # Create a visual card for each place in the timeline
                    col_icon, col_details = st.columns([0.8, 5])
                    with col_icon:
                        place_type = place_row.get('place_type', 'Place')
                        if place_type == 'Hotel':
                            st.markdown("🏨")
                        elif place_type == 'Restaurant':
                            st.markdown("🍽️")
                        elif place_type == 'Museum':
                            st.markdown("🏛️")
                        elif place_type == 'Park':
                            st.markdown("🌳")
                        elif place_type == 'Beach':
                            st.markdown("🏖️")
                        else:
                            st.markdown("📍")
                    with col_details:
                        st.markdown(f"**{place_row['place']}** • {place_row.get('country', '')} • {place_row.get('region', '')}")
                st.markdown("---")

        # edit the itinerary using the data editor, allowing changes to the 'day' column and displaying a clickable link for Google Maps. The 'place', 'region', 'place_type', 'country', and 'description' columns are disabled to prevent editing, while the 'google_maps_url' column is displayed as a link button that opens the location in Google Maps when clicked. The edited DataFrame is stored in `edited_df` for later saving.
        edited_df = st.data_editor(
            curr_itinerary,
            # organize columns in a logical order for itinerary editing, with 'day' first for easy sorting, followed by key place information and the Google Maps link at the end for quick access.
            column_order=("day", "place", "country", "region", "place_type", "description", "google_maps_url"),
            column_config={
                "day": st.column_config.NumberColumn("Day", min_value=1, step=1, required=True),
                "place": st.column_config.TextColumn("Place", disabled=True),
                "region": st.column_config.TextColumn("Region", disabled=True),
                "place_type": st.column_config.TextColumn("Place_Type", disabled=True),
                "country": st.column_config.TextColumn("Country", disabled=True),
                "description": st.column_config.TextColumn("Description", width="medium", disabled=True),
                # the 'google_maps_url' column is configured as a LinkColumn that validates URLs starting with "https://", displays a custom text "📍 Open Map", and is disabled to prevent editing while still allowing users to click the link to open the location in Google Maps.
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
                    # clean the itinerary data before exporting to ensure that the PDF and KML files are generated with valid and complete information. This includes removing rows without a place name, ensuring the 'day' column is properly formatted as integers, and filling any remaining NaN values with empty strings to prevent issues in the output files.
                    clean_itinerary = curr_itinerary.dropna(subset=['place']).copy()

                    # ensure 'day' is numeric and fill non-numeric or missing values with 1, then convert to integer type for proper sorting and display in the PDF.
                    clean_itinerary['day'] = pd.to_numeric(clean_itinerary['day'], errors='coerce').fillna(1).astype(
                        int)

                    # clean any remaining NaN values in the itinerary to prevent issues in the PDF and KML generation, ensuring that all fields have valid data (even if it's just an empty string) for consistent output formatting.
                    clean_itinerary = clean_itinerary.fillna("")

                    if clean_itinerary.empty:
                        st.error("The itinerary is empty. Add some places first!")
                        st.stop()
                    # -------------------------------------------

                    # make filenames safe and consistent by replacing spaces with underscores and using the current route name as the base for both the PDF and KML filenames. This ensures that the files are easily identifiable and organized in the output folder.
                    route_name = st.session_state.current_route.replace(" ", "_")
                    pdf_filename = f"{route_name}.pdf"
                    kml_filename = f"{route_name}.kml"

                    pdf_path = os.path.join(OUTPUT_FOLDER, pdf_filename)
                    kml_path = os.path.join(OUTPUT_FOLDER, kml_filename)

                    # name of the integrator class that takes the cleaned itinerary data and generates both the Google Maps directions URL and the KML file for mapping. This class is responsible for integrating the itinerary data with Google Maps to create a visual representation of the route and providing a downloadable KML file that can be used in various mapping applications.
                    integrator = GoogleMapsIntegrator(clean_itinerary)

                    # maps the itinerary data to a Google Maps directions URL that can be included in the PDF, allowing users to easily access the route on Google Maps directly from their itinerary guide. This URL is generated based on the places and their order in the cleaned itinerary, providing a convenient way for travelers to visualize their trip on a map.
                    full_route_url = integrator.generate_directions_url()

                    # create the kml file
                    integrator.create_kml_file(kml_path)

                    # make the pdf maker instance, passing the cleaned itinerary, customer name, Google Maps URL, and stations data (converted to a DataFrame if available) to generate a comprehensive PDF guide for the trip. The stations data is included in the PDF to provide travelers with important information about key locations such as hospitals and police stations along their route.
                    df_stations = pd.DataFrame(st.session_state.stations).fillna(
                        "") if st.session_state.stations else None

                    maker = pdfMaker(
                        clean_itinerary,
                        customer_name=customer_name,
                        route_url=full_route_url,
                        stations_data=df_stations
                    )
                    maker.create_pdf(pdf_path)

                    st.success(f"✅ Files saved to: `{OUTPUT_FOLDER}/`")

                    # provide download buttons for both the generated PDF and KML files, allowing users to easily download their itinerary guide and map. The buttons are displayed side by side for a convenient user experience, with appropriate icons and file type indications to clearly differentiate between the two types of files.
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