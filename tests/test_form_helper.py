import unittest
from naukri_assistant.form_helper import answer_candidates, is_sensitive_label, is_naukri_host


class FormHelperTests(unittest.TestCase):
    def test_never_matches_sensitive_fields(self):
        self.assertTrue(is_sensitive_label("PAN Card"))
        self.assertTrue(is_sensitive_label("Date of Birth"))
        self.assertTrue(is_sensitive_label("Mobile Number"))
        self.assertFalse(is_sensitive_label("Current Employer"))

    def test_ctc_is_not_disclosed_by_default(self):
        cfg = {"applicant": {"current_ctc_lpa": 8, "expected_ctc_lpa": 17, "ctc_disclosure": "ask"}}
        triggers = [trigger for group, _ in answer_candidates(cfg) for trigger in group]
        self.assertFalse(any("ctc" in trigger or "salary" in trigger for trigger in triggers))

    def test_ctc_requires_explicit_numeric_disclosure_policy(self):
        cfg = {"applicant": {"current_ctc_lpa": 8, "expected_ctc_lpa": 17, "ctc_disclosure": "numbers"}}
        triggers = [trigger for group, _ in answer_candidates(cfg) for trigger in group]
        self.assertIn("current ctc", triggers)
        self.assertIn("expected ctc", triggers)

    def test_host_guard(self):
        self.assertTrue(is_naukri_host("https://www.naukri.com/job-listings/a"))
        self.assertFalse(is_naukri_host("https://careers.example.com/apply"))


if __name__ == "__main__":
    unittest.main()
