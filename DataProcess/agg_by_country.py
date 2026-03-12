import os
import pandas as pd
from thefuzz import fuzz


def aggregate_by_country_refined(root_dir, output_dir="Unified_Countries"):
    """
    This function aggregates data from multiple CSV files in a directory structure organized by country, and creates unified CSV files for each country with de-duplication and fuzzy matching for place names and descriptions.
    :param root_dir: the root directory containing subdirectories for each country, which in turn contain CSV files with place data.
    :param output_dir: the directory where the unified CSV files will be saved, one for each country. Each file will contain columns for place name, country, description, and map link, with de-duplication applied to both place names and descriptions.
    :return: None, but saves the processed CSV files in the specified output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    # use a nested dictionary to store data by country and place name, with lists of descriptions for de-duplication
    countries_data = {}

    # Walk through the directory structure and read each CSV file
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            # Only process CSV files that are not already enriched or unified
            if file.endswith(".csv") and not any(x in file for x in ["_enriched", "_unified"]):
                file_path = os.path.join(root, file)
                try:
                    df = pd.read_csv(file_path)
                except Exception as e:
                    print(f"Error reading {file_path}: {e}")
                    continue

                for _, row in df.iterrows():
                    # clean and standardize the country, place name, and description fields
                    country = str(row.get('country', os.path.basename(root))).strip()
                    place_name = str(row.get('place', '')).strip()
                    desc = str(row.get('description', '')).strip()

                    # Skip rows with missing or invalid place names or descriptions
                    if not place_name or place_name.lower() == 'nan' or not desc or desc.lower() == 'nan':
                        continue

                    # Initialize the country entry if it doesn't exist
                    if country not in countries_data:
                        countries_data[country] = {}

                    # Fuzzy matching for place names to handle slight variations (e.g., "Bangkok" vs "Bangkok City")
                    found_match = None
                    # search for a similar place name in the existing data for the country, if we find one with a similarity score above 90, we will consider it the same place
                    for existing_name in countries_data[country].keys():
                        if fuzz.token_sort_ratio(place_name.lower(), existing_name.lower()) > 90:
                            found_match = existing_name
                            break

                    target_name = found_match if found_match else place_name

                    if target_name not in countries_data[country]:
                        countries_data[country][target_name] = {
                            "descriptions": [],  # use fuzzy matching to avoid adding very similar descriptions multiple times
                            "map_link": ""
                        }

                    # map the description to the existing place name, but only if it's not too similar to an existing description for that place
                    is_duplicate_desc = False
                    for existing_desc in countries_data[country][target_name]["descriptions"]:
                        # if the new description is very similar to an existing one (similarity score above 85), we will consider it a duplicate and not add it
                        if fuzz.ratio(desc.lower(), existing_desc.lower()) > 85:
                            is_duplicate_desc = True
                            break

                    if not is_duplicate_desc:
                        countries_data[country][target_name]["descriptions"].append(desc)

                    # save the map link if we don't have one for this place yet, and the current row has a valid map link
                    if not countries_data[country][target_name]["map_link"]:
                        map_url = row.get('google_maps_url', row.get('map_link', ''))
                        if pd.notna(map_url) and map_url != '':
                            countries_data[country][target_name]["map_link"] = map_url

    # Now we have a nested dictionary with countries as keys, and for each country, we have place names as keys, and for each place name, we have a list of unique descriptions and a map link. We will now create a unified CSV file for each country with this data.
    for country, places in countries_data.items():
        final_rows = []
        for name, info in places.items():
            for d in info["descriptions"]:
                final_rows.append({
                    "place": name,
                    "country": country,
                    "description": d,
                    "google_maps_url": info["map_link"]
                })

        # save the final rows for this country to a CSV file, but only if we have at least one valid row
        if final_rows:
            country_df = pd.DataFrame(final_rows)
            output_file = os.path.join(output_dir, f"{country}_processed.csv")
            country_df.to_csv(output_file, index=False, encoding='utf-8-sig')
            print(f"Saved {len(final_rows)} rows for {country}: {output_file}")

# run
aggregate_by_country_refined("../ScrapedData/Bucketlistly/Italy")

