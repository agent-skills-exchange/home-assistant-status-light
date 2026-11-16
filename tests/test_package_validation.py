"""Offline negative fixtures for optional development validation dependencies."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
try:
    import jsonschema
    import skills_ref
except ImportError:
    AVAILABLE = False
else:
    AVAILABLE = True
    spec = importlib.util.spec_from_file_location("validate_package", ROOT / "scripts/validate_package.py")
    checks = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(checks)


@unittest.skipUnless(AVAILABLE, "Install requirements-ci.txt for package checks")
class PackageTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads((ROOT / "dependencies.json").read_text())
        self.schema = json.loads((ROOT / "schemas/dependencies-v1.schema.json").read_text())

    def check_manifest(self):
        checks.check_manifest(ROOT, self.manifest, self.schema)

    def test_current_package(self):
        checks.check_package(ROOT)

    def test_missing_required_field(self):
        del self.manifest["credentials"]
        with self.assertRaises(jsonschema.ValidationError):
            self.check_manifest()

    def test_unknown_feature(self):
        self.manifest["software"][0]["applies_to"] = ["missing"]
        with self.assertRaises(ValueError):
            self.check_manifest()

    def test_unknown_platform(self):
        self.manifest["software"][0]["platforms"] = ["missing"]
        with self.assertRaises(ValueError):
            self.check_manifest()

    def test_duplicate_id(self):
        self.manifest["software"].append(copy.deepcopy(self.manifest["software"][0]))
        with self.assertRaises(ValueError):
            self.check_manifest()

    def test_missing_instructions(self):
        self.manifest["software"][0]["installation"]["instructions"] = "missing.md"
        with self.assertRaises(ValueError):
            self.check_manifest()

    def test_local_reference_escape(self):
        with self.assertRaises(ValueError):
            checks.local_file(ROOT, "../outside.md")

    def test_broken_document_link(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "README.md").write_text("[missing](missing.md)")
            with self.assertRaises(ValueError):
                checks.check_links(root)

    def test_duplicate_json_key(self):
        with self.assertRaises(ValueError):
            json.loads('{"duplicate": 1, "duplicate": 2}', object_pairs_hook=checks.unique_object)

    def test_wrong_lock_digest(self):
        self.manifest["lockfiles"] = [{"path": "README.md", "sha256": "0" * 64,
            "format": "synthetic", "applies_to": ["status-signals"]}]
        with self.assertRaises(ValueError):
            self.check_manifest()


if __name__ == "__main__":
    unittest.main()
