from abc import ABC, abstractmethod
from selenium import webdriver
import os
import pandas as pd

class BaseScraper(ABC):
    def __init__(self, driver, web_name):
        self.driver = driver
        self.web_name = web_name

    @abstractmethod
    def extract_links(self, category_url):
        """extract the links from the category page, each website has a different structure,
        gets a dict the contain the parent place and the category url,
        and returns a list of dicts with the parent place, title and link"""
        pass

    @abstractmethod
    def extract_post_data(self, post_url, parent_place, post_title):
        """extract the data from the post page, each website has a different structure,
        gets the post url and returns a dict with the post title, parent place and the links in the post"""
        pass

    def save_data(self, data_list, filename):
        """
        save the data to a CSV file, if the file already exists, it will append the new data to the existing file,
        and remove duplicates based on the 'place' and 'description' columns, keeping the first occurrence.
        """
        if not data_list:
            return

        # make the file if not exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        new_df = pd.DataFrame(data_list)

        # check if there is no duplicates
        if os.path.isfile(filename):
            existing_df = pd.read_csv(filename)
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            final_df = combined_df.drop_duplicates(subset=['place', 'description'], keep='first')
        else:
            final_df = new_df

        # make the csv file
        final_df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"Successfully saved to {filename}")

    def clean_filename(self, parent_place, post_title):
        """clean the post title to create a valid filename, keeping only alphanumeric characters and underscores, and truncating to 30 characters"""
        clean_title = "".join([c for c in post_title if c.isalnum() or c == ' ']).strip().replace(" ", "_")
        path = os.path.join("../ScrapedData", self.web_name, parent_place, f"{clean_title[:30]}.csv")
        return path
