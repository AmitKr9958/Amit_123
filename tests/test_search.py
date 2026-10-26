import unittest
from naukri_assistant.search import build_search_urls


class SearchTests(unittest.TestCase):
    def test_builds_expected_searches(self):
        cfg = {"keywords": ["Power BI Developer"], "locations": ["Delhi", "Remote"], "max_pages_per_search": 2}
        urls = build_search_urls(cfg)
        self.assertEqual(len(urls), 4)
        self.assertIn("power-bi-developer-jobs-in-delhi", urls[0][1])
        self.assertIn("k=Power%20BI%20Developer", urls[0][1])
        self.assertIn("power-bi-developer-jobs?", urls[2][1])


if __name__ == "__main__":
    unittest.main()
