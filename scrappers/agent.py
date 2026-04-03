import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import json
from urllib.parse import urlparse
from langchain_ollama import ChatOllama
import sys

# --- 1. Path and Environment Management ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, ".."))

if project_root not in sys.path:
    sys.path.append(project_root)

load_dotenv(os.path.join(project_root, ".env"))

# --- 2. Data Models (Pydantic) ---
class TravelPlace(BaseModel):
    place: str = Field(description="Name of the specific attraction or spot")
    country: str = Field(description="Name of the country")
    region: str = Field(description="The specific area or city within the country")
    place_type: str = Field(description="the type of the point of interest")
    google_maps_url: str = Field(description="URL to Google Maps if mentioned, else 'N/A'")
    description: str = Field(description="A concise summary of the review or tips for this place")

class TravelDataList(BaseModel):
    places: List[TravelPlace]

# --- 3. LLM Management (Required for Streamlit) ---
class LLMManager:
    def __init__(self, use_local: bool = False):
        self.use_local = use_local
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.current_model = "llama-3.3-70b-versatile"
        self.local_model_name = "llama3.2:3b"

    def get_llm(self):
        if self.use_local:
            print(f"🤖 Using Local Model (Ollama): {self.local_model_name}")
            return ChatOllama(
                model=self.local_model_name,
                temperature=0,
                format="json"
            )
        else:
            print(f"🤖 Using Groq Model: {self.current_model}")
            return ChatGroq(
                temperature=0,
                model_name=self.current_model,
                groq_api_key=self.groq_api_key
            ).bind(response_format={"type": "json_object"})

    def invoke_with_retry(self, input_data, max_retries=3):
        for i in range(max_retries):
            try:
                llm = self.get_llm()
                return llm.invoke(input_data)
            except Exception as e:
                if "429" in str(e) or "rate_limit" in str(e).lower():
                    if i < max_retries - 1:
                        time.sleep((i + 1) * 10)
                    else:
                        print("\n🛑 Groq Rate Limit Reached.")
                        choice = input("Switch to Local Ollama? (y/n): ").strip().lower()
                        if choice == 'y':
                            self.use_local = True
                            return "RETRY_WITH_LOCAL"
                        else:
                            raise e
                else:
                    raise e

# --- 4. Scraping Helpers ---
def get_soup(url):
    session = requests.Session()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.google.com/",
        "Connection": "keep-alive",
    }
    try:
        response = session.get(url, headers=headers, timeout=20, allow_redirects=True)
        response.raise_for_status()
        return BeautifulSoup(response.text, 'html.parser')
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 403:
            print(f"🛡️ Blocked by WAF (403): {url}")
        else:
            print(f"❌ HTTP Error {e.response.status_code}: {url}")
        return None

def find_relevant_posts(llm_service: LLMManager, homepage_url: str, country: str):
    print(f"🔍 [LLM] Deep searching for posts about {country} on {homepage_url}...")
    soup = get_soup(homepage_url)
    if not soup: return []

    domain = urlparse(homepage_url).netloc
    all_links = []

    for a in soup.find_all('a', href=True):
        link = a['href']
        if link.startswith('/'):
            link = f"{urlparse(homepage_url).scheme}://{domain}{link}"
        if domain in link and not any(x in link for x in ["/tag/", "/category/", "/page/", "facebook.com", "instagram.com"]):
            all_links.append(link)

    test_links = list(set(all_links))[:100]
    if not test_links: return []

    prompt = f"""
        You are a travel URL analyzer. From the list provided, return a JSON object with a key "urls".
        The "urls" should contain ONLY links that are actual blog posts, travel guides, or destination articles about '{country}'.

        CRITICAL:
        - Exclude links to external booking sites (Booking.com, Viator, etc.).
        - Include only links that look like internal articles of the blog.
        - If a link is a city guide in {country}, include it.

        LIST TO ANALYZE:
        {test_links}
    """
    
    response = llm_service.invoke_with_retry(prompt)

    if response == "RETRY_WITH_LOCAL":
        print(f"🔄 Retrying URL analysis for {country} with local model...")
        return find_relevant_posts(llm_service, homepage_url, country)

    if not response: return []

    try:
        raw_content = response.content if hasattr(response, 'content') else response
        content = json.loads(raw_content)
        urls = content.get("urls", [])
        return [u for u in urls if domain in u]
    except Exception as e:
        print(f"⚠️ Error parsing URLs: {e}")
        return []

def extract_data_from_post(llm_service: LLMManager, url: str, country_name: str):
    soup = get_soup(url)
    if not soup: return None

    for s in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        s.decompose()

    clean_text = soup.get_text(separator=' ', strip=True)[:15000]

    prompt = f"""
            You are a travel data extraction specialist for {country_name}.
            Extract every beach, temple, hotel, restaurant, or attraction mentioned in the text.

            For the 'description' field:
            - ACT AS A RAW DATA EXTRACTOR.
            - DO NOT summarize or rewrite the author's words.
            - CAPTURE the author's original review, specific feedback, and sentiment.
            - INCLUDE specific details.

            Return JSON: {{ "places": [ {{ "place": "...", "country": "{country_name}", "region": "...", "place_type": "...", "google_maps_url": "...", "description": "..." }} ] }}

            TEXT:
            {clean_text}
            """

    response = llm_service.invoke_with_retry(prompt)

    if response == "RETRY_WITH_LOCAL":
        print(f"🔄 Retrying {url} with local model...")
        return extract_data_from_post(llm_service, url, country_name)

    if not response: return None

    try:
        raw_content = response.content if hasattr(response, 'content') else response
        content = json.loads(raw_content)
        raw_places = content.get("places", [])

        filtered_places = []
        for p in raw_places:
            ext_country = p.get("country", "").strip().lower()
            if country_name.lower() in ext_country or ext_country in country_name.lower():
                filtered_places.append(TravelPlace(**p))
        return TravelDataList(places=filtered_places)
    except Exception as e:
        print(f"⚠️ Extraction error at {url}: {e}")
        return None

# --- 5. Main Execution ---
def main(blog_name, country_data):
    country_name = country_data['country']
    category_url = country_data['category_url']
    
    llm_service = LLMManager(use_local=False) 

    # Safe dynamic paths
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    folder_path = os.path.join(project_root, "ScrapedData", blog_name.replace(" ", "_"))
    
    os.makedirs(folder_path, exist_ok=True)

    relevant_urls = find_relevant_posts(llm_service, category_url, country_name)
    
    all_results = []
    domain_info = urlparse(category_url)
    base_domain = f"{domain_info.scheme}://{domain_info.netloc}"

    for url in relevant_urls:
        if url.startswith('/'):
            url = base_domain + url
            
        print(f"📖 Scraping: {url}")
        data = extract_data_from_post(llm_service, url, country_name)
        if data and data.places:
            for item in data.places:
                row = item.model_dump()
                row['source_url'] = url
                row['blog_source'] = blog_name
                all_results.append(row)
        time.sleep(2)

    if all_results:
        df = pd.DataFrame(all_results)
        full_path = os.path.join(folder_path, f"travel_data_{country_name.replace(' ', '_')}.csv")
        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"🏆 Completed! Saved to {full_path}")

# --- 6. Configuration Loader ---
def load_config():
    # Safe dynamic path for config
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, ".."))
    config_path = os.path.join(project_root, "blogs.json")
    
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

if __name__ == "__main__":
    SITES_CONFIG = load_config()
    for blog_config in SITES_CONFIG:
        blog_name = blog_config['blog_name']
        for destination in blog_config['destinations']:
            try:
                main(blog_name, destination)
            except Exception as e:
                print(f"❌ Error: {e}")
            time.sleep(5)