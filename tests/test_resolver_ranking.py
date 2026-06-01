import unittest

from scripts.telegram_bot.resolver.ranking import rank_candidates


class ResolverRankingTests(unittest.TestCase):
    def test_ranking_is_deterministic_and_deduplicated(self):
        urls = [
            "https://example.com/privacy",
            "https://careers.example.com/jobs/42",
            "https://careers.example.com/jobs/42",
            "https://example.com/jobs/42",
        ]
        ranked = rank_candidates(urls, "https://example.com/original")
        self.assertEqual(ranked, [
            "https://example.com/jobs/42",
            "https://careers.example.com/jobs/42",
            "https://example.com/privacy",
        ])

    def test_same_score_uses_url_as_stable_tiebreaker(self):
        ranked = rank_candidates(["https://b.example/job/2", "https://a.example/job/1"])
        self.assertEqual(ranked, ["https://a.example/job/1", "https://b.example/job/2"])


if __name__ == "__main__":
    unittest.main()
