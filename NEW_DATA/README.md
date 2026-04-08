# NEW_DATA Directory

This folder stores new travel data to be merged with existing processed data using weighted averaging.

## Purpose

When agents scrape new travel data or users submit reviews, place them in this directory. The `update_pipeline.py` script will:

1. **Classify** new descriptions using the fine-tuned ML model
2. **Merge** with existing data using weighted averages (preserving statistical accuracy)
3. **Update** the canonical `app/finalData/` files with merged results

## File Format

CSV files with the following required columns:

| Column | Type | Description |
|--------|------|-------------|
| `country` | string | Country name (must match processed filenames without "_processed.csv") |
| `place` | string | Place/location name |
| `description` | string | Detailed description of the place and experience |

### Recommended Core Columns
- `region`: Region, city, or district name
- `place_type`: Category such as landmark, city, nature, museum, restaurant, hotel
- `google_maps_url`: Direct Google Maps link

### Optional Columns
- `source`: Source label; copied into `blog_source` when present
- `blog_source`: Existing source label used by processed country files
- `review_date`: ISO or display timestamp for manual reviews
- `is_manual_entry`: Boolean flag for manually submitted rows
- Category scores: `romance`, `family`, `cost`, `nature`, `adventure`, `culture`, `food`, `relaxation`, `service`, `accessibility`

If a file still uses a legacy `text` column instead of `description`, the update pipeline now normalizes it automatically. Rows with empty descriptions are dropped during validation.
Rows with low-information placeholder descriptions (for example "Not mentioned in this text") are also dropped during validation.

## Example

`TEMPLATE.csv` is intentionally minimal and includes the most common fields:
- `country`, `place`, `description`
- `region`, `place_type`, `google_maps_url`

Add optional metadata columns (like `source`, `blog_source`, `review_date`, ratings, etc.) only when needed.

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
   - Merged with existing `app/finalData/` files using weighted averaging
   - Old ratings preserved but intelligently updated
   - Manually supplied category scores are reused instead of being reclassified
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
- The supported processed-data directory is `app/finalData/`
- After update, verify results and commit merged data to version control

## Cleanup

After successful merging, you can archive or delete the CSV files from this directory:
```bash
rm NEW_DATA/*.csv
```
(Keep this README for documentation)
