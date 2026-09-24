# v1.0.1 publication checklist

## Repository history

- The initial GitHub import culminates in a commit whose tree contains only the exact surviving v1.0.1 payload.
- Earlier T-series work is documented as pre-Git history rather than manufactured as commits.
- The `v1.0.1` tag should target commit `6f9696f58a6242e6aa6dcf75d139d059ecc72304`, the first commit whose tree exactly matches the surviving v1.0.1 payload.
- Publication-preparation documentation is in later ordinary commits.
- No retrospective pre-Git development commits are manufactured.

## Release payload

Expected archive:

```text
SFM_Bring_Near_Props_v1_01.zip
```

Expected SHA-256:

```text
2c598753595d6c15a8de8a6f043b86c98185b51df52841abdbe2a8ad0528716a
```

Expected files:

```text
README.txt
workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py
```

- `tools/validate_release.py` reports PASS against the supplied archive.
- The tracked stable payload remains byte-identical to the archive.
- The T156 development candidate remains clearly separated from the stable payload.

## Static validation

- The stable release source parses successfully under the available modern Python parser where applicable.
- The T156 development candidate parses successfully under the available modern Python parser where applicable.
- Such parsing is recorded only as a static syntax check, not as proof of SFM/Python-2.7 runtime compatibility.

## Historical SFM runtime evidence

The preserved development evidence supports the release architecture documented in this repository, including:

- fixed-point / captured-target identity;
- literal root-transform layout semantics;
- qualified static position writes;
- whole-track animated translation;
- frame-aligned native notification refresh at 24 fps;
- repeated Apply behavior;
- native Undo;
- mixed static + animated batches;
- multi-target group integration;
- retained-palette lifecycle; and
- selection-capture hardening.

A missing formal T154 result section and missing separate T156 runtime log are explicitly documented rather than inferred away.

## Documentation and license

- `README.md` distinguishes stable release content from the later T156 candidate.
- `README.txt` remains byte-identical to the release ZIP.
- `LICENSE` contains the standard CC0 1.0 Universal legal text.
- `LICENSE_SCOPE.md` limits the dedication to owned/controlled material.
- Third-party software, names, APIs, formats, and assets are not represented as relicensed.
- `docs/DEVELOPMENT_HISTORY.md` clearly labels the T-series chronology as pre-Git.
- `docs/RELEASE_PROVENANCE.md` records exact release hashes and the Columns/Across discrepancy.

## Privacy and rights audit

For publication verification:

- scan every object reachable from the proposed public branch/tag;
- scan author/committer/tagger metadata and commit/tag messages;
- scan current tracked files and the exact release ZIP;
- confirm the public identity is only the approved ChadChan3D identity where project attribution is present;
- confirm prohibited unrelated work/nonprofit identifiers are absent;
- confirm personal machine account paths are absent;
- confirm no secret, token, private key, cookie, webhook credential, or authentication file is present;
- confirm raw private logs/screenshots/handoffs/ledgers are not tracked; and
- report scanner coverage as bounded rather than absolute.

## Knowledge transfer

- Generate the knowledge package outside the public repository.
- Include only sanitized summaries or selected public-safe evidence.
- Keep raw runtime logs/screenshots/private handoffs out of the transfer package.
- Validate strict JSON, candidate/evidence IDs, hashes, and relative paths in `handoff.json`.
- Record publication as complete only after the public branch, tag, release, and release asset are verified.

## External publication

Publication was explicitly approved before this repository was populated. Any later tag, release, release-asset, visibility, or deployment changes should remain limited to the approved SFM Bring Near: Props destination and verified release payload.
