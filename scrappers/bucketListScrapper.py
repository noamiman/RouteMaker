import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from scrappers.base_scrapper import BaseScraper
from DataProcess.DataProcessor import TravelDataProcessor

class bucketlistlyScraper(BaseScraper):
    def extract_links(self, category_url):
        """
        the function gets the category url and returns a list of dicts with the post title and link.
        :param category_url: the url of the category page to extract the links from.
        :return posrts_data: a list of dicts with the post title and link.
        """
        print(f"--- Fetching links from: {category_url} ---")
        # use the driver to get the category page
        self.driver.get(category_url)

        posts_data = []
        try:
            # wait max 10 seconds for the related-post links to be present
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a.related-post")))

            cards = self.driver.find_elements(By.CSS_SELECTOR, "a.related-post")
            print(f"found: {len(cards)} cards")

            for card in cards:
                try:
                    # gets the link and title of the post and add it to the posts_data list
                    link = card.get_attribute("href")
                    title_el = card.find_elements(By.TAG_NAME, "h3")
                    title = title_el[0].text.strip() if title_el else "No Title"
                    posts_data.append({"title": title, "link": link})
                except:
                    continue
        except Exception as e:
            print(f"Error extracting links: {e}")
        return posts_data


    def extract_post_data(self, post_url, parent_place, post_title):
        """
        the function gets the post url and returns a dict with the post title, parent place and the links in the post.
        :param post_url: the url of the post page to extract the data from.
        :param parent_place: the parent place of the post, which is the country in our case, to add it to the final data dict.
        :param post_title: the title of the post, to add it to the final data dict and to create the filename for the csv file.
        :return: a dict with the post title, parent place and the links in the post.
        """
        try:
            print(f"Scraping: {post_title}")
            # use the driver to get the post page
            self.driver.get(post_url)

            # wait max 10 seconds for the paragraphs to be present
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, "p")))

            # find all elements with the class name "first-of-type" and get their text, which are the place names we want to target
            elements = self.driver.find_elements(By.CLASS_NAME, "first-of-type")
            target_names = {e.text.strip() for e in elements if e.text.strip()}

            # if we found target names, we will look for links in the paragraphs that contain those names, and if we find them, we will add them to the results list with the place name, description, google maps url and country.
            results = []
            paragraphs = self.driver.find_elements(By.TAG_NAME, "p")

            if target_names:
                for p in paragraphs:
                    links_in_p = p.find_elements(By.TAG_NAME, "a")
                    for link_element in links_in_p:
                        name_found = link_element.text.strip()
                        # בתוך הלופ של הסקרייפר - רק איסוף נתונים
                        if name_found in target_names:
                            results.append({
                                "place": name_found,
                                "raw_description": p.text.replace(name_found, "").strip(),  # שומרים את המקור
                                "google_maps_url": link_element.get_attribute("href"),
                                "country": parent_place
                            })

                        # מחוץ ללופ - עיבוד מרוכז (או פשוט קריאה למעבד)
                        for res in results:
                            res["description"] = TravelDataProcessor.process_description(res["raw_description"])

            if len(results)<3:
                print(f"DEBUG: Falling back to general link search for {post_title}")
                all_links = self.driver.find_elements(By.TAG_NAME, "a")
                for l in all_links:
                    href = l.get_attribute("href") or ""
                    if "google.com/maps" in href or "goo.gl/maps" in href or "amap.com" in href:
                        place_name = l.text.strip()
                        if place_name and len(place_name) > 1:
                            try:
                                parent_p = l.find_element(By.XPATH, "./..")
                                description = parent_p.text.replace(place_name, "").strip()
                            except:
                                description = "No description available"

                            results.append({
                                "place": place_name,
                                "description": description,
                                "google_maps_url": href,
                                "country": parent_place
                            })

            if results:
                filename = self.clean_filename(parent_place, post_title)
                self.save_data(results, filename)
            else:
                print(f"WARNING: Still no data found for {post_title}")

        except Exception as e:
            print(f"Error in {post_url}: {e}")


if __name__ == "__main__":

    chrome_options = Options()
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    scraper = bucketlistlyScraper(driver, web_name="Bucketlistly")

    my_categories = {
        "South-Korea": "https://www.bucketlistly.blog/destinations/south-korea"
    }

    try:
        for parent_name, url in my_categories.items():
            all_posts = scraper.extract_links(url)
            for post in all_posts:
                scraper.extract_post_data(post['link'], parent_name, post['title'])
                time.sleep(random.uniform(3, 5))
    finally:
        driver.quit()