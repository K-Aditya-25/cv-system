import json
import unittest
from unittest.mock import patch

from scripts.create_job_from_description import call_claude_for_valid_payload, repair_selected_skill_categories
from tests.pdf_fixtures import database_with_skills


class SkillRepairTests(unittest.TestCase):
    def test_skill_category_repair_moves_existing_skill_to_canonical_category(self) -> None:
        payload = {"selection": {"skills": {"machine_learning": ["Explainable AI", "Interpretability"]}}}
        repairs = repair_selected_skill_categories(payload, database_with_skills())
        self.assertEqual(repairs, ["Explainable AI: machine_learning -> ai_llm_engineering"])
        self.assertEqual(payload["selection"]["skills"], {
            "ai_llm_engineering": ["Explainable AI"], "machine_learning": ["Interpretability"],
        })

    def test_validation_retry_uses_allowed_skills_and_previous_payload(self) -> None:
        invalid = {
            "job_config": {"company": "Target", "role": "Engineer", "output_name": "target_engineer"},
            "selection": {"skills": {"machine_learning": ["Responsible AI"]}},
            "job_summary_text": "Target engineer role.", "selection_rationale": ["Initial selection."],
        }
        valid = {
            "job_config": {"company": "Target", "role": "Engineer", "output_name": "target_engineer"},
            "selection": {"skills": {"machine_learning": ["Interpretability"]}},
            "job_summary_text": "Target engineer role.", "selection_rationale": ["Corrected selection."],
        }
        with patch("scripts.create_job_from_description.call_anthropic", side_effect=[json.dumps(invalid), json.dumps(valid)]) as call_mock:
            payload, _, selection, repairs = call_claude_for_valid_payload(
                system_prompt="System", user_prompt="Original", model="model",
                database=database_with_skills(), allow_longer_cv=False,
            )
        self.assertEqual(payload, valid)
        self.assertEqual(selection.skills, {"machine_learning": ["Interpretability"]})
        self.assertEqual(repairs, [])
        self.assertEqual(call_mock.call_count, 2)
        retry_prompt = call_mock.call_args_list[1].args[1]
        for text in ["Validation error:", "Responsible AI", "Allowed skills by category:", "Explainable AI", "Previous JSON:"]:
            self.assertIn(text, retry_prompt)
