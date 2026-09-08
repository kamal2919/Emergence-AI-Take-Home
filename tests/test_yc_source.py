import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from signaldesk.sources.yc import collect_snapshot


class FakeHttpGet:
    def get(self, url):
        return (
            '<html><head><meta content="Example Co" property="og:title">'
            '<meta content="Example company description." property="og:description"></head></html>'
        )


class YCSourceTests(unittest.TestCase):
    def test_collects_dated_metadata_snapshot(self):
        urls = [f"https://www.ycombinator.com/companies/example-{number}" for number in range(10)]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            seed_path = root / "seed.json"
            output_path = root / "snapshot.json"
            seed_path.write_text(json.dumps({"company_urls": urls}))
            snapshots = collect_snapshot(
                seed_path,
                output_path,
                http_get=FakeHttpGet(),
                now=datetime(2026, 9, 8, tzinfo=UTC),
            )
            self.assertEqual(len(snapshots), 10)
            self.assertEqual(snapshots[0].title, "Example Co")
            self.assertEqual(json.loads(output_path.read_text())["pages"][0]["description"], "Example company description.")
