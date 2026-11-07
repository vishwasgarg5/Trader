# Step 2 AMC acquisition and discovery safety addendum

This addendum supplements the approvals in issue #30. It is binding for Step 2 execution.

## Branch and review sequence

1. All corrected workflow/design changes are developed on a branch and submitted as a draft pull request. No corrected design is committed directly to `main`.
2. The Motilal acquisition workflow is `workflow_dispatch` only. It has no `push`, `pull_request`, schedule, or other automatic trigger.
3. The dispatch requires the full 40-character `approved_design_commit_sha`. The job refuses to proceed unless that SHA exactly equals the workflow run's `github.sha`, and checks out that exact SHA.
4. Do not merge to `main`, and do not dispatch acquisition, until a human other than the implementation agent has recorded the design review. The implementation agent may run a technical checklist/pre-check and report findings, but may not label it the formal design review or sign it off.
5. Merge only the reviewed design. The user or another designated human owns the formal design-review record. The independent evidence reviewer remains a separate person and is still required to close Step 2.

## Navi and Aditya Birla discovery-only work

No prior Navi or Aditya Birla browser diagnostics or acquisition workflow runs exist in the repository history inspected for this plan. The following official AMC archive pages are the discovery targets:

- Navi: https://navi.com/mutual-fund/downloads/portfolio/
- Aditya Birla Sun Life: https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio

The dedicated `AMC archive discovery only` workflow is `workflow_dispatch` only. Run it separately once for each AMC. These runs:

- load the official archive page;
- record visible selectors/controls and request/response URL and metadata;
- do not change selectors, click buttons or links, read response bodies, or download files;
- cancel and flag any unexpected browser download event;
- store a JSON discovery record as a GitHub Actions artifact.

**Classification:** a discovery-only run is not an acquisition attempt, consumes zero acquisition attempts, and does not count against the approved Motilal attempt cap. This is because it does not retrieve or persist portfolio source bytes. A failed discovery-only run also consumes zero acquisition attempts. If any file download is attempted unexpectedly, the run fails and the event is recorded; it still must not be reclassified as an acquisition attempt unless source bytes were actually acquired and persisted.

Discovery does not establish archive completeness or prove historical workbook availability. It is a prerequisite diagnostic only.

## Current gates

- Motilal corrected acquisition: not authorized until human design review is recorded after PR review.
- Navi and Aditya Birla: discovery-only diagnostics may run; no downloads.
- Independent evidence reviewer: still undesignated; blocks Step 2 closure, not the one approved Motilal run.
- Research hold: ACTIVE.
