# Agent Skills compatibility

Checked against the public [Agent Skills specification](https://agentskills.io/specification)
on 16 November 2026, using the official Python `skills-ref` 0.1.0 at upstream
commit `f130f348f502d9804278a617f86929846896d2e9`. An earlier check used a
same-name npm tool (0.1.5); that was not the official reference validator.
The official validator now passes too. The published specification does
not supply a numbered format version; this is a dated compatibility check,
not a certification or a promise about future revisions.

## Standard package format

- The directory and frontmatter name are `home-assistant-status-light`.
- `SKILL.md` contains YAML frontmatter followed by Markdown instructions.
- Required `name` and `description` fields meet the naming/length constraints.
- `license` and `compatibility` use the standard optional fields.
- Additional metadata uses the standard string-to-string `metadata` mapping.
- Instructions are below the recommended 500-line limit; scripts, setup,
  troubleshooting and examples are separate resources referenced relatively.
- No experimental `allowed-tools` declaration or host-specific tool grants
  are needed. Execution remains subject to the user's host controls.

Validate from the directory containing the package:

```sh
python -m pip install --require-hashes -r home-assistant-status-light/requirements-ci.txt
python home-assistant-status-light/scripts/validate_package.py
```

`requirements-ci.txt` pins the official validator source archive and development
dependencies with hashes. The validator is imported by its Python module name,
not an ambiguous host command. `skills-ref` is not a runtime dependency. Format
validation checks frontmatter and naming; it is not a security review, an
installation test or an end-to-end HA test.

CI also validates the dependency JSON against the bundled draft v1 schema,
cross-referenced features/platforms and local documentation/dependency files.
External links and anchors are not fetched or validated. The schema snapshot
is GPL-3.0-or-later Exchange draft source, byte-identical to the profile used
for initial validation (SHA-256
`4eb294994ba61661b5558ab5f60735bcb1404a137270bc4a6a806412a7a609ce`).
It remains a draft extension, not an official Agent Skills schema. Validators
are development-only; the operational helper remains standard-library-only.

## Exchange extension

`dependencies.json` follows the Exchange draft dependency profile v1, not the
core Agent Skills specification. It is linked through a namespaced metadata
key rather than new top-level frontmatter fields. The compatibility-notes key
is also namespaced. A standard host may ignore these custom metadata values;
the package still provides ordinary Markdown setup/dependency instructions.

Neither the standard nor the manifest provides dependency installation,
credential provisioning, runtime permission enforcement or automatic loading.
No particular host, Briar integration or Bluetooth adapter is required by the
helper. iStrip+/ESPHome are optional HA-side infrastructure, not Agent Skills
format requirements.

## What has and has not been tested

The original helper has 26 passing offline tests on Linux x86_64 under Python
3.11 and 3.14 in [GitHub Actions run 43875730256](https://github.com/agent-skills-exchange/home-assistant-status-light/actions/runs/43875730256).
See [test scope](../tests/README.md) for limitations. Linux aarch64,
macOS, Windows and loading by individual agent products remain unqualified;
platform declarations are not cross-platform test evidence. The new helper
has not been live commissioned against HA.

PR #1's maintainer-approved merge/review exception applied only to its exact
revision. Static analysis and passing tests are not independent review.
