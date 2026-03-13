import pandas as pd
import ollama
import json
import os
from tqdm import tqdm

# --- config ---
INPUT_CSV = "../DataProcess/Unified_Countries/Italy_processed.csv"
OUTPUT_JSON = "../DataProcess/Unified_Countries/Italy_Labeled.json"
MODEL_NAME = "llama3.2:3b"

CATEGORIES = [
    "Romance", "Family", "Cost", "Nature", "Adventure",
    "Culture", "Food", "Relaxation", "Service", "Accessibility"
]

# --- prompt ---
SYSTEM_PROMPT = f"""
You are a travel data analyst. Your task is to rate a travel review across 10 categories.
For each category, provide a score from 0 to 10, where 0 is 'not relevant/very poor' and 10 is 'highly relevant/excellent'.

CRITICAL INSTRUCTIONS:
1. Be decisive. Use the full scale (0-10). If a review is very negative about cost, give it 1 or 2.
2. If a category is not mentioned at all, give it 0.
3. You MUST respond ONLY with a valid JSON object. No prose, no headers.

The JSON format must be:
{{
  "Romance": int, "Family": int, "Cost": int, "Nature": int, "Adventure": int,
  "Culture": int, "Food": int, "Relaxation": int, "Service": int, "Accessibility": int
}}
"""


def get_llm_rating(review_text):
    """use ollama 3.2b to get the rating for a single review. Returns a dict with category scores."""
    try:
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[
                {'role': 'system', 'content': SYSTEM_PROMPT},
                {'role': 'user', 'content': f"Review to rate: {review_text}"}
            ],
            format='json', # for validation and to ensure we get a JSON response
            options={"temperature": 0.1}  # low temperature for more deterministic output
        )
        return json.loads(response['message']['content'])
    except Exception as e:
        print(f"\nError processing review: {e}")
        return {cat: 0 for cat in CATEGORIES}


def main():
    # load the CSV data
    if not os.path.exists(INPUT_CSV):
        print(f"Error: {INPUT_CSV} not found.")
        return

    df = pd.read_csv(INPUT_CSV)

    # load existing processed data if available (for resuming)
    processed_data = []
    if os.path.exists(OUTPUT_JSON):
        with open(OUTPUT_JSON, "r", encoding="utf-8") as f:
            processed_data = json.load(f)

    start_index = len(processed_data)
    print(f"Starting from index {start_index} out of {len(df)}")

    # process each review and get ratings
    for i in tqdm(range(start_index, len(df)), desc="Labeling Reviews"):
        row = df.iloc[i]
        review_text = str(row['description']).strip()

        # call the LLM to get ratings for this review
        ratings = get_llm_rating(review_text)

        # build the entry for this review
        entry = {
            "review_id": f"th-r-{i:05d}",
            "review": review_text,
            "distribution": ratings
        }

        processed_data.append(entry)

        # save progress every 10 reviews to avoid losing data in case of interruption
        if i % 10 == 0:
            with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(processed_data, f, indent=2, ensure_ascii=False)

    # final save after processing all reviews
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(processed_data, f, indent=2, ensure_ascii=False)

    print(f"\nProcessing complete! Saved to {OUTPUT_JSON}")


if __name__ == "__main__":
    main()