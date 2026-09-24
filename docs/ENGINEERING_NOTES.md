# Engineering notes

These notes describe the qualified SFM Bring Near: Props architecture represented by the surviving v1.0.1 release and its preserved development evidence.

They do not define a general-purpose Source Filmmaker transform framework.

## Evidence classifications

This document uses three practical categories:

- **Observed** — directly established by preserved live SFM runtime evidence.
- **Production rule** — behavior implemented by the surviving release source in response to that evidence.
- **Limitation** — behavior outside the supported contract or not proven generally.

## Fixed point and captured group

**Production rule:** The right-click context establishes the fixed point through the current animation set. Selection does not establish the fixed point.

**Observed:** T151 showed that a valid right-clicked model can open the tool even when the broader SFM selection contains unresolved DAGs.

**Production rule:** Unresolved selected DAGs are ignored/logged rather than treated as fatal. Recognized selected model owners become movement candidates.

**Production rule:** The retained palette stores exact animation-set IDs. Display names are not movement authority.

**Production rule:** Re-running the same tool version while the palette is open can merge newly selected eligible models while preserving the fixed point.

## Reference-relative axes

The planner derives artist-facing axes from the fixed point's evaluated orientation.

In the release source:

```text
Front / Back (X) -> reference forward
Left / Right (Y) -> reference right
Up / Down (Z)    -> reference up
```

These are reference-relative directions, not unconditional global-world X/Y/Z directions.

**Production rule:** Placement direction and Row/Grid spread are computed from this reference-relative basis.

## Root-transform distance semantics

**Observed:** Later placement tests qualified literal user-facing distance and spacing values for the tested cases.

**Production rule:** The current planner treats `From model` / `From camera` and `Between models` as root-transform layout distances rather than bounds-to-bounds clearance values.

Row/Grid offsets are centered around the layout origin.

When the chosen spread itself points through the fixed point, the planner may shift the layout origin farther outward only enough to keep all target origins on the selected placement side. This can make the actual origin distance greater than the requested minimum while retaining the literal spacing offsets.

## Static position writer

**Production rule:** Supported constant/static root-position tracks use the existing position key and source position value, followed by the bound channel's `Operate()` call.

The writer does not use a general-purpose `sfm.Move`/`sfm.Rotate` cycle for Props production placement.

## Animated whole-track translation

The central animated rule is a rigid translation of the existing position track.

For a supported multi-key root-position track, production does the following:

1. read the bound channel's current local time;
2. frame-align that time with `TimeAtCurrentFrame(...)` using the project frame rate;
3. evaluate the position log at that aligned time;
4. compute `delta = desired_position - aligned_evaluated_position`;
5. add the same delta to every existing position key with indexed `SetKeyValue(...)`;
6. do not add, delete, or retime keys;
7. do not write the animated source `valuePosition` as a replacement for the keyed track;
8. call the bound position channel's `Operate()`; and
9. verify the resulting track and final evaluated/world state.

**Observed:** T134 preserved all 23 keys in the tested animated track with a uniform translation and final position residual of approximately `0.000002596` world units.

**Limitation:** The strongest preserved frame-alignment/notification qualification was at 24 fps. Other frame rates were not formally qualified by the preserved evidence.

## Native notification and viewport refresh

The development series established that correct internal animation state and correct viewport presentation are separate requirements.

**Observed:** T107 showed that `sfmApp.ProcessEvents()` alone was insufficient for immediate animated viewport propagation.

**Observed:** T108 showed that the bound position channel's `Operate()` could produce correct evaluated/destination/world state while the viewport remained visually stale.

**Observed:** T130 showed that `CAppNotifyScopeGuard(reason, 0)` crosses the native application notification boundary that makes the viewport consume the changed animated state. Its first arrangement was state-disqualified because the channel-local time aligned during the notified render pass.

**Observed:** T134 solved that mismatch by planning against the predicted frame-aligned time before mutation.

**Production rule:** Changed target writes occur inside one `CAppNotifyScopeGuard(..., 0)`, followed by native Undo completion and one normal `sfmApp.ProcessEvents()` pass.

Do not summarize this as “ProcessEvents fixes refresh.” The qualified behavior depends on the native notification scope plus the frame-aligned writer.

## Undo contract

**Observed:** T140 established two independent native Undo entries for two changed Applies.

**Observed:** T142 established one native Ctrl+Z restoring a mixed static + animated transaction.

**Production rule:** All changed targets in one Apply share one native SFM Undo transaction.

**Production rule:** A no-op Apply produces zero writes and zero Undo entries.

**Production rule:** A partial post-mutation failure stops the operation, cleans up the native scope when possible, and enters a recovery-required state rather than attempting an unqualified synthetic rollback.

## Mixed and multi-target behavior

**Observed:** T136 passed a two-animated-target notification transaction.

**Observed:** T141 passed one static plus one animated target in the same Apply.

**Observed:** T143 passed an unrestricted production-shaped group with four changed targets: three static and one animated.

These tests qualified the integrated batch architecture under the tested conditions; they do not establish that every arbitrary SFM model/rig relationship is supported.

## Relationship safety

**Production rule:** Target identity, live shot/document state, root-position binding, and relevant parent state are re-read before mutation.

**Production rule:** Unsupported or ambiguous model relationships are blocked before movement rather than guessed through.

**Production rule:** The fixed point may be an ordinary scene camera, but cameras are references only; Props does not move cameras or lights.

## Retained-palette lifecycle

The palette is modeless and retained across repeated Apply operations.

The qualified lifecycle includes:

- adding selected eligible models on a later invocation;
- removing captured models;
- reordering model rows without changing SFM selection;
- model rename presentation;
- deleted-target recovery;
- shot switch/return handling;
- document retirement;
- script reload/controller retirement; and
- shutdown/close safety.

Session-only UI settings include placement, Row/Grid mode, arrangement direction, and distance/spacing controls. Fixed-point identity and captured-model membership do not persist across a fresh palette session.

## Crash guardrails from failed experiments

Two negative findings are retained because they materially constrain future SFM tooling:

1. A broad `QApplication.allWidgets()` enumeration experiment caused a native SFM crash. Broad Qt widget enumeration is therefore excluded from this architecture.
2. Retained/delayed `sfm.SelectDag(...)` experiments hard-crashed SFM before the intended Undo step. The production architecture does not depend on delayed selection mutation.

Synthetic viewport clicks were used only as diagnostics during the refresh investigation and were rejected as a production solution.

## UI and list behavior

The qualified release baseline includes:

- compact main palette width of 366 px;
- model-name right elision with the full name available on hover;
- one through seven model rows shown without normal scrolling;
- eight or more models capped at seven visible rows and scrolled;
- per-row Up/Down order controls; and
- default `From` and `Between` values of 28 SFM units.

A short-screen safeguard may force earlier scrolling when necessary.

## Grid control history

The surviving v1.0.1 source is T154 and exposes **Across** plus **Rows** for Grid. Both controls choose distinct reference-relative axes; the second dropdown excludes the first axis.

The shipped `README.txt` uses the later terms **Columns** and **Rows**. The preserved T156 development candidate applies that UI wording but does not have a separate complete SFM runtime qualification log in the public evidence.

## Compatibility limits

- Source Filmmaker bundled Python 2.7.5 / PySide / SFM bindings are the target environment.
- The production animation writer was deeply qualified only for the observed root-position binding topology.
- Non-24-fps frame-aligned notification behavior remains formally unqualified in the preserved evidence.
- Unsupported parent, lock, constraint, or binding states may be refused rather than handled speculatively.
- Generic Python parsing/compilation outside SFM does not prove runtime compatibility.
