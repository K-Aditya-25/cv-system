import io
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from scripts.telegram_bot.resolver.boundary_planner import PlannedBoundary
from scripts.telegram_bot.resolver.fetch import FetchResult
from scripts.telegram_bot.resolver.service import ResolverService
from scripts.telegram_bot.resolver_models import ResolutionRequest, SearchCandidate


def jsonld(title="Graduate SWE"):
    words = " ".join(["backend reliability scalability observability testing"] * 12)
    return (
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"' + title + '","hiringOrganization":{"name":"eBay"},'
        '"description":"<strong>What you will accomplish</strong><br>' + words + '"}'
        "</script>"
    )


class LinkedinFastPipelineTests(unittest.TestCase):
    def test_linkedin_direct_json_ld_resolves_without_discovery(self):
        discover = MagicMock()
        fetch = MagicMock(return_value=FetchResult("https://linkedin.com/jobs/view/1234567890", jsonld()))
        result = ResolverService(fetch=fetch, discover=discover, cache={}).resolve(
            ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.posting.metadata.company, "eBay")
        discover.search.assert_not_called()

    def test_linkedin_tries_one_discovered_candidate_after_direct_failure(self):
        candidate = SearchCandidate("https://ie.linkedin.com/jobs/view/role-at-ebay-1234567890")
        discover = MagicMock(search=MagicMock(return_value=SimpleNamespace(candidates=(candidate,))))
        fetch = MagicMock(side_effect=[
            FetchResult("https://www.linkedin.com/jobs/view/1234567890/", "<html>blocked</html>"),
            FetchResult(candidate.url, jsonld()),
        ])
        with patch("scripts.telegram_bot.resolver.linkedin_fast_extract.tensorix_description_filter",
                   return_value=PlannedBoundary(None, "timeout")):
            result = ResolverService(fetch=fetch, discover=discover, cache={}).resolve(
                ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "resolved")
        self.assertEqual(fetch.call_count, 2)

    def test_linkedin_clean_visible_sections_resolve_deterministically(self):
        html = "<html><body><main><h2>What you will accomplish</h2><p>" + (
            "Build production backend services improve reliability scalability observability "
            "testing debugging automation distributed marketplace data platforms. " * 4
        ) + "</p><h2>What you will bring</h2><p>Java Python SQL NoSQL Kubernetes Kafka.</p></main></body></html>"
        result = ResolverService(fetch=MagicMock(return_value=FetchResult("https://x", html)),
                                 discover=[], cache={}).resolve(
            ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "resolved")

    def test_linkedin_tensorix_failure_returns_manual_required(self):
        fetch = MagicMock(return_value=FetchResult("https://x", "<html><body>blocked</body></html>"))
        with patch("scripts.telegram_bot.resolver.linkedin_fast_extract.tensorix_description_filter",
                   return_value=PlannedBoundary(None, "timeout")):
            result = ResolverService(fetch=fetch, discover=[], cache={}).resolve(
                ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "needs_explicit_link")

    def test_linkedin_ignores_discovery_candidates_without_same_job_id(self):
        discover = MagicMock(search=MagicMock(return_value=SimpleNamespace(candidates=(
            SearchCandidate("https://careers.linkedin.com"),
            SearchCandidate("https://www.linkedin.com/jobs/search"),
        ))))
        fetch = MagicMock(return_value=FetchResult("https://x", "<html><body>blocked</body></html>"))
        with patch("scripts.telegram_bot.resolver.linkedin_fast_extract.tensorix_description_filter",
                   return_value=PlannedBoundary(None, "timeout")):
            result = ResolverService(fetch=fetch, discover=discover, cache={}).resolve(
                ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "needs_explicit_link")
        fetch.assert_called_once()

    def test_route_logs_include_strategy_and_method(self):
        fetch = MagicMock(return_value=FetchResult("https://linkedin.com/jobs/view/1234567890", jsonld()))
        output = io.StringIO()
        with redirect_stdout(output):
            ResolverService(fetch=fetch, discover=[], cache={}).resolve(
                ResolutionRequest(7, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertIn("strategy=linkedin_fast_pipeline", output.getvalue())
        self.assertIn("decision=resolved method=json-ld", output.getvalue())

    def test_non_linkedin_keeps_direct_first_path(self):
        discover = MagicMock()
        extract = MagicMock(return_value=SimpleNamespace(description="ok", title="", company="", location=""))
        result = ResolverService(
            fetch=MagicMock(return_value=FetchResult("https://jobs.example/1", "<html/>")),
            extract=extract, discover=discover, cache={},
        ).resolve(ResolutionRequest(1, "https://jobs.example/1"))
        self.assertEqual(result.status, "resolved")
        discover.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
