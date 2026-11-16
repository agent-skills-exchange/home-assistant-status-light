# Test scope

Run `python3 -m unittest discover -s tests -v` from the package root. Fixtures
are synthetic; no test contacts HA, flashes hardware or reads real credentials.
They exercise target confinement, fixed service bodies, safe error handling,
quiet hours, brightness bounds, snapshot/restore, interrupted cleanup,
manual-override detection and ambiguous writes.

Local evidence is reported with the candidate's actual test results. Linux
Python tests do not establish Claude/Cursor/Codex loading or macOS/Windows
behaviour. New helper live commissioning remains separate from previously
verified HA/ESPHome infrastructure. Hosted CI and independent review are separate
release gates; do not relabel local tests or SkillSpector as those gates.

Initial author validation: Linux x86_64, Python3.14.4,26 passing synthetic unit
tests; Agent Skills reference validation and Exchange dependency validation pass.
Static SkillSpector passes with score10/LOW and zero suppressions. Its remaining
generic permissions warning is covered by the explicit companion manifest rather
than a non-standard top-level SKILL.md field. Two LOW scope-wording matches occur
in the unmodified GPL licence text, not executable instructions. The initial
HIGH match was a rejected credential-file URL fixture; that fixture now uses a
harmless synthetic file URL while retaining invalid-scheme coverage. No baseline
was generated. These are author observations, not independent review approval.

Hosted validation of the initial implementation: [Actions run 43875730256](https://github.com/agent-skills-exchange/home-assistant-status-light/actions/runs/43875730256)
passed all 26 tests on Ubuntu 24.04 x86_64 with Python 3.11 and 3.14.
PR #1 was merged with a maintainer-approved exact-revision exception to pending
independent review; no independent review pass is claimed. That exception does
not waive review for subsequent changes. Platform declarations remain broader
than the tested Linux x86_64/Python matrix.

## Automated package checks

CI installs hash-pinned development dependencies from `requirements-ci.txt`
in a separate package-validation job, then runs `scripts/validate_package.py`
and its negative-fixture tests. These use the official Python `skills-ref`
source, not the same-name npm command used for an earlier local check. The
official validator also passes on the current package. The helper itself has
no new runtime dependencies. Without development dependencies, the additional
package tests skip explicitly; the original 26 runtime tests still run.

The bundled draft Exchange schema checks structure; additional tests reject
unknown feature/platform references, duplicate IDs/JSON keys, missing files,
escaping local references, broken inline Markdown file links and changed
lockfile digests. External URLs and Markdown anchors are not checked.
