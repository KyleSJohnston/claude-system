"""Tests for bazaar/scripts/bazaar_dispatch.py.

@decision DEC-BAZAAR-004
@title bazaar_dispatch.py for non-tool phases; mock mode for testing
@status accepted
@rationale Tests exercise real dispatch logic in mock mode — no API calls.
Covers: config parsing, mock dispatch, error isolation (one failure doesn't
block others), provider routing, output file writing, summary structure.
Mock mode reads from fixtures; tests verify the plumbing without live APIs.

No API calls — all tests use --mock mode with fixture files.
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

SKILL_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(SKILL_ROOT / "scripts"))

import bazaar_dispatch as bd


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def make_dispatch_config(dispatches: list) -> dict:
    """Helper: build a dispatches config dict."""
    return {"dispatches": dispatches}


def make_dispatch(
    dispatch_id: str,
    provider: str = "anthropic",
    fixture: str = None,
    output_file: str = None,
) -> dict:
    """Helper: build a single dispatch entry."""
    d = {
        "id": dispatch_id,
        "provider": provider,
        "user_prompt": f"Test prompt for {dispatch_id}",
        "system_prompt": "You are a test system.",
    }
    if fixture:
        d["mock_fixture"] = fixture
    if output_file:
        d["output_file"] = output_file
    return d


class TestMockDispatch(unittest.TestCase):

    def test_mock_dispatch_returns_fixture_content(self):
        fixture_path = str(FIXTURES_DIR / "sample_dispatch.json")
        dispatch = make_dispatch("test-01", fixture=fixture_path)

        text, model = bd._mock_dispatch(dispatch)

        self.assertIsInstance(text, str)
        self.assertIn("mock", model)
        # Content should be the fixture JSON
        data = json.loads(text)
        self.assertIn("ideator", data)

    def test_mock_dispatch_fallback_when_no_fixture(self):
        dispatch = make_dispatch("test-02", provider="openai")
        text, model = bd._mock_dispatch(dispatch)

        self.assertIsInstance(text, str)
        data = json.loads(text)
        self.assertTrue(data.get("mock"))
        self.assertEqual(data["dispatch_id"], "test-02")
        self.assertEqual(data["provider"], "openai")

    def test_mock_dispatch_missing_fixture_uses_fallback(self):
        dispatch = make_dispatch("test-03", fixture="/nonexistent/path.json")
        text, model = bd._mock_dispatch(dispatch)

        data = json.loads(text)
        self.assertTrue(data.get("mock"))


class TestRunSingleDispatch(unittest.TestCase):

    def test_mock_dispatch_success(self):
        fixture_path = str(FIXTURES_DIR / "sample_dispatch.json")
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "result.json")
            dispatch = make_dispatch("d-01", fixture=fixture_path, output_file=out)

            result = bd._run_single_dispatch(dispatch, mock=True)

            self.assertTrue(result["success"])
            self.assertEqual(result["dispatch_id"], "d-01")
            self.assertIsNone(result["error"])
            self.assertGreaterEqual(result["elapsed"], 0)  # mock may be sub-ms
            # Output file should be written
            self.assertTrue(Path(out).exists())

    def test_mock_dispatch_writes_output_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            out = str(Path(tmpdir) / "subdir" / "result.json")
            dispatch = make_dispatch("d-02", output_file=out)

            bd._run_single_dispatch(dispatch, mock=True)

            self.assertTrue(Path(out).exists())
            with open(out) as f:
                data = json.load(f)
            self.assertEqual(data["dispatch_id"], "d-02")

    def test_mock_dispatch_parses_json_output(self):
        fixture_path = str(FIXTURES_DIR / "sample_dispatch.json")
        dispatch = make_dispatch("d-03", fixture=fixture_path)

        result = bd._run_single_dispatch(dispatch, mock=True)

        # The fixture is valid JSON, so parsed should not be None
        self.assertIsNotNone(result["parsed"])
        self.assertIn("ideator", result["parsed"])

    def test_elapsed_time_recorded(self):
        dispatch = make_dispatch("d-04")
        result = bd._run_single_dispatch(dispatch, mock=True)
        self.assertGreaterEqual(result["elapsed"], 0)

    def test_result_has_all_required_fields(self):
        dispatch = make_dispatch("d-05")
        result = bd._run_single_dispatch(dispatch, mock=True)

        required = ["dispatch_id", "provider", "model_used", "text", "parsed",
                    "elapsed", "success", "error"]
        for field in required:
            self.assertIn(field, result, f"Missing field: {field}")


class TestDispatchAll(unittest.TestCase):

    def test_single_dispatch_mock(self):
        dispatches = [make_dispatch("batch-01")]
        summary = bd.dispatch_all(dispatches, mock=True)

        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["succeeded"], 1)
        self.assertEqual(summary["failed"], 0)
        self.assertEqual(len(summary["results"]), 1)

    def test_multiple_dispatches_parallel(self):
        dispatches = [make_dispatch(f"batch-{i}") for i in range(5)]
        summary = bd.dispatch_all(dispatches, mock=True, max_workers=3)

        self.assertEqual(summary["total"], 5)
        self.assertEqual(summary["succeeded"], 5)
        self.assertEqual(summary["failed"], 0)

    def test_error_isolation(self):
        """One bad dispatch should not prevent others from succeeding."""
        good_dispatch = make_dispatch("good-01")
        # Force an error by using a provider with no key and non-mock mode... but
        # we test error isolation differently: corrupt the dispatch so live call fails
        # In mock mode all succeed, so we test by patching _mock_dispatch behavior
        # Instead, test by injecting a dispatch that will raise during file write
        bad_dispatch = {
            "id": "bad-01",
            "provider": "anthropic",
            "user_prompt": "test",
            "system_prompt": "test",
            "output_file": "/dev/null/impossible/path.json",  # will fail to write
            "mock_fixture": str(FIXTURES_DIR / "sample_dispatch.json"),
        }
        dispatches = [good_dispatch, bad_dispatch, make_dispatch("good-02")]
        summary = bd.dispatch_all(dispatches, mock=True)

        # good-01 and good-02 succeed; bad-01 may fail on write but dispatch continues
        self.assertEqual(summary["total"], 3)
        # At least 2 succeed (the good ones)
        self.assertGreaterEqual(summary["succeeded"], 2)

    def test_empty_dispatches(self):
        summary = bd.dispatch_all([], mock=True)
        self.assertEqual(summary["total"], 0)
        self.assertEqual(summary["succeeded"], 0)
        self.assertEqual(summary["failed"], 0)

    def test_summary_has_results_list(self):
        dispatches = [make_dispatch("r-01"), make_dispatch("r-02")]
        summary = bd.dispatch_all(dispatches, mock=True)

        self.assertIn("results", summary)
        self.assertEqual(len(summary["results"]), 2)
        for r in summary["results"]:
            self.assertIn("dispatch_id", r)
            self.assertIn("success", r)

    def test_different_providers_routed(self):
        """Verify different providers produce different model_used labels in mock."""
        dispatches = [
            make_dispatch("a-01", provider="anthropic"),
            make_dispatch("o-01", provider="openai"),
            make_dispatch("g-01", provider="gemini"),
        ]
        summary = bd.dispatch_all(dispatches, mock=True)

        model_labels = {r["dispatch_id"]: r["model_used"] for r in summary["results"]}
        # Each should contain the provider name in mock mode
        self.assertIn("anthropic", model_labels["a-01"])
        self.assertIn("openai", model_labels["o-01"])
        self.assertIn("gemini", model_labels["g-01"])


class TestGetApiKey(unittest.TestCase):

    def test_unknown_provider_returns_none(self):
        key = bd._get_api_key("unknown-provider-xyz")
        self.assertIsNone(key)

    def test_known_provider_name_accepted(self):
        """Known provider names map to env key names without error."""
        for provider in ["anthropic", "openai", "gemini", "perplexity"]:
            # Don't assert key value — may or may not be set in test env
            # Just verify no exception is raised
            try:
                bd._get_api_key(provider)
            except Exception as e:
                self.fail(f"_get_api_key({provider!r}) raised {e}")


class TestLoadProvider(unittest.TestCase):

    def test_unknown_provider_raises(self):
        with self.assertRaises(ImportError):
            bd._load_provider("does-not-exist")

    def test_known_providers_importable(self):
        """All known provider modules should be importable."""
        for provider in ["anthropic", "openai", "gemini", "perplexity"]:
            try:
                module = bd._load_provider(provider)
                self.assertTrue(hasattr(module, "chat"),
                               f"{provider} module missing chat() function")
            except ImportError as e:
                self.fail(f"Failed to import {provider}: {e}")


class TestKeychainDirResolution(unittest.TestCase):
    """Verify KEYCHAIN_DIR resolves to a path rooted at the ~/.claude project.

    DEC-BAZAAR-010: KEYCHAIN_DIR is computed by walking up from __file__
    to the first directory containing CLAUDE.md (the project anchor), then
    appending scripts/lib. This is robust across worktrees and file moves,
    unlike the fragile parents[N] approach it replaced.
    """

    def test_keychain_dir_contains_scripts_lib(self):
        """KEYCHAIN_DIR path should end in 'scripts/lib'."""
        parts = bd.KEYCHAIN_DIR.parts
        self.assertGreaterEqual(len(parts), 2,
                                "KEYCHAIN_DIR should have at least 2 path components")
        self.assertEqual(parts[-1], "lib",
                         f"KEYCHAIN_DIR should end in 'lib', got: {bd.KEYCHAIN_DIR}")
        self.assertEqual(parts[-2], "scripts",
                         f"KEYCHAIN_DIR parent should be 'scripts', got: {bd.KEYCHAIN_DIR}")

    def test_keychain_dir_rooted_at_claude_root(self):
        """KEYCHAIN_DIR parent (scripts/) should be a sibling of CLAUDE.md."""
        scripts_dir = bd.KEYCHAIN_DIR.parent   # .../scripts
        claude_root = scripts_dir.parent        # .../.claude
        claude_md = claude_root / "CLAUDE.md"
        self.assertTrue(
            claude_md.exists(),
            f"Expected CLAUDE.md at {claude_md} — KEYCHAIN_DIR may be miscalculated. "
            f"KEYCHAIN_DIR={bd.KEYCHAIN_DIR}"
        )

    def test_find_claude_root_returns_directory_with_claude_md(self):
        """_find_claude_root() should return a directory containing CLAUDE.md."""
        root = bd._find_claude_root()
        self.assertTrue(
            (root / "CLAUDE.md").exists(),
            f"_find_claude_root() returned {root!r} which has no CLAUDE.md"
        )


class TestStripMarkdownFencing(unittest.TestCase):
    """Verify _strip_markdown_fencing() handles all fence variants correctly.

    DEC-BAZAAR-011: LLMs wrap JSON in markdown fences despite being told
    not to. This function strips fences before json.loads() so the parser
    receives clean JSON.
    """

    def test_plain_json_unchanged(self):
        """Plain JSON with no fencing should be returned unchanged."""
        payload = '{"key": "value", "num": 42}'
        self.assertEqual(bd._strip_markdown_fencing(payload), payload)

    def test_json_fence_with_language_tag(self):
        """```json ... ``` fencing should be stripped."""
        fenced = '```json\n{"key": "value"}\n```'
        result = bd._strip_markdown_fencing(fenced)
        self.assertEqual(result, '{"key": "value"}')

    def test_json_fence_without_language_tag(self):
        """``` ... ``` fencing (no language tag) should be stripped."""
        fenced = '```\n{"key": "value"}\n```'
        result = bd._strip_markdown_fencing(fenced)
        self.assertEqual(result, '{"key": "value"}')

    def test_whitespace_around_fences_stripped(self):
        """Leading/trailing whitespace around fences should be stripped."""
        fenced = '  \n```json\n{"key": "value"}\n```\n  '
        result = bd._strip_markdown_fencing(fenced)
        self.assertEqual(result, '{"key": "value"}')

    def test_stripped_output_is_valid_json(self):
        """Result after stripping should be parseable as JSON."""
        fenced = '```json\n{"ideas": ["a", "b", "c"], "score": 9}\n```'
        stripped = bd._strip_markdown_fencing(fenced)
        parsed = json.loads(stripped)
        self.assertEqual(parsed["score"], 9)
        self.assertEqual(len(parsed["ideas"]), 3)

    def test_run_single_dispatch_parses_fenced_fixture(self):
        """_run_single_dispatch() should parse JSON even when fixture is fenced."""
        # Build a fenced JSON fixture on the fly
        inner = json.dumps({"ideator": "test", "ideas": ["x"]})
        fenced_content = f"```json\n{inner}\n```"

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write fenced content as the fixture file
            fixture_path = Path(tmpdir) / "fenced_fixture.json"
            fixture_path.write_text(fenced_content)

            dispatch = make_dispatch("fence-01", fixture=str(fixture_path))
            result = bd._run_single_dispatch(dispatch, mock=True)

        self.assertTrue(result["success"])
        # text should be the raw fenced content
        self.assertIn("```", result["text"])
        # parsed should have been successfully extracted despite fencing
        self.assertIsNotNone(result["parsed"],
                             "parsed should not be None for fenced JSON output")
        self.assertIn("ideator", result["parsed"])


if __name__ == "__main__":
    unittest.main()
