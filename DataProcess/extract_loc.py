import pandas as pd
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
import time


def get_enriched_travel_data(df, place_col, country_hint=""):
    """
    מבצע גיאוקודינג חכם על שמות מקומות בטבלה, כולל חילוץ עיר ומחוז.
    מונע כפילויות בריצה מול ה-API.
    """

    # 1. יצירת רשימת מקומות ייחודיים בלבד כדי לחסוך זמן וקריאות API
    unique_places = pd.DataFrame(df[place_col].unique(), columns=[place_col])

    # הגדרת הגיאוקודר (User Agent ייחודי חשוב מאוד)
    geolocator = Nominatim(user_agent="noam_bgu_final_project_v6")

    # הגדרת סדרי עדיפויות לחילוץ שדות מהכתובת (מבוסס על הניסיון הקודם)
    city_keys = ['city', 'town', 'village', 'municipality', 'suburb', 'city_district']
    state_keys = ['state', 'state_district', 'region']

    geo_results = []

    print(f"מתחיל לעבד {len(unique_places)} מקומות ייחודיים מתוך {len(df)} שורות סה\"כ...")

    for index, row in unique_places.iterrows():
        place_name = row[place_col]
        query = f"{place_name}, {country_hint}" if country_hint else place_name

        try:
            # בקשת הנתונים (addressdetails=True הוא קריטי לחילוץ העיר)
            location = geolocator.geocode(query, addressdetails=True, language='en', timeout=10)

            # גיבוי: אם לא נמצא עם המדינה, ננסה חיפוש גלובלי
            if not location and country_hint:
                location = geolocator.geocode(place_name, addressdetails=True, language='en')

            if location:
                addr = location.raw.get('address', {})

                # חילוץ עיר (לוקח את הראשון שנמצא ברשימת העדיפויות)
                city = next((addr[k] for k in city_keys if k in addr), "Unknown Area")

                # חילוץ מחוז/מדינה (State)
                state = next((addr[k] for k in state_keys if k in addr), "Unknown District")

                geo_results.append({
                    place_col: place_name,
                    'lat': location.latitude,
                    'lon': location.longitude,
                    'closest_city': city,
                    'state': state
                })
                print(f"הצלחתי: {place_name} -> {city}, {state}")
            else:
                geo_results.append({place_col: place_name, 'closest_city': None, 'state': None})
                print(f"לא נמצא מיקום עבור: {place_name}")

            # השהייה קלה כדי לא להיחסם (Rate Limiting)
            time.sleep(1.2)

        except Exception as e:
            print(f"שגיאה בעיבוד {place_name}: {e}")
            geo_results.append({place_col: place_name, 'closest_city': None, 'state': None})

    # 2. הפיכת התוצאות ל-DataFrame
    geo_df = pd.DataFrame(geo_results)

    # 3. חיבור (Merge) חזרה לטבלה הגדולה המקורית
    # זה מצמיד לכל שורת ביקורת את הנתונים הגיאוגרפיים המתאימים לה
    final_df = df.merge(geo_df, on=place_col, how='left')

    return final_df


# --- דוגמה לשימוש בסקריפט ---

if __name__ == "__main__":
    # נניח שזו הטבלה הגדולה שלך (למשל אחרי הסקריפינג)
    with open ("Unified_Countries/Thailand_processed.csv", "r", encoding="utf-8") as f:
        data = pd.read_csv(f)
    original_df = pd.DataFrame(data)

    # הפעלת הפונקציה
    enriched_df = get_enriched_travel_data(original_df, 'place', country_hint="thailand")

    # שמירה ל-CSV
    enriched_df.to_csv('final_enriched_data.csv', index=False)


    print("\n--- עיבוד הסתיים ---")
    print(enriched_df.head())