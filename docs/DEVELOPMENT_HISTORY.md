# Development history

SFM Bring Near: Props was developed and released before this Git repository existed.

This document preserves a public-safe chronology reconstructed from the surviving source, cumulative test ledger, handoff, runtime results, and release archive.

The T-series identifiers below:

- predate Git tracking;
- identify development or qualification checkpoints;
- are not Git commit numbers; and
- must not be interpreted as reconstructed commit history.

Git history begins only with the later audited repository import.

## Product direction

The project converged on a retained, nonmodal placement palette with a deliberately chosen fixed point and a captured group of moved model targets.

The final product contract is narrow:

- the right-clicked model or ordinary scene camera is the fixed point;
- other selected eligible model animation sets become the moved group;
- the fixed point does not move;
- Props does not move cameras or lights;
- placement is translation-only;
- model orientation, scale, and ordinary parent state are preserved;
- Row and Grid placement use literal user-facing distance and spacing values measured from root transforms;
- repeated Apply operations create independent native Undo entries;
- no-op Apply creates no Undo entry; and
- unsupported or ambiguous relationships fail closed.

## Early geometry and placement qualification

Early checkpoints established the reference-relative direction basis later retained by production:

- Front / Back follows the fixed point's artist-facing forward axis;
- Left / Right follows its artist-facing right axis; and
- Up / Down follows its up axis.

The planner evolved away from bounds-based spacing and toward literal root-transform distances. Later tests retained centered Row/Grid offsets and added only the minimum outward shift needed to keep target origins on the selected placement side.

## Retained palette, identity, and lifecycle

The middle development series established that movement authority belongs to the captured group rather than whatever happens to be selected at Apply time.

The retained palette was hardened for:

- adding selected models on a later invocation while keeping the fixed point;
- removing captured models from the group;
- exact animation-set identity rather than display names;
- model rename handling;
- deleted-target recovery;
- shot changes and return;
- document changes;
- script reload/controller retirement;
- quit/shutdown behavior; and
- partial-failure recovery.

A broad Qt widget enumeration experiment caused a native SFM crash and was permanently rejected. Delayed retained `sfm.SelectDag(...)` experiments also hard-crashed SFM and were removed from the architecture.

## T85-T95 — integrated production path

T85 began the integrated production candidate series.

Subsequent checkpoints exercised mixed static/animated targets, Undo/Redo, shot return, deleted-target recovery, partial-failure behavior, document retirement, quit/shutdown behavior, camera-reference distance handling, and final compact UI behavior.

T95 concluded with **PASS — final pre-release end-to-end regression** in the preserved ledger.

## T96-T103 — release and UI refinement

T96-T101 refined release presentation and compact-window terminology.

T102-T103 revisited spacing semantics, animated behavior, and large captured-model lists before the animation writer was redesigned more deeply.

## T104-T108 — whole-track animated translation

T104 introduced the central animated-position strategy: translate every existing root-position key by one uniform delta instead of collapsing the animation to one value.

T105 passed the literal-distance rule and the whole-track path at the tested current-key time.

T106 exposed a between-key failure in the then-current refresh path.

T107 showed that `sfmApp.ProcessEvents()` alone did not make the viewport consume the updated animated state.

T108 established that the bound position channel's `Operate()` call made the internal evaluated/destination/world state correct for the tested between-key target, while the viewport could still remain visually stale.

This separated animation-authoring correctness from viewport-presentation correctness.

## T109-T134 — native viewport refresh investigation

A long bounded refresh campaign tested timing, focus, Qt update, host activation, palette visibility, under-cursor viewport updates, viewport-child focus, and synthetic-click diagnostics.

Those approaches did not provide an acceptable production solution.

T130 was the breakthrough: wrapping the qualified mutation in `CAppNotifyScopeGuard(..., 0)` caused the viewport to update without a physical click. The first arrangement was **visual PASS / state disqualified**, because SFM aligned the channel-local time during event processing and the translated path had been computed against the pre-aligned time.

T131-T133 localized and characterized that timing behavior.

T134 computed the translation against `TimeAtCurrentFrame(...)` before mutation. The preserved 24 fps test then reached:

**FULL PASS — visual refresh + final state correct**.

The 23-key animated path remained a rigid translation; no key was added, deleted, or retimed; the global playhead did not drift.

## T135-T143 — repeatability, Undo, and group integration

The notification-based writer was then broadened deliberately:

- T135: repeated changed Apply operations — PASS;
- T136: two animated targets in one notified transaction — PASS;
- T140: two independent native Undo entries — PASS;
- T141: mixed static + animated Apply — PASS;
- T142: one native Undo restoring the mixed transaction — PASS; and
- T143: unrestricted four-target production-shaped group integration — FULL PASS.

The preserved T143 run contained three static targets and one animated target.

## T144-T150 — production cleanup

T144 qualified the production-cleanup candidate.

T145 exposed a presentation-only Help regression and was not accepted as the final visual source.

T146-T150 corrected Help footer/copy, added model ordering, added session-only UI state and alternating row bands, stabilized window sizing, and clarified that distance is measured from root transforms.

The resulting production source was built as `SFM_Bring_Near_Props.py` and later passed the preserved release-file functional smoke.

## T151-T153 — release hardening

T151 corrected selection capture after real use exposed an unresolved-selected-DAG launch failure.

The qualified rule became:

- `sfm.GetCurrentAnimationSet()` identifies the right-clicked fixed point independently of selection;
- unresolved selected DAGs are ignored and logged rather than treated as fatal; and
- valid selected model owners are still captured normally.

T151 passed.

T152 added right-side ellipsis for long model names and preserved full names on hover. The visual result passed, while revealing a list-height follow-up.

T153 changed list sizing to use actual row heights, showing one through seven rows without unnecessary scrolling and capping eight or more at seven visible rows. T153 passed.

The final 2026-09-16 production file incorporated T151-T153 and the previously qualified movement/Undo/lifecycle behavior.

## T154 — explicit Grid plane controls

On 2026-09-17, T154 restored an explicit second Grid direction control.

Row continued to expose one **Direction**. Grid exposed **Across** and **Rows**, each choosing among:

- Front / Back (X)
- Left / Right (Y)
- Up / Down (Z)

The secondary control excludes the axis already selected by the first control so the two dimensions form a 2D plane instead of collapsing onto one line.

The exact source in the surviving `SFM_Bring_Near_Props_v1_01.zip` is byte-identical to T154.

The cumulative ledger preserves T154's qualification plan, but not a separate completed T154 runtime-result section. The subsequent release/archive existence is production evidence that the candidate was packaged, but it is not substituted for a missing formal qualification log.

## T155-T156 — post-release wording refinement

T155 removed one redundant Help sentence that repeated the X/Y/Z axis names already shown by the controls.

T156 renamed Grid's first control from **Across** to **Columns**, retaining **Rows** for the second control.

The preserved T156 source differs from T154 only in diagnostic identity and this UI/Help wording. No separate complete SFM runtime qualification log for T156 is preserved in the publication evidence, so it remains a development candidate rather than being substituted silently for the stable release source.

## Surviving v1.0.1 archive

The surviving archive contains exactly two files:

```text
README.txt
workshop/scripts/sfm/animset/SFM_Bring_Near_Props.py
```

Its Python source is byte-identical to T154. Its `README.txt`, however, already describes the later **Columns / Rows** wording.

That discrepancy is preserved and documented rather than rewritten retroactively.

See [`RELEASE_PROVENANCE.md`](RELEASE_PROVENANCE.md).

## Evidence boundary

The private development evidence includes cumulative ledgers, handoffs, runtime logs, screenshots, and many intermediate probes.

The public repository intentionally does not publish that entire archive. This history records the durable conclusions, important failures, and evidence limitations without exposing private or redundant development material.
