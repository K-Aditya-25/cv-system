import unittest

from scripts.job_creation.compact_refiner import _compact_prompt
from tests.test_refinement_router import router_context


class CompactRefinerTests(unittest.TestCase):
    def test_compact_prompt_omits_candidate_inventory_and_job_description(self):
        context = router_context()
        prompt = _compact_prompt(context, "polish wording")
        self.assertIn("polish wording", prompt)
        self.assertIn("\\section{Projects}", prompt)
        self.assertIn("Current Job Config", prompt)
        self.assertIn("Current Selection", prompt)
        self.assertNotIn("Candidate Inventory", prompt)
        self.assertNotIn("Job description", prompt)


if __name__ == "__main__":
    unittest.main()
