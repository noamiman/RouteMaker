import pandas as pd
import ollama
import os
from tqdm import tqdm
import argparse
from datetime import datetime


class TravelSummarizer:
    def __init__(self, model_name='qwen2.5:0.5b', num_descriptions=3):
        self.model_name = model_name
        self.num_descriptions = num_descriptions
        tqdm.pandas()

    def _summarize_text(self, descriptions):
        """gets a list of descriptions and uses the specified model to combine them into a single professional summary of about 50 words."""
        valid_descriptions = [str(d) for d in descriptions if pd.notna(d) and str(d).strip() != ""]
        if not valid_descriptions:
            return "No description available."

        if len(valid_descriptions) == 1 and len(valid_descriptions[0].split()) < 15:
            return valid_descriptions[0]

        combined_text = "\n".join([f"- {desc}" for desc in valid_descriptions])

        prompt = f""""You are a strict data extractor. Summarize the text in 2-3 concise sentences "
                f"focusing ONLY on: {combined_text}. "
                "CRITICAL: Output ONLY the summary text. Do not list the topics. Do not include headers. "
                "Do not say 'Summary:' or 'Here is the text'. Just the raw summary."""

        try:
            response = ollama.chat(
                model=self.model_name,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.1, 'num_predict': 300}
            )
            return response['message']['content'].strip()
        except Exception as e:
            return f"Error: {e}"

    def process_file(self, input_path, output_path=None, overwrite=False):
        """processes a single CSV file, aggregates descriptions by place,
         summarizes them using the specified model,
          and saves the results (overwrites if specified)."""
        print(f"\n--- Processing: {input_path} ---")
        df = pd.read_csv(input_path)

        # define columns to check and aggregate
        cols_to_avg = ['romance', 'family', 'cost', 'nature', 'adventure',
                       'culture', 'food', 'relaxation', 'service', 'accessibility']

        agg_rules = {
            'country': 'first',
            'google_maps_url': 'first',
            'description': lambda x: "\n\n".join(list(dict.fromkeys([str(d).strip() for d in x if pd.notna(d) and str(d).strip() != ""]))[:3])  # you can change to lambda if LLM is enabled
        }

        extra_cols = ['region', 'place_type', 'blog_source']
        for col in extra_cols:
            if col in df.columns:
                agg_rules[col] = 'first'

        # only add numeric columns that actually exist in the file
        for col in cols_to_avg:
            if col in df.columns:
                agg_rules[col] = 'mean'

        # aggregate by place
        df_grouped = df.groupby('place', as_index=False).agg(agg_rules)
        
        # Add description_count (number of descriptions per place)
        df_grouped['description_count'] = df.groupby('place').size().reset_index(name='description_count')['description_count'].values
        
        # Add last_updated timestamp
        df_grouped['last_updated'] = datetime.now().strftime('%Y-%m-%d')

        actual_numeric_cols = [col for col in cols_to_avg if col in df_grouped.columns]
        df_grouped[actual_numeric_cols] = df_grouped[actual_numeric_cols].fillna(0)
        # heuristic cost adjustment
        if 'cost' in df_grouped.columns:
            df_grouped['cost'] = df_grouped['cost'] * 2

        df_grouped[actual_numeric_cols] = df_grouped[actual_numeric_cols].round(0).astype(int)
        all_text_cols = ['description', 'country', 'google_maps_url'] + extra_cols
        for col in all_text_cols:
            if col in df_grouped.columns:
                # הופך NaN למחרוזת ריקה באמת
                df_grouped[col] = df_grouped[col].fillna("")

        print("Using the first 3 available descriptions (skipping LLM)...")

        # logic for output path or overwrite
        if overwrite:
            final_path = input_path
        elif output_path:
            final_path = output_path
        else:
            final_path = input_path.replace(".csv", "_summarized.csv")

        df_grouped.to_csv(final_path, index=False, encoding='utf-8-sig')
        print(f"Saved to: {final_path}")

    def process_folder(self, folder_path, output_folder, overwrite=False):
        """processes all CSV files in a folder. If overwrite is True, ignores output_folder."""
        if not overwrite and not os.path.exists(output_folder):
            os.makedirs(output_folder)

        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        print(f"Found {len(files)} files in {folder_path}")

        for file in files:
            input_path = os.path.join(folder_path, file)

            if overwrite:
                self.process_file(input_path, overwrite=True)
            else:
                output_path = os.path.join(output_folder, f"summarized_{file}")
                self.process_file(input_path, output_path)


# --- using ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create final summarized travel data")
    parser.add_argument("--input", "-i", default="../finalData",
                       help="Input directory containing processed CSV files")
    parser.add_argument("--output", "-o", default="../finalData",
                       help="Output directory for summarized files")
    parser.add_argument("--overwrite", action="store_true",
                       help="Overwrite existing files instead of creating new ones")
    parser.add_argument("--model", "-m", default="qwen2.5:0.5b",
                       help="Ollama model name for summarization")

    args = parser.parse_args()

    summarizer = TravelSummarizer(model_name=args.model)
    summarizer.process_folder(args.input, args.output, overwrite=args.overwrite)