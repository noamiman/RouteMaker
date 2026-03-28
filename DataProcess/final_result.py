import pandas as pd
import ollama
import os
from tqdm import tqdm

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

        # todo: fix the prompt to be more clear and concise, and to instruct the model to write in a first-person tone without any intro text, and to limit the summary to 3 sentences.
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

    def process_file(self, input_path, output_path=None):
        """processes a single CSV file, aggregates descriptions by place,
         summarizes them using the specified model,
          and saves the results to a new CSV file."""
        print(f"\n--- Processing: {input_path} ---")
        df = pd.read_csv(input_path)

        # configure the aggregation rules for each column: take the first value for country and google_maps_url, combine descriptions into a list of unique values (up to num_descriptions), and average the numeric scores
        agg_rules = {
            'country': 'first',
            'google_maps_url': 'first',
            # 'description': lambda x: list(set(x))[:self.num_descriptions],
            'description': 'first',
            'romance': 'mean', 'family': 'mean', 'cost': 'mean',
            'nature': 'mean', 'adventure': 'mean', 'culture': 'mean',
            'food': 'mean', 'relaxation': 'mean', 'service': 'mean',
            'accessibility': 'mean'
        }

        # aggregate by place and apply the defined rules to combine descriptions and average the scores
        df_grouped = df.groupby('place', as_index=False).agg(agg_rules)

        # the cost in the majority of the cases is underestimated, so we will multiply it by 2 to make it more realistic (this is just a heuristic and can be adjusted based on the actual data distribution)
        df_grouped['cost'] = df_grouped['cost'] * 2

        # summarize the combined descriptions for each place using the specified model
        # print(f"Summarizing using {self.model_name}...")
        # df_grouped['description'] = df_grouped['description'].progress_apply(self._summarize_text)

        print("Using the first available description (skipping LLM)...")

        # clean up the numeric columns by rounding to the nearest integer for better presentation
        numeric_cols = df_grouped.select_dtypes(include=['number']).columns
        df_grouped[numeric_cols] = df_grouped[numeric_cols].round(0).astype(int)

        # save the final summarized and aggregated results to a new CSV file
        if not output_path:
            output_path = input_path.replace(".csv", "_summarized.csv")

        df_grouped.to_csv(output_path, index=False)
        print(f"Saved to: {output_path}")

    def process_folder(self, folder_path, output_folder):
        """processes all CSV files in a folder and saves the summarized results to another folder"""
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        files = [f for f in os.listdir(folder_path) if f.endswith('.csv')]
        print(f"Found {len(files)} files in {folder_path}")

        for file in files:
            input_path = os.path.join(folder_path, file)
            output_path = os.path.join(output_folder, f"summarized_{file}")
            self.process_file(input_path, output_path)


# --- using ---
if __name__ == "__main__":
    # create an instance of the summarizer with the desired model
     summarizer = TravelSummarizer(model_name='qwen2.5:0.5b')
     summarizer.process_file('../finalData/Unified_Countries/Albania_processed.csv', '../finalData/Unified_Countries/Albania_processed_sum.csv')
    # option A: process a single file
    # summarizer.process_file("../scrappers/travel_data_Taiwan.csv", "Taiwan_final.csv")

    # option B: process all CSV files in a folder and save the summarized results to another folder
    # summarizer.process_folder("Unified_Countries", "Summarized_Results")

    # print("summarize: ", summarizer._summarize_text("This traditional teahouse with its rows of windows and paper lanterns is the most famous view in Jiufen. If you plan to have tea there, you’ll want to book ahead online."))