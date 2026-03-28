import pandas as pd
import torch
import os
from transformers import AutoTokenizer, AutoModelForSequenceClassification

class TravelClassifier:
    def __init__(self, model_path, device=None):
        self.device = device or ("cuda" if torch.cuda.is_available() else "cpu")
        self.label_keys = [
            "romance", "family", "cost", "nature", "adventure",
            "culture", "food", "relaxation", "service", "accessibility"
        ]

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
            prediction = self.predict(str(row['description']))
            return pd.Series(prediction)
        except Exception as e:
            print(f"  Error on {row.get('place', 'unknown')}: {e}")
            return pd.Series({k: None for k in self.label_keys + ["short_summary"]})

    def process_csv(self, file_path, force_update=False):
        """peocesses a single CSV file, enriches it with predictions, and saves the updated file."""
        if not file_path.endswith(".csv"):
            return

        df = pd.read_csv(file_path)

        # check if the file already has the label columns and skip processing if they exist (unless force_update is True)
        if not force_update and all(col in df.columns for col in self.label_keys):
            print(f"Skipping {os.path.basename(file_path)} - already enriched.")
            return

        print(f"Processing {os.path.basename(file_path)}...")
        enrichment_df = df.apply(self._enrich_row, axis=1)

        df = pd.concat([df, enrichment_df], axis=1)
        df.to_csv(file_path, index=False)
        print(f"Successfully updated {file_path}")

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
    MODEL_DIR = "../model/tourism_model_checkpoint_2240"
    DATA_DIR = "../finalData/Unified_Countries/travel_data_Italy.csv"

    classifier = TravelClassifier(MODEL_DIR)

    # process a single file
    classifier.process_csv(DATA_DIR)