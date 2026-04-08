import tempfile
import unittest
from pathlib import Path

import pandas as pd

from update_pipeline import IncrementalUpdater


CATEGORIES = [
    "romance",
    "family",
    "cost",
    "nature",
    "adventure",
    "culture",
    "food",
    "relaxation",
    "service",
    "accessibility",
]


class UpdatePipelineTests(unittest.TestCase):
    def test_normalize_legacy_text_and_drop_placeholder(self):
        updater = IncrementalUpdater(base_data_dir=".", model_path="unused")
        df = pd.DataFrame(
            [
                {"country": "Thailand", "place": "Valid", "text": "Great temple by the river."},
                {"country": "Thailand", "place": "Noise", "text": "Not mentioned in this text."},
            ]
        )

        normalized = updater.normalize_new_data(df)

        self.assertEqual(len(normalized), 1)
        self.assertIn("description", normalized.columns)
        self.assertEqual(normalized.iloc[0]["place"], "Valid")

    def test_classify_skips_when_all_rows_have_ratings(self):
        updater = IncrementalUpdater(base_data_dir=".", model_path="unused")
        row = {"country": "Thailand", "place": "Wat Arun", "description": "Good description"}
        row.update({cat: 6 for cat in CATEGORIES})
        df = pd.DataFrame([row])

        out = updater.classify_new_data(df.copy())

        self.assertEqual(int(out.iloc[0]["romance"]), 6)
        self.assertEqual(int(out.iloc[0]["food"]), 6)

    def test_merge_country_data_sets_metadata_for_new_places(self):
        with tempfile.TemporaryDirectory() as tmp:
            base_dir = Path(tmp) / "base"
            base_dir.mkdir(parents=True, exist_ok=True)

            base_df = pd.DataFrame(
                [
                    {
                        "place": "Old Place",
                        "country": "Thailand",
                        "description": "Existing description",
                        "description_count": 2,
                        "last_updated": "2026-04-07",
                        **{cat: 5 for cat in CATEGORIES},
                    }
                ]
            )
            base_df.to_csv(base_dir / "Thailand_processed.csv", index=False)

            updater = IncrementalUpdater(base_data_dir=str(base_dir), model_path="unused")
            new_df = pd.DataFrame(
                [
                    {
                        "place": "Brand New",
                        "country": "Thailand",
                        "description": "New place description",
                        **{cat: 7 for cat in CATEGORIES},
                    }
                ]
            )

            merged = updater.merge_country_data("Thailand", new_df)
            created = merged[merged["place"] == "Brand New"].iloc[0]

            self.assertEqual(int(created["description_count"]), 1)
            self.assertTrue(str(created["last_updated"]).strip())


if __name__ == "__main__":
    unittest.main()
