import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.telegram_bot.job_catalog import available_jobs, numbered_jobs


class TelegramJobCatalogTests(unittest.TestCase):
    def test_available_jobs_lists_only_folders_with_pdfs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            folder = root / "acme"
            folder.mkdir()
            (folder / "job_config.yaml").write_text(yaml.safe_dump({
                "company": "Acme", "role": "Engineer", "output_name": "acme_cv",
            }), encoding="utf-8")
            (folder / "acme_cv.pdf").write_bytes(b"%PDF")
            jobs = available_jobs(root)
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].label, "Acme - Engineer")
        self.assertIn("1. Acme - Engineer", numbered_jobs(jobs))


if __name__ == "__main__":
    unittest.main()
