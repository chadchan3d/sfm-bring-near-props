# Release provenance

## Authoritative surviving release

The authoritative surviving release artifact supplied for publication preparation is:

```text
SFM_Bring_Near_Props_v1_01.zip
```

Archive size:

```text
40,157 bytes
```

SHA-256:

```text
2c598753595d6c15a8de8a6f043b86c98185b51df52841abdbe2a8ad0528716a
```

The ZIP has no archive comment and is not encrypted.

## Exact payload

The archive contains two files plus directory entries:

```text
README.txt
workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py
```

`README.txt`

- size: `3,687` bytes
- SHA-256: `030ba67e352059fb68c1e5fd4915f697b415f9a658c5b871af9c2853d2da8933`

`workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py`

- size: `192,833` bytes
- SHA-256: `f8f249920101f4fe17df2c773c15c0dad9ab962fa37fa65ba7368c15729a72c1`

The release Python source is byte-identical to the preserved development file `BNP_T154_Grid_Plane_Controls_RC.py`.

## ZIP metadata

The archive central directory records Windows/PKWARE file-time metadata. It contains no archive comment, per-entry comment, encrypted payload, personal username, or source directory.

The directory entries are:

```text
workshop/
workshop/scripts/
workshop/scripts/sfm/
workshop/scripts/sfm/animset/
```

## Known release presentation discrepancy

The archive preserves one real packaging discrepancy:

- the Python source presents Grid controls as **Across** and **Rows**;
- `README.txt` describes the same controls as **Columns** and **Rows**.

The later T156 development candidate changes the first UI label to **Columns** and removes one redundant Help sentence. The discrepancy is documented rather than retroactively changing the v1.0.1 release bytes.

The release source also retains development-era internal identity strings:

```text
Version 1.0.0
1.0.0-rc50-grid-plane-controls
C:\Users\Public\Documents\BNP_T154_Grid_Plane_Controls_RC.log
```

These are release-hygiene inconsistencies, not privacy findings. `C:\Users\Public\...` is the standard shared Windows profile and does not expose the developer's account name.

## Privacy review of exact archive

The exact archive bytes, entry names, README, and Python source were reviewed for the standing publication blockers.

No prohibited personal/work identity association or personal machine account path was detected within the audited release artifact.

The public author identity present in the release content is ChadChan3D.

The review also checked for common credential/private-key/token patterns. No finding was detected within the audited archive scope.

This is a bounded audit result, not a claim that any scanner can guarantee the absence of every possible secret.

## Git relationship

This project predates Git.

The initial GitHub import uses a short connector-created sequence and culminates in commit `6f9696f58a6242e6aa6dcf75d139d059ecc72304`, whose tree exactly matches the two surviving release payload files. It does not invent commits for earlier T-series development.

Repository documentation, license material, validation tooling, and selected sanitized development material belong to ordinary publication commits after that exact-payload import point.

The `v1.0.1` tag should target commit `6f9696f58a6242e6aa6dcf75d139d059ecc72304`, not a later documentation commit.

## Release validator

Run:

```text
python tools/validate_release.py path/to/SFM_Bring_Near_Props_v1_01.zip
```

The validator checks archive identity, safe member paths, exact payload file list, member sizes/hashes, and byte equality against the tracked v1.0.1 release payload.
