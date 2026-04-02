import os
import pandas as pd
from thefuzz import fuzz
import argparse

def aggregate_by_country_refined(root_dir, output_dir="../finalData"):
    os.makedirs(output_dir, exist_ok=True)
    countries_data = {}

    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith(".csv") and not any(x in file for x in ["_enriched", "_unified"]):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

                for _, row in df.iterrows():
                    country = str(row.get('country', os.path.basename(root))).strip()
                    place_name = str(row.get('place', '')).strip()
                    desc = str(row.get('description', '')).strip()

                    if not place_name or place_name.lower() == 'nan' or not desc or desc.lower() == 'nan':
                        continue

                    if country not in countries_data:
                        countries_data[country] = {}

                    found_match = None
                    for existing_name in countries_data[country].keys():
                        if fuzz.token_sort_ratio(place_name.lower(), existing_name.lower()) > 90:
                            found_match = existing_name
                            break

                    target_name = found_match if found_match else place_name

                    # 1. אתחול מקום חדש אם לא קיים
                    if target_name not in countries_data[country]:
                        countries_data[country][target_name] = {
                            "descriptions": [],
                            "google_maps_url": "",
                            "region": "",
                            "place_type": "",
                            "blog_source": ""
                        }

                    target_obj = countries_data[country][target_name]

                    # 2. הוספת תיאור (בדיקת כפילות פאזי)
                    is_duplicate_desc = False
                    for existing_desc in target_obj["descriptions"]:
                        if fuzz.ratio(desc.lower(), existing_desc.lower()) > 85:
                            is_duplicate_desc = True
                            break
                    if not is_duplicate_desc:
                        target_obj["descriptions"].append(desc)

                    # 3. עדכון שדות נוספים רק אם הם ריקים (כדי לא לדרוס מידע קיים)
                    if not target_obj["google_maps_url"]:
                        map_url = row.get('google_maps_url', row.get('map_link', ''))
                        if pd.notna(map_url) and str(map_url).strip() != '':
                            target_obj["google_maps_url"] = map_url

                    if not target_obj["region"]:
                        val = row.get('region', '')
                        if pd.notna(val): target_obj["region"] = str(val).strip()

                    if not target_obj["place_type"]:
                        val = row.get('place_type', '')
                        if pd.notna(val): target_obj["place_type"] = str(val).strip()

                    if not target_obj["blog_source"]:
                        val = row.get('blog_source', '')
                        if pd.notna(val): target_obj["blog_source"] = str(val).strip()

    # 4. יצירת ה-CSV לכל מדינה
    for country, places in countries_data.items():
        final_rows = []
        for name, info in places.items():
            for d in info["descriptions"]:
                final_rows.append({
                    "place": name,
                    "country": country,
                    "region": info["region"],
                    "description": d,
                    "place_type": info["place_type"],
                    "google_maps_url": info["google_maps_url"],
                    "blog_source": info["blog_source"]
                })

        if final_rows:
            country_df = pd.DataFrame(final_rows)
            country_df = country_df.fillna("")
            output_file = os.path.join(output_dir, f"{country}_processed.csv")
            country_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"✅ Saved {len(final_rows)} rows for {country}")

# Run
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aggregate travel data by country")
    parser.add_argument("--input", "-i", default="../ScrapedData",
                       help="Input directory containing scraped data")
    parser.add_argument("--output", "-o", default="../finalData",
                       help="Output directory for processed files")
    args = parser.parse_args()

    aggregate_by_country_refined(args.input, args.output)