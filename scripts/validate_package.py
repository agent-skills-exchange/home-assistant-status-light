"""Offline package checks. Development dependencies: requirements-ci.txt.

SPDX-License-Identifier: GPL-3.0-or-later. Assisted-by: Briar.
No HA access, credential lookup, remote schema resolution or installation.
"""
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

from jsonschema import Draft202012Validator
from skills_ref.parser import read_properties
from skills_ref.validator import validate

ROOT = Path(__file__).resolve().parents[1]
SECTIONS = ("platforms", "hosts", "software", "skills", "network", "credentials", "lockfiles")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key")
        result[key] = value
    return result


def read_json(path):
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_object)


def local_file(root, relative, base=None):
    root = root.resolve()
    if Path(relative).is_absolute():
        raise ValueError("Absolute local reference")
    target = ((base or root) / relative).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise ValueError("Missing or escaping local reference")
    return target


def check_manifest(root, manifest, schema):
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(manifest)
    features = set(manifest["features"])
    platforms = {item["id"] for item in manifest["platforms"]}
    for section in SECTIONS:
        ids = [item["id"] for item in manifest[section] if "id" in item]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate dependency ID")
        for item in manifest[section]:
            if set(item["applies_to"]) - features:
                raise ValueError("Unknown feature reference")
            if set(item.get("platforms", [])) - platforms:
                raise ValueError("Unknown platform reference")
            for evidence in item.get("support", {}).get("evidence", []):
                local_file(root, evidence)
            if "installation" in item:
                local_file(root, item["installation"]["instructions"])
            if "provisioning" in item:
                local_file(root, item["provisioning"])
            if section == "lockfiles":
                path = local_file(root, item["path"])
                if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
                    raise ValueError("Lockfile digest mismatch")


def check_links(root):
    # This package uses ordinary inline links, not a general Markdown dialect.
    # Validate tracked documentation areas only; do not inspect private configs.
    documents = list(root.glob("*.md"))
    for directory in ("references", "tests"):
        documents.extend((root / directory).glob("*.md"))
    for document in documents:
        for match in re.finditer(r"!?\[[^\]\n]*\]\(([^)\n]+)\)", document.read_text()):
            destination = match.group(1).strip().removeprefix("<").removesuffix(">")
            url = urlsplit(destination)
            if url.scheme or url.netloc or not url.path:
                continue  # External links are not fetched; anchors are not checked.
            local_file(root, unquote(url.path), document.parent)


def check_package(root=ROOT):
    errors = validate(root)
    if errors:
        raise ValueError("Agent Skills reference validation failed: " + "; ".join(errors))
    props = read_properties(root).to_dict()
    metadata = props.get("metadata", {})
    for key in ("agent-skills-exchange-dependencies", "agent-skills-exchange-compatibility"):
        local_file(root, metadata[key])
    manifest = read_json(root / metadata["agent-skills-exchange-dependencies"])
    schema = read_json(root / "schemas/dependencies-v1.schema.json")
    check_manifest(root, manifest, schema)
    check_links(root)


if __name__ == "__main__":
    check_package()
    print("Official Agent Skills format, dependency profile and local references: valid")
