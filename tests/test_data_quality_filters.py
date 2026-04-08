import unittest

from DataProcess.agg_by_country import is_placeholder_description as agg_is_placeholder
from scrappers.agent import is_placeholder_description as scraper_is_placeholder


class DataQualityFilterTests(unittest.TestCase):
    def test_placeholder_phrases_are_blocked(self):
        self.assertTrue(agg_is_placeholder("Not mentioned in this text."))
        self.assertTrue(scraper_is_placeholder("No specific details were provided."))

    def test_real_descriptions_are_kept(self):
        text = "A riverside temple with detailed murals and excellent sunset views."
        self.assertFalse(agg_is_placeholder(text))
        self.assertFalse(scraper_is_placeholder(text))


if __name__ == "__main__":
    unittest.main()
