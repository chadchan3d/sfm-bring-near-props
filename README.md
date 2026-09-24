# SFM Bring Near: Props

SFM Bring Near: Props is a Source Filmmaker Animation Set utility for quickly arranging selected props or character models around a deliberately chosen model or scene camera.

The fixed model or camera stays in place. Bring Near moves only the captured model targets and preserves their orientation, scale, ordinary parent relationship, and qualified existing position animation.

## Stable release

The surviving stable release is **v1.0.1**.

This Git repository was created after the tool had already been developed and released. The initial GitHub import culminates in a commit whose tree exactly matches the surviving v1.0.1 payload before publication documentation is added; earlier T-series development stages are preserved as documented pre-Git history rather than reconstructed commits.

The authoritative surviving release archive is:

```text
SFM_Bring_Near_Props_v1_01.zip
```

SHA-256:

```text
2c598753595d6c15a8de8a6f043b86c98185b51df52841abdbe2a8ad0528716a
```

See [`docs/RELEASE_PROVENANCE.md`](docs/RELEASE_PROVENANCE.md).

## Installation

1. Download the v1.0.1 release ZIP.
2. Extract it into:

   ```text
   SourceFilmmaker\game\
   ```

3. Restart Source Filmmaker.

The release archive contains:

```text
README.txt
workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py
```

## Usage

1. In the Animation Set Editor, select the models you want to move.
2. Right-click the model or scene camera you want to use as the fixed point.
3. Run **Bring Near: Props**.
4. Choose a placement: **In Front**, **Behind**, **Left**, or **Right**.
5. Choose **Row** or **Grid** and its arrangement directions.
6. Set the distance from the fixed point and the spacing between models.
7. Reorder or remove captured models if needed.
8. Click **Bring Near**.

Press **Ctrl+Z** to undo a changed Apply.

The fixed point is established by the right-click context, not by the current selection. To change the fixed point, close Bring Near and invoke it again on the new model or camera.

## Row and Grid

**Row** distributes the captured models along one reference-relative axis.

**Grid** distributes them across two different reference-relative axes, producing a 2D grid plane. The available direction vocabulary is:

- Front / Back (X)
- Left / Right (Y)
- Up / Down (Z)

The shipped v1.0.1 script labels the two Grid controls **Across** and **Rows**. The `README.txt` shipped in the same archive uses the later wording **Columns** and **Rows**. A preserved post-release T156 candidate implements that wording change and removes one redundant Help line; it is retained under [`development/`](development/) and is not represented as the byte-identical v1.0.1 release source.

## Animation behavior

Static targets use the qualified root-position write path.

For supported multi-key position animation, Bring Near translates every existing position key by the same delta. This preserves the tested path shape instead of flattening the animation to one position. The final animated refresh path uses frame-aligned evaluation plus SFM's native application notification scope.

The strongest preserved animated qualification was performed at **24 fps**. Other frame rates were not formally qualified by the preserved test evidence.

## Safety behavior

Bring Near validates live document, shot, target identity, parent state, and supported root-position bindings before movement. Unsupported or ambiguous target relationships fail closed instead of being moved speculatively.

Successful changed targets share one native SFM Undo transaction. A no-op Apply creates no Undo entry.

## Compatibility

Bring Near targets Source Filmmaker's bundled Python 2.7.5 environment, PySide, and SFM Python bindings.

The repository's generic syntax/static checks are not substitutes for SFM runtime qualification.

## Repository contents

- `workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py` — byte-identical v1.0.1 release script.
- `README.txt` — byte-identical v1.0.1 release README.
- `development/BNP_T156_Columns_Rows_Grid_Labels_RC.py` — preserved post-release UI wording candidate; not the stable release payload.
- `LICENSE` — CC0 1.0 Universal legal text.
- `LICENSE_SCOPE.md` — scope of the CC0 dedication and exclusions.
- `docs/DEVELOPMENT_HISTORY.md` — public-safe pre-Git chronology.
- `docs/ENGINEERING_NOTES.md` — qualified implementation behavior and limits.
- `docs/RELEASE_PROVENANCE.md` — exact surviving release identity and known packaging discrepancy.
- `docs/RELEASE_CHECKLIST.md` — validation and publication checks.
- `tools/validate_release.py` — validates the surviving v1.0.1 archive against the tracked release payload.

## Development history

The project predates Git. Earlier development was tracked through T-series runtime checkpoints, cumulative ledgers, handoffs, logs, and release files.

No retrospective Git commits are manufactured from those artifacts.

See [`docs/DEVELOPMENT_HISTORY.md`](docs/DEVELOPMENT_HISTORY.md).

## Author

ChadChan3D  
https://ChadChan3D.com/assets/

## License

Material owned by ChadChan3D and within the author's authority to dedicate is released under **CC0 1.0 Universal**.

See [`LICENSE`](LICENSE) and [`LICENSE_SCOPE.md`](LICENSE_SCOPE.md).

Source Filmmaker and other third-party names, software, formats, APIs, and assets remain the property of their respective owners and are not relicensed by this repository.
