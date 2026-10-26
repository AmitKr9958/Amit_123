import tempfile
import unittest
from pathlib import Path
from naukri_assistant.db import JobStore


class StoreTests(unittest.TestCase):
    def test_deduplicates_and_tracks_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = JobStore(Path(tmp) / "test.sqlite3")
            job = {
                "job_id": "123456789",
                "url": "https://www.naukri.com/job-listings/example-123456789",
                "title": "Power BI Developer", "company": "Example", "location": "Delhi",
                "experience": "5-8 years", "posted_text": "1 day ago", "description": "Power BI SQL",
                "search_query": "test", "match_score": 65, "matched_skills": "Power BI, SQL",
                "excluded_reasons": "", "matched_at": "2026-10-26T12:00:00+00:00"
            }
            self.assertEqual(db.upsert_job(job), "new")
            self.assertEqual(db.upsert_job(job), "seen")
            self.assertTrue(db.update_status("123456789", "applied"))
            self.assertEqual(db.get_job("123456789")["status"], "applied")
            db.close()


if __name__ == "__main__":
    unittest.main()
