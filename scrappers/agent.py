import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
import os
from dotenv import load_dotenv
import json
from urllib.parse import urlparse
from langchain_ollama import ChatOllama

# --- configure ---
load_dotenv()

# todo: change from global parameter to a class
use_local_model = False
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CURRENT_MODEL = "llama-3.3-70b-versatile"
LOCAL_MODEL_NAME = "llama3.2:3b"

class TravelPlace(BaseModel):
    place: str = Field(description="Name of the specific attraction or spot")
    country: str = Field(description="Name of the country")
    region: str = Field(description="The specific area or city within the country")
    place_type: str = Field(description="the type of the point of interest")
    google_maps_url: str = Field(description="URL to Google Maps if mentioned, else 'N/A'")
    description: str = Field(description="A concise summary of the review or tips for this place")

class TravelDataList(BaseModel):
    places: List[TravelPlace]

def get_llm():
    """
    function that load the right model.
    """
    if use_local_model:
        print(f"🤖 Using Local Model (Ollama): {LOCAL_MODEL_NAME}")
        return ChatOllama(
            model=LOCAL_MODEL_NAME,
            temperature=0,
            format="json"
        )
    else:
        print(f"🤖 Using Groq Model: {CURRENT_MODEL}")
        return ChatGroq(
            temperature=0,
            model_name=CURRENT_MODEL,
            groq_api_key=GROQ_API_KEY
        ).bind(response_format={"type": "json_object"})

def invoke_with_retry(input_data, max_retries=3):
    global use_local_model

    # check 3 times and chose the model
    for i in range(max_retries):
        try:
            llm = get_llm()
            return llm.invoke(input_data)
        except Exception as e:
            # 429 if out of tokens
            if "429" in str(e) or "rate_limit" in str(e).lower():
                if i < max_retries - 1:
                    time.sleep((i + 1) * 10)
                else:
                    print("\n🛑 Groq Rate Limit Reached.")
                    choice = input("Switch to Local Ollama? (y/n): ").strip().lower()
                    if choice == 'y':
                        use_local_model = True
                        return "RETRY_WITH_LOCAL"
                    else:
                        raise e
            else:
                raise e

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

def find_relevant_posts(homepage_url, country):
    print(f"🔍 [LLM] Deep searching for posts about {country} on {homepage_url}...")
    soup = get_soup(homepage_url)
    if not soup: return []

    domain = urlparse(homepage_url).netloc
    all_links = []

    for a in soup.find_all('a', href=True):
        link = a['href']
        if link.startswith('/'):
            link = f"{urlparse(homepage_url).scheme}://{domain}{link}"

        # basic filtering of the url's
        if domain in link and not any(
                x in link for x in ["/tag/", "/category/", "/page/", "facebook.com", "instagram.com"]):
            all_links.append(link)

    all_links = list(set(all_links))
    test_links = all_links[:100]

    if not test_links:
        return []

    # get the right model
    llm = get_llm()

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

    response = invoke_with_retry(prompt)

    if response == "RETRY_WITH_LOCAL":
        print(f"🔄 Retrying URL analysis for {country} with local model...")
        return find_relevant_posts(homepage_url, country)

    if not response: return []

    try:
        # get the content
        raw_content = response.content if hasattr(response, 'content') else response
        content = json.loads(raw_content)
        urls = content.get("urls", [])
        return [u for u in urls if domain in u]
    except Exception as e:
        print(f"⚠️ Error parsing LLM response in find_relevant_posts: {e}")
        return []

def extract_data_from_post(url, country_name):
    soup = get_soup(url)
    if not soup: return None

    for s in soup(["script", "style", "nav", "footer", "header", "aside", "form"]):
        s.decompose()

    clean_text = soup.get_text(separator=' ', strip=True)[:15000]

    # get the right model
    llm = get_llm()

    prompt = f"""
            You are a travel data extraction specialist for {country_name}.
            Extract every beach, temple, hotel, restaurant, or attraction mentioned in the text.

            For the 'description' field:
            - ACT AS A RAW DATA EXTRACTOR.
            - DO NOT summarize or rewrite the author's words.
            - CAPTURE the author's original review, specific feedback, and sentiment.
            - INCLUDE specific details like "the water was crystal clear" or "the service was slow" rather than saying "the author liked the place".
            - The goal is to keep the original context so it can be analyzed for ratings later.

            Return JSON: {{ "places": [ {{ "place": "...", "country": "{country_name}", "region": "...", "place_type": "...", "google_maps_url": "...", "description": "..." }} ] }}

            TEXT:
            {clean_text}
            """

    response = invoke_with_retry(prompt)

    if response == "RETRY_WITH_LOCAL":
        print(f"🔄 Retrying {url} with local model...")
        return extract_data_from_post(url, country_name)

    if not response: return None

    try:
        # ב-Ollama התגובה לפעמים מגיעה כטקסט ישיר ולא כאובייקט עם .content
        # תלוי בגרסת ה-Langchain, לכן נבדוק את שניהם
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
        print(f"⚠️ Parsing error: {e}")
        return None

def main(blog_name, country_data):
    """
    מנהלת את תהליך הסריקה עבור מדינה ספציפית בבלוג ספציפי.
    country_data: dict containing 'country' and 'category_url'
    """
    country_name = country_data['country']
    category_url = country_data['category_url']

    all_results = []

    # יצירת נתיב לתיקייה לפי שם הבלוג (מחליף רווחים בקו תחתי)
    folder_path = "../ScrapedData/"+blog_name.replace(" ", "_")
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        print(f"📁 Created folder: {folder_path}")

    # מציאת הפוסטים הרלוונטיים
    relevant_urls = find_relevant_posts(category_url, country_name)
    print(f"✅ Found {len(relevant_urls)} posts for {country_name} in {blog_name}.")

    domain_info = urlparse(category_url)
    base_domain = f"{domain_info.scheme}://{domain_info.netloc}"

    for url in relevant_urls:
        if url.startswith('/'):
            url = base_domain + url

        print(f"📖 Scraping: {url}")
        data = extract_data_from_post(url, country_name)

        if data and data.places:
            print(f"✨ Found {len(data.places)} places in this post.")
            for item in data.places:
                row = item.model_dump()
                row['source_url'] = url
                row['blog_source'] = blog_name
                all_results.append(row)

        # השהייה קצרה בין פוסטים בתוך אותה מדינה
        time.sleep(2)

    # שמירה לקובץ בתוך התיקייה של הבלוג
    if all_results:
        df = pd.DataFrame(all_results)
        file_name = f"travel_data_{country_name}.csv"
        full_path = os.path.join(folder_path, file_name)

        df.to_csv(full_path, index=False, encoding='utf-8-sig')
        print(f"🏆 Completed {country_name}! Saved to {full_path}")
    else:
        print(f"❓ No data found for {country_name} in {blog_name}.")

with open("../blogs.json", 'r', encoding='utf-8') as f:
    SITES_CONFIG = json.load(f)

if __name__ == "__main__":
    for blog_config in SITES_CONFIG:
        blog_name = blog_config['blog_name']
        print(f"\n🌐 Starting work on blog: {blog_name}")

        for destination in blog_config['destinations']:
            print(f"\n📍 Processing Country: {destination['country']}")
            try:
                main(blog_name, destination)
            except Exception as e:
                print(f"❌ Error processing {destination['country']} in {blog_name}: {e}")

            print("😴 Sleeping between countries...")
            time.sleep(10)
