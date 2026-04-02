# 🌍 Travel Route Maker

An intelligent travel planning application that combines web scraping, machine learning classification, and interactive itinerary building to create personalized travel experiences.

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Data Pipeline](#data-pipeline)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Data Sources](#data-sources)
- [ML Model](#ml-model)
- [Contributing](#contributing)

## 🎯 Overview

Travel Route Maker is a comprehensive travel planning platform that:

1. **Scrapes** travel blog data from multiple sources
2. **Processes** and cleans the data using fuzzy matching
3. **Classifies** destinations using a fine-tuned ML model
4. **Provides** an interactive web interface for itinerary planning
5. **Generates** PDF guides and KML maps for trips

The system transforms raw travel blog content into structured, classified data that travelers can use to build custom itineraries with ratings for romance, adventure, family-friendliness, cost, and more.

## ✨ Features

### 🕷️ Data Collection
- Multi-source web scraping from travel blogs
- Automated data extraction and cleaning
- Fuzzy matching for duplicate removal
- Country-wise data aggregation

### 🤖 Machine Learning
- Fine-tuned DeBERTa model for place classification
- 10-dimensional rating system (romance, family, cost, nature, adventure, culture, food, relaxation, service, accessibility)
- Automated content analysis and scoring

### 🌐 Web Application
- Interactive Streamlit-based interface
- Multi-route itinerary management
- Advanced filtering and search capabilities
- Real-time map integration
- PDF and KML export functionality

### 📊 Data Processing Pipeline
- Automated end-to-end data processing
- Configurable pipeline steps
- Progress tracking and error handling
- Batch processing capabilities

## 🏗️ Architecture

```
Travel Route Maker
├── 📁 ScrapedData/          # Raw scraped travel data
├── 📁 DataProcess/          # Data processing scripts
│   ├── agg_by_country.py    # Data aggregation & deduplication
│   ├── classify_local_tuned.py # ML classification
│   └── final_result.py      # Final summarization
├── 📁 finalData/            # Processed, classified data
├── 📁 model/                # ML model checkpoints
├── 📁 app/                  # Streamlit web application
│   ├── main.py             # Main application
│   ├── pages/              # Additional pages
│   └── output/             # Generated PDFs and KMLs
└── 📁 saved_itineraries/    # User-created itineraries
```

## 🔄 Data Pipeline

The system provides two pipeline modes for different use cases:

### Pipeline Modes

#### 1. **Update Pipeline** (Daily Use) 🔄
Fast, incremental updates using weighted averaging to merge new data with existing processed data.

```bash
python update_pipeline.py --new-data NEW_DATA/
```

**When to use:**
- Adding new agent-scraped reviews
- Incorporating user submissions
- Regular incremental updates
- Preserves all existing data with intelligent merging

**Features:**
- Only classifies new descriptions (fast!)
- Weighted averaging maintains statistical accuracy
- Tracks `description_count` for data quality metrics
- Metadata tracking (`last_updated` timestamp)

#### 2. **Full Rebuild Pipeline** (Maintenance) 🔧
Complete rebuild from raw scraped data, processing all files from scratch.

```bash
python run_pipeline.py
```

**When to use:**
- After bulk agent scraping completes
- Database reset/optimization needed
- Schema or processing logic changes
- Admin maintenance tasks

**Note:** Overwrites `finalData/` completely. Use carefully.

### Pipeline Architecture

The data processing pipeline consists of three main stages:

### 1. Data Aggregation (`agg_by_country.py`)
**Input:** Raw CSV files from `ScrapedData/`  
**Process:**
- Reads all CSV files from subdirectories
- Groups data by country using fuzzy string matching
- Removes duplicate descriptions (85% similarity threshold)
- Consolidates place information (URLs, types, regions)

**Output:** Country-specific processed CSV files in `finalData/`

### 2. ML Classification (`classify_local_tuned.py`)
**Input:** Processed CSV files from `finalData/`  
**Process:**
- Uses fine-tuned DeBERTa model for text classification
- Analyzes place descriptions for 10 categories:
  - Romance (0-10)
  - Family-friendly (0-10)
  - Cost (0-10)
  - Nature (0-10)
  - Adventure (0-10)
  - Culture (0-10)
  - Food (0-10)
  - Relaxation (0-10)
  - Service quality (0-10)
  - Accessibility (0-10)

**Output:** CSV files with added classification columns

### 3. Final Summarization (`final_result.py`)
**Input:** Classified CSV files
**Process:**
- Aggregates multiple descriptions per place
- Averages classification scores
- Generates summarized descriptions (optional LLM)
- Applies cost adjustment heuristics

**Output:** **Overwrites** the processed files with final summarized datasets

## 🚀 Installation

### Prerequisites
- Python 3.8+
- Git
- Ollama (for text summarization)

### Setup Steps

1. **Clone the repository:**
```bash
git clone <repository-url>
cd RouteMaker
```

2. **Create virtual environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Install Ollama (optional, for summarization):**
```bash
# Install from https://ollama.ai/
ollama pull qwen2.5:0.5b
```

5. **Verify model checkpoint exists:**
```bash
ls model/checkpoints/tourism_model_checkpoint_2240/
```

## 📖 Usage

### Quick Start

1. **Start the web application:**
```bash
streamlit run app/main.py
```

2. **Open your browser** to `http://localhost:8501`

### Data Management

Both pipeline modes are accessible in the Streamlit app under **⚙️ Admin Panel** in the sidebar for easy management.

#### Using Update Pipeline (Recommended for Regular Updates)

1. **Place new data in NEW_DATA folder:**
```bash
# NEW_DATA/
# ├── new_reviews.csv
# ├── agent_scraped_2024.csv
# └── TEMPLATE.csv (format example)
```

2. **Run the update pipeline:**
```bash
python update_pipeline.py --new-data NEW_DATA/
```

3. **Results:**
   - New descriptions automatically classified
   - Existing places merged with weighted averaging
   - Statistics displayed (unchanged/merged/new counts)
   - `finalData/` updated with new data

#### Using Full Rebuild (Maintenance Only)

1. **Rebuild from raw scraped data:**
```bash
python run_pipeline.py
```

2. **Options:**
```bash
# Force re-processing of all files
python run_pipeline.py --force

# Skip ML classification (if model unavailable)
python run_pipeline.py --skip-classification
```

### Individual Pipeline Steps

```bash
# Step 1: Aggregate data
python DataProcess/agg_by_country.py --input ScrapedData --output finalData

# Step 2: Classify places
python DataProcess/classify_local_tuned.py --model model/checkpoints/tourism_model_checkpoint_2240 --data finalData

# Step 3: Final processing
python DataProcess/final_result.py --input finalData --output finalData --overwrite
```

### Web Application Features

- **Multi-route management:** Create and manage multiple trip itineraries
- **Advanced filtering:** Filter by country, region, place type, and ratings
- **Interactive editing:** Drag-and-drop day assignment, inline editing
- **Export options:** Generate PDF guides and KML maps
- **Emergency stations:** Built-in emergency contact database

## 📁 Project Structure

```
RouteMaker/
├── 📄 readme.md                    # This file
├── 📄 requirements.txt             # Python dependencies
├── 📄 run_pipeline.py              # Full rebuild pipeline
├── 📄 update_pipeline.py           # Incremental update pipeline
│
├── 📁 ScrapedData/                 # Raw scraped data
│   ├── Bucketlistly/
│   ├── The_Blonde_Abroad/
│   └── The_World_Travel_Guy/
│
├── 📁 NEW_DATA/                    # New reviews/scraped data for updates
│   ├── TEMPLATE.csv               # Format example
│   └── README.md                  # Update workflow documentation
│
├── 📁 DataProcess/                 # Data processing scripts
│   ├── agg_by_country.py          # Data aggregation
│   ├── classify_local_tuned.py    # ML classification
│   └── final_result.py            # Final summarization
│
├── 📁 finalData/                   # Processed datasets
│   ├── Albania_processed.csv
│   ├── Vietnam_processed.csv
│   └── ...
│
├── 📁 model/                       # ML models and checkpoints
│   ├── checkpoints/
│   │   └── tourism_model_checkpoint_2240/
│   └── demonstrationModel.py
│
├── 📁 app/                         # Streamlit web application
│   ├── main.py                    # Main application
│   ├── pages/                     # Additional pages
│   │   ├── add_review.py
│   │   ├── agent_management.py
│   │   └── ...
│   ├── output/                    # Generated files
│   └── pdf_maker.py               # PDF generation
│
├── 📁 saved_itineraries/           # User itineraries
├── 📁 scrappers/                   # Scraping scripts
└── 📁 blogs.json                   # Blog configuration
```

## 📊 Data Sources

The system currently processes data from:

- **Bucketlistly** - Comprehensive travel guides
- **The Blonde Abroad** - Southeast Asia focus
- **The World Travel Guy** - Global travel insights

Each source provides:
- Place names and descriptions
- Location data (country, region)
- Google Maps links
- Place categories and types

## 🧠 ML Model

### Model Architecture
- **Base Model:** Microsoft DeBERTa v3 Small
- **Task:** Multi-label classification (10 categories)
- **Input:** Place descriptions (max 128 tokens)
- **Output:** Ratings 0-10 for each category

### Training Data
- Curated travel blog content
- Human-annotated ratings
- Multi-label classification approach
- Fine-tuned on travel-specific language

### Performance
- High accuracy on travel content classification
- Robust handling of diverse writing styles
- Efficient inference for batch processing

## 🤝 Contributing

### Development Setup
1. Fork the repository
2. Create a feature branch: `git checkout -b feature/new-feature`
3. Make your changes
4. Run tests: `python run_pipeline.py --force`
5. Commit changes: `git commit -am 'Add new feature'`
6. Push to branch: `git push origin feature/new-feature`
7. Submit a pull request

### Code Style
- Follow PEP 8 Python style guidelines
- Add docstrings to functions and classes
- Include type hints where possible
- Write descriptive commit messages

### Adding New Data Sources
1. Create scraper in `scrappers/` directory
2. Update `blogs.json` configuration
3. Test data extraction
4. Run full pipeline to verify integration

### Improving ML Model
1. Prepare additional training data
2. Update `model/finetune_tourism.py`
3. Train and validate new checkpoints
4. Update pipeline to use new model version

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Travel bloggers for providing rich content
- Hugging Face for transformer models
- Streamlit for the web framework
- Open source community for data processing tools

---

**Happy travels! 🌍✈️**