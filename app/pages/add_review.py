import streamlit as st
import pandas as pd
import os
from datetime import datetime


def load_existing_data():
    # הנתיב שציינת
    data_path = "finalData/Unified_Countries"

    if not os.path.exists(data_path):
        return pd.DataFrame()

    files = [f for f in os.listdir(data_path) if f.endswith('.csv')]
    if not files:
        return pd.DataFrame()

    # טעינת הקובץ הראשון שנמצא בתיקייה
    full_path = os.path.join(data_path, files[0])
    return pd.read_csv(full_path)


def save_review(review_data):
    reviews_file = "user_reviews.csv"
    df_new = pd.DataFrame([review_data])
    if os.path.exists(reviews_file):
        df_old = pd.read_csv(reviews_file)
        df_final = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_final = df_new
    df_final.to_csv(reviews_file, index=False, encoding='utf-8-sig')


st.set_page_config(
    page_title="Add Review",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

places_df = load_existing_data()

# יצירת רשימת מקומות בסיסית
if not places_df.empty:
    places_df.columns = [c.strip() for c in places_df.columns]
    place_list = sorted(places_df['place'].unique().tolist())
else:
    place_list = []

# הוספת אופציה של "מקום חדש" לראש הרשימה
NEW_PLACE_OPTION = "➕ Add New Place..."
options = [NEW_PLACE_OPTION] + place_list

with st.form("review_form"):
    st.subheader("Location Details")

    selected_option = st.selectbox("Select a place or add a new one:", options)

    # משתנים שיחזיקו את פרטי המקום
    final_place_name = ""
    final_country = ""
    final_region = ""
    final_place_type = ""

    # אם המשתמש בחר להוסיף מקום חדש
    if selected_option == NEW_PLACE_OPTION:
        st.info("Fill in the details for the new location:")
        final_place_name = st.text_input("Place Name*", placeholder="e.g. Kuang Si Falls")
        final_country = st.text_input("Country*", placeholder="e.g. Laos")
        final_region = st.text_input("Region/City", placeholder="e.g. Luang Prabang")
        final_place_type = st.text_input("Place Type", placeholder="e.g. Waterfall, Viewpoint, Temple...")
        final_url = st.text_input("Maps Url", placeholder="e.g. https://goo.gl/maps/...")

    else:
        # חילוץ מידע אוטומטי מה-CSV עבור מקום קיים
        place_info = places_df[places_df['place'] == selected_option].iloc[0]
        final_place_name = selected_option
        final_country = place_info.get('country', 'Unknown')
        final_region = place_info.get('region', 'Unknown')
        final_place_type = place_info.get('place_type', 'General')
        final_url = place_info.get('google_maps_url', 'Unknown')

        st.caption(f"Country: {final_country} | Region: {final_region}")

    st.divider()
    st.subheader("Ratings (1-10)")

    col1, col2 = st.columns(2)
    categories = [
        ('romance', '💕 Romance'), ('family', '👨‍👩‍👧‍👦 Family'),
        ('cost', '💰 Cost/Value'), ('nature', '🌿 Nature'),
        ('adventure', '🎒 Adventure'), ('culture', '🏛️ Culture'),
        ('food', '🍕 Food'), ('relaxation', '🧘 Relaxation'),
        ('service', '🛎️ Service'), ('accessibility', '♿ Accessibility')
    ]

    ratings = {}
    for i, (key, label) in enumerate(categories):
        with col1 if i % 2 == 0 else col2:
            ratings[key] = st.slider(label, 1, 10, 5)

    user_text = st.text_area("Your Review:", placeholder="How was your experience?")

    # כפתור השליחה
    submitted = st.form_submit_button("Submit Review ✅")

    if submitted:
        # בדיקה שהמשתמש מילא שם ומדינה אם זה מקום חדש
        if selected_option == NEW_PLACE_OPTION and (not final_place_name or not final_country):
            st.error("Please provide at least a name and a country for the new place.")
        else:
            review_entry = {
                "place": final_place_name,
                "country": final_country,
                "region": final_region,
                "place_type": final_place_type,
                "google_maps_url": final_url,
                "review_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "text": user_text,
                "is_manual_entry": True if selected_option == NEW_PLACE_OPTION else False,
                **ratings
            }

            save_review(review_entry)
            st.success(f"Review for {final_place_name} saved successfully!")
            st.balloons()