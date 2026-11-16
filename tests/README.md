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
