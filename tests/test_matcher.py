import unittest
from naukri_assistant.matcher import score_job, parse_posted_days, parse_experience_range, parse_salary_range


class MatcherTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "keywords": ["Power BI Developer", "Data Analyst"],
            "locations": ["Delhi", "Gurugram", "Noida", "Remote"],
            "skills": ["Power BI", "DAX", "SQL", "Power Query"],
            "exclude_keywords": ["internship", "fresher"],
            "experience_min": 5,
            "experience_max": 12,
            "posted_within_days": 5,
            "salary_floor_lpa": 16,
            "min_match_score": 25
        }

    def test_strong_power_bi_role_scores(self):
        result = score_job({
            "title": "Power BI Developer", "company": "Example",
            "location": "Gurugram", "description": "Power BI, DAX, SQL, Power Query dashboards",
            "experience": "5-8 years", "posted_text": "1 day ago", "salary_text": "18-25 LPA"
        }, self.cfg)
        self.assertGreaterEqual(result["match_score"], 70)
        self.assertTrue(result["is_eligible"])
        self.assertIn("Power BI", result["matched_skills"])

    def test_fresher_roles_excluded(self):
        result = score_job({"title": "Power BI Fresher", "company": "", "location": "Delhi", "description": "Power BI"}, self.cfg)
        self.assertEqual(result["match_score"], 0)
        self.assertFalse(result["is_eligible"])

    def test_unrelated_role_scores_lower(self):
        result = score_job({"title": "Accountant", "company": "", "location": "Mumbai", "description": "Tally"}, self.cfg)
        self.assertLess(result["match_score"], 35)
        self.assertFalse(result["is_eligible"])

    def test_out_of_range_experience_is_excluded(self):
        result = score_job({
            "title": "Power BI Developer", "company": "Example", "location": "Delhi",
            "experience": "1-3 years", "posted_text": "Today", "salary_text": "20-25 LPA"
        }, self.cfg)
        self.assertIn("experience outside", result["excluded_reasons"])

    def test_stale_job_is_excluded(self):
        result = score_job({
            "title": "Power BI Developer", "company": "Example", "location": "Delhi",
            "experience": "5-8 years", "posted_text": "14 days ago", "salary_text": "20-25 LPA"
        }, self.cfg)
        self.assertIn("posted 14 days ago", result["excluded_reasons"])

    def test_salary_below_floor_is_excluded(self):
        result = score_job({
            "title": "Power BI Developer", "company": "Example", "location": "Noida",
            "experience": "5-8 years", "posted_text": "2 days ago", "salary_text": "8-12 LPA"
        }, self.cfg)
        self.assertIn("salary maximum below", result["excluded_reasons"])

    def test_parse_helpers(self):
        self.assertEqual(parse_posted_days("1 day ago"), 1)
        self.assertEqual(parse_posted_days("2 weeks ago"), 14)
        self.assertEqual(parse_experience_range("5-8 Yrs"), (5, 8))
        self.assertEqual(parse_salary_range("12-18 LPA"), (12.0, 18.0))


if __name__ == "__main__":
    unittest.main()
