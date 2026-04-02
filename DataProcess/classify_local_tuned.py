import pandas as pd
import torch
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from tqdm import tqdm
import argparse


class TravelClassifier:
    def __init__(self, model_path, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.label_keys = [
            "romance", "family", "cost", "nature", "adventure",
            "culture", "food", "relaxation", "service", "accessibility"
        ]
        self.min_description_length = 200  # Minimum chars for ML classification
        self.category_means = {}  # Will be calculated per CSV

        print(f"Loading model to {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small", use_fast=False)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path).to(self.device)
        self.model.eval()

    def predict(self, text):
        """predicts the labels for a single text input."""
        inputs = self.tokenizer(text, return_tensors="pt", padding=True,
                                truncation=True, max_length=128).to(self.device)

        with torch.no_grad():
            outputs = self.model(**inputs)
            predictions = torch.clamp(outputs.logits * 10.0, 0, 10).round().int()

        results = dict(zip(self.label_keys, predictions[0].tolist()))
        return results

    def _enrich_row(self, row):
        """processes a single row of the DataFrame and returns the predictions as a Series."""
        try:
            description = str(row['description']).strip()
            
            # Check description length
            if len(description) < self.min_description_length:
                # Use mean ratings for short descriptions
                mean_results = {k: self.category_means.get(k, 5.0) for k in self.label_keys}
                return pd.Series(mean_results)
            
            # Use ML model for sufficient descriptions
            prediction = self.predict(description)
            return pd.Series(prediction)
        except Exception as e:
            print(f"  Error on {row.get('place', 'unknown')}: {e}")
            return pd.Series({k: None for k in self.label_keys + ["short_summary"]})

    def process_csv(self, file_path, force_update=False):
        """processes a single CSV file, enriches it with predictions, and overwrites the file."""
        if not file_path or not os.path.isfile(file_path):
            print(f"File not found: {file_path}")
            return

        df = pd.read_csv(file_path)

        has_labels = all(col in df.columns for col in self.label_keys)

        if has_labels and not force_update:
            print(f"Skipping {os.path.basename(file_path)} - already enriched.")
            return

        print(f"Processing {os.path.basename(file_path)}...")
        
        # Calculate mean ratings from existing data for short descriptions
        for key in self.label_keys:
            if key in df.columns:
                self.category_means[key] = df[key].astype(float).mean()
            else:
                self.category_means[key] = 5.0  # Default fallback
        
        print(f"  Category means: {self.category_means}")

        if has_labels:
            cols_to_drop = [c for c in self.label_keys if c in df.columns]
            df = df.drop(columns=cols_to_drop)

        tqdm.pandas(desc=f"Enriching {os.path.basename(file_path)}")
        enrichment_df = df.progress_apply(self._enrich_row, axis=1)

        final_df = pd.concat([df, enrichment_df], axis=1)
        final_df = final_df.loc[:, ~final_df.columns.duplicated()]
        final_df.to_csv(file_path, index=False, encoding='utf-8-sig')

        print(f"Successfully updated: {file_path} (Columns: {list(final_df.columns)})")

    def process_all_csvs(self, root_dir, force_update=False):
        """processes all CSV files in the specified directory and its subdirectories."""
        print(f"Starting batch processing in: {root_dir}")

        for root, _, files in os.walk(root_dir):
            for file in files:
                if file.endswith(".csv") and not file.endswith("_enriched.csv"):
                    file_path = os.path.join(root, file)
                    self.process_csv(file_path, force_update=force_update)

        print("Batch processing complete.")


# --- using the classifier ---
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Classify travel places using ML model")
    parser.add_argument("--model", "-m", default="../model/checkpoints/tourism_model_checkpoint_2240",
                       help="Path to the trained model directory")
    parser.add_argument("--data", "-d", default="../finalData",
                       help="Directory containing CSV files to classify")
    parser.add_argument("--force", action="store_true",
                       help="Force re-processing even if files already have classifications")

    args = parser.parse_args()

    classifier = TravelClassifier(args.model)
    classifier.process_all_csvs(args.data, force_update=args.force)