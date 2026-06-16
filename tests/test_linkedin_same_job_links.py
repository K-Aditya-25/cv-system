import unittest
from unittest.mock import MagicMock

from scripts.telegram_bot.resolver.fetch import FetchResult
from scripts.telegram_bot.resolver.service import ResolverService
from scripts.telegram_bot.resolver_models import ResolutionRequest


def jsonld():
    words = " ".join(["backend reliability scalability observability testing"] * 12)
    return (
        '<script type="application/ld+json">'
        '{"@type":"JobPosting","title":"Graduate SWE","hiringOrganization":{"name":"eBay"},'
        '"description":"What you will accomplish<br>' + words + '"}'
        "</script>"
    )


class LinkedinSameJobLinksTests(unittest.TestCase):
    def test_tries_same_job_link_from_direct_html_before_discovery(self):
        linked = "https://ie.linkedin.com/jobs/view/role-at-ebay-1234567890"
        discover = MagicMock()
        fetch = MagicMock(side_effect=[
            FetchResult("https://www.linkedin.com/jobs/view/1234567890/", f'<a href="{linked}">same</a>'),
            FetchResult(linked, jsonld()),
        ])
        result = ResolverService(fetch=fetch, discover=discover, cache={}).resolve(
            ResolutionRequest(1, "https://www.linkedin.com/jobs/view/1234567890/"))
        self.assertEqual(result.status, "resolved")
        self.assertEqual(fetch.call_args_list[1].args[0], linked)
        discover.search.assert_not_called()


if __name__ == "__main__":
    unittest.main()
