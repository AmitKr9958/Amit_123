import unittest
from naukri_assistant.matcher import score_job


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "keywords": ["Power BI Developer", "Data Analyst"],
            "locations": ["Delhi", "Gurugram", "Noida", "Remote"],
            "skills": ["Power BI", "DAX", "SQL", "Power Query"],
            "exclude_keywords": ["internship", "fresher"]
        }

    def test_strong_power_bi_role_scores(self):
        result = score_job({
            "title": "Power BI Developer", "company": "Example",
            "location": "Gurugram", "description": "Power BI, DAX, SQL, Power Query dashboards"
        }, self.cfg)
        self.assertGreaterEqual(result["match_score"], 70)
        self.assertIn("Power BI", result["matched_skills"])

    def test_fresher_roles_excluded(self):
        result = score_job({"title": "Power BI Fresher", "company": "", "location": "Delhi", "description": "Power BI"}, self.cfg)
        self.assertEqual(result["match_score"], 0)

    def test_unrelated_role_scores_lower(self):
        result = score_job({"title": "Accountant", "company": "", "location": "Mumbai", "description": "Tally"}, self.cfg)
        self.assertLess(result["match_score"], 35)


if __name__ == "__main__":
    unittest.main()
