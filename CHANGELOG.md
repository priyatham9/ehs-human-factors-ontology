# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog and this project uses semantic versioning.

## [Unreleased]

### Added
- `docs/crosswalk.html`: legend doubles as a strength filter, a coverage-by-framework bar chart counted from the grid, and a floating detail tip that is not clipped by the scrolling grid and closes on Escape
- `docs/walkthrough.html`: factor tiles jump to the first rule firing that uses them and show how many firings consume them, a step scrubber, and `#step=N` deep links
- `docs/story.html`: derivation edges draw from premise to conclusion as each stratum lights up

### Fixed
- `docs/walkthrough.html`: the site header sat before `<!doctype html>` (quirks mode) and the page had no `<body>`; arrow keys fired inside the site menu and with modifier keys; the "latest fact" highlight marked the newest list item even when the step re-derived an older fact; Play at the last step did nothing
- `docs/walkthrough.html`: title now names the repository

## [0.1.0] - 2026-09-09

### Added
- OWL/Turtle ontology (867 lines) encoding IDHEAS-G's four-context PIF structure: task, system, operational, and human contexts with 20 performance-influencing factors
- Reified alignments with explicit match strengths and citations mapping factors to SPAR-H, CREAM, HFACS, and HSE PIF list frameworks (78 external factors, 90 correspondences)
- Stratified Datalog rule engine with bottom-up evaluation, no function symbols, and derivation traces showing every derived fact linked to scenario inputs and cited literature
- Crosswalk (Markdown and CSV) generated from ontology with enforcement that the published version matches the source, preventing silent drift
- Synthetic scenario corpus (fabricated, labelled) and worked example (reactor startup nonroutine) exercising the engine with full trace output
- Macrocognitive function assignments for each PIF (detection, understanding, decisionmaking, action execution, interteam coordination) with function-specific evaluation rules
