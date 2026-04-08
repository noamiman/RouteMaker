# RouteMaker

RouteMaker is a travel planning platform that transforms unstructured travel-blog content into structured, scored destination data, then exposes it through an interactive itinerary planner.

The project combines data engineering, ML inference, and a user-facing planning UI:
- Web data ingestion from multiple travel sources
- Place cleaning and deduplication
- 10-category place scoring with a fine-tuned model
- Streamlit itinerary planning interface
- PDF and KML export for trip sharing and navigation

## Summary

RouteMaker helps travelers plan personalized routes instead of relying on generic ratings.

Instead of asking "is this place 4.5 stars?", it asks:
- Is it good for my travel style?
- Does it fit my route and pace?
- Is it a good match for what I care about (adventure, food, culture, relaxation, etc.)?

The result is a practical route-planning workflow: discover places, score by preference, build your itinerary, and export a complete PDF with your route details.

## Why This Project Exists

The idea came from real travel experience.

While traveling, I realized that a single Google Maps score (for example 4.5) often does not tell you what you actually need to plan a meaningful trip. A high rating does not explain if the place is romantic, family-friendly, relaxing, adventurous, or worth adding to your specific route.

RouteMaker was built to solve that gap: make travel planning more personal, more structured, and easier to act on. It lets users build a route tailored to their preferences and export the full plan as a PDF with route details.

## Table of Contents

1. [Summary](#summary)
2. [Why This Project Exists](#why-this-project-exists)
3. [What This Project Does](#what-this-project-does)
4. [How the System Works](#how-the-system-works)
5. [Project Layout](#project-layout)
6. [Setup](#setup)
7. [Run the App](#run-the-app)
8. [Pipeline Workflows](#pipeline-workflows)
9. [NEW_DATA Contract](#new_data-contract)
10. [Validation and Quality Gates](#validation-and-quality-gates)
11. [Common Commands](#common-commands)
12. [Troubleshooting](#troubleshooting)
13. [Author](#author)

## What This Project Does

RouteMaker is designed to answer one practical question: how can we turn noisy travel content into actionable planning data?

It supports this end-to-end flow:
1. Collect place mentions and descriptions from travel content.
2. Normalize and deduplicate place records.
3. Score each place across key traveler dimensions.
4. Let users filter, compare, and assemble day-by-day routes.
5. Export trip outputs into portable formats.

### Main User Capabilities

- Browse places by country and region
- Filter by place type and category scores
- Build multi-day routes
- Add manual place reviews through the app
- Export itineraries to PDF and KML

## How the System Works

### High-Level Architecture

1. Raw scraped data lands under `ScrapedData/`.
2. Data pipeline builds processed country files.
3. Canonical processed output is stored in `app/finalData/`.
4. Streamlit app reads only from `app/finalData/`.

Canonical processed data location:
- `app/finalData/`

### Pipeline Stages

The full rebuild pipeline runs in three steps:

1. Aggregation: `DataProcess/agg_by_country.py`
- Reads raw CSV files
- Merges near-duplicate place names
- Removes duplicate descriptions
- Filters low-information placeholder descriptions

2. Classification: `DataProcess/classify_local_tuned.py`
- Loads the fine-tuned classifier
- Produces 10 category scores per description
- Adds rating columns to processed rows

3. Final summarization: `DataProcess/final_result.py`
- Aggregates per-place descriptions
- Computes per-place score outputs
- Adds lineage fields (`description_count`, `last_updated`)

## Project Layout

```text
RouteMaker/
├── app/
│   ├── main.py                 # Streamlit app entrypoint
│   ├── pages/                  # Extra app pages (review/admin)
│   ├── output/                 # PDF/KML helpers
│   └── finalData/              # Canonical processed datasets
├── DataProcess/                # Pipeline stages
├── scrappers/                  # Extraction/scraping logic
├── NEW_DATA/                   # Incoming incremental update files
├── scripts/                    # Utility and validation scripts
├── tests/                      # Automated tests
├── run_pipeline.py             # Full rebuild runner
├── update_pipeline.py          # Incremental updater
├── Makefile                    # Common dev commands
└── readme.md
```

## Setup

### Prerequisites

- Python 3.8+
- Git
- Optional: Ollama (only needed for LLM summarization modes)

### Install

```bash
git clone <repository-url>
cd RouteMaker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional Ollama model:

```bash
ollama pull qwen2.5:0.5b
```

## Run the App

```bash
streamlit run app/main.py
```

Open:
- `http://localhost:8501`

## Pipeline Workflows

### 1) Incremental Update (recommended for regular use)

Use when you add one or more files to `NEW_DATA/`.

```bash
python update_pipeline.py --new-data NEW_DATA/
```

Behavior summary:
- Normalizes incoming file schema
- Accepts legacy `text` by mapping it to `description`
- Filters empty or placeholder descriptions
- Reuses provided category ratings when present
- Runs ML scoring only for rows that still need it
- Merges into `app/finalData/` with lineage updates

### 2) Full Rebuild (maintenance / major refresh)

Use when you want to rebuild all countries from raw sources.

```bash
python run_pipeline.py --force
```

This runs aggregation -> classification -> final summarization, then rewrites country files in `app/finalData/`.

## NEW_DATA Contract

### Required Columns

- `country`
- `place`
- `description`

### Recommended Columns

- `region`
- `place_type`
- `google_maps_url`

### Optional Metadata

- `source`
- `blog_source`
- `review_date`
- `is_manual_entry`
- Category columns: `romance`, `family`, `cost`, `nature`, `adventure`, `culture`, `food`, `relaxation`, `service`, `accessibility`

Template:
- `NEW_DATA/TEMPLATE.csv`

## Validation and Quality Gates

Before pushing changes, run:

```bash
make test && make validate-data
```

What these checks cover:
- Unit tests for normalization, merge behavior, and quality filters
- Processed file schema validation
- Blank description detection
- Placeholder-description detection

## Common Commands

All from project root:

```bash
# Run automated tests
make test

# Validate processed files
make validate-data

# Incremental update from NEW_DATA/
make update

# Full rebuild pipeline
make rebuild

# Streamlit startup smoke run
make smoke-app
```

## Troubleshooting

### A country file has no score columns

Cause:
- File likely came from pre-classified/raw format.

Fix:

```bash
python run_pipeline.py --force
```

### validate-data fails

Run:

```bash
make validate-data
```

Then fix reported issues in the listed file(s), especially required columns and empty descriptions.

### App starts but shows old or unexpected data

Check that current files exist under:
- `app/finalData/`

Then run either:

```bash
make update
```

or

```bash
make rebuild
```

### Full rebuild prints a CSV read warning from one raw scraped file

Cause:
- A malformed or empty raw CSV in `ScrapedData/`.

Fix:
- Remove or repair that specific raw file, then rerun the rebuild.

## Author

Noamiman

LinkedIn:
- https://www.linkedin.com/in/noamiman/

If you work on travel, data, or ML products, I would be glad to connect.
