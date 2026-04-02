# NEW_DATA Directory

This folder stores new travel data to be merged with existing processed data using weighted averaging.

## Purpose

When agents scrape new travel data or users submit reviews, place them in this directory. The `update_pipeline.py` script will:

1. **Classify** new descriptions using the fine-tuned ML model
2. **Merge** with existing data using weighted averages (preserving statistical accuracy)
3. **Update** the finalData/ files with merged results

## File Format

CSV files with the following required columns:

| Column | Type | Description |
|--------|------|-------------|
| `country` | string | Country name (must match finalData filenames without "_processed.csv") |
| `place` | string | Place/location name |
| `description` | string | Detailed description of the place and experience |
| `place_type` | string | Category: landmark, city, nature, museum, restaurant, hotel, etc. |

### Optional Columns
- `rating`: Pre-existing rating (0-10) if available
- `source`: Where the data came from (agent_scraper, user_review, etc.)
- `date`: ISO date (YYYY-MM-DD) when data was collected

## Example

See `TEMPLATE.csv` for a template with proper formatting.

## Workflow

1. **Place new CSV files here**
   ```
   NEW_DATA/
   ├── agent_scraped_2024-01-15.csv
   └── user_reviews_batch_3.csv
   ```

2. **Run the update pipeline**
   ```bash
   python update_pipeline.py --new-data NEW_DATA/
   ```

3. **Results**
   - New data is classified automatically
   - Merged with existing finalData/ using weighted averaging
   - Old ratings preserved but intelligently updated
   - `description_count` tracks statistical weight
   - `last_updated` shows when merge occurred

## Key Features

### Weighted Averaging
When a place exists in both old and new data:
```
new_rating = (old_rating × old_count + new_rating × new_count) / (old_count + new_count)
description_count = old_count + new_count
```

Example:
- Old: 3 descriptions averaged to `romance=6.0`
- New: 1 description with `romance=8.0`
- Merged: `(6.0×3 + 8.0×1) / 4 = 6.5` → Accurate!

### Smart Processing
- **Fast**: Only NEW descriptions get classified (old ratings reused)
- **Accurate**: Weighted averages account for sample size differences
- **Complete**: All descriptions preserved (up to 5 per place in output)
- **Tracked**: `description_count` and `last_updated` for lineage

## Notes

- Place names are matched using fuzzy matching (90% threshold - same as aggregation pipeline)
- Completely new places are added directly without merging
- Classification uses the fine-tuned DeBERTa model from `model/checkpoints/`
- After update, verify results and commit merged data to version control

## Cleanup

After successful merging, you can archive or delete the CSV files from this directory:
```bash
rm NEW_DATA/*.csv
```
(Keep this README for documentation)
