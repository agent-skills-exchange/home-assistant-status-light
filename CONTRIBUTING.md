# Contributing

Keep this a standalone, optional Agent Skills package. Retain GPL-3.0-or-later
for original work and preserve licences/notices for any future third-party
material. Disclose agent assistance with `Assisted-by: Briar` where applicable.

Read SKILL.md and references/setup.md before changing control behaviour. Keep
runtime imports standard-library-only, the one-light/fixed-service boundary,
safe diagnostics, explicit dependencies and separation of instruction loading
from execution authority. No quiet automatic installers, polling or task hooks.

Run `python3 -m unittest discover -s tests -v` and the Exchange dependency/schema
checks. Material skill changes need static SkillSpector inspection before
activation. Keep actual candidate identity and findings; don't suppress unknown
findings or call static analysis independent review. Behavioural/credential
changes also retain risk-appropriate independent review and CI. Maintainers own
merges/releases. Do not publish private deployment data or real credentials.
