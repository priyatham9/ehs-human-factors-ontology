# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog and this project uses semantic versioning.

## [Unreleased]

### Added
- `docs/story.html`: motion layer on story engine 2.0 (GSAP 3.15 from cdnjs): cinematic hero, word-mask headline reveals, a new pinned "argument in five beats" chapter (problem, evidence, method, finding, so what) whose connector rail draws as you scroll and whose counts (4, 31, 89, 31 of 80) roll from the walkthrough and crosswalk data, a pinned "what this does not establish" chapter, spring hover and press; in-page links to a pinned chapter land at its end
- `docs/crosswalk.html`: GSAP motion layer: masked headline reveal, match-strength tiles flip up with counters, a pinned "Four frameworks, four different fits" chapter where each framework's bar fills in turn, the heat grid settles in from its centre, filters slide the remaining rows with Flip, the cell detail rises into place
- `docs/walkthrough.html`: a pinned "Four conditions, six stages, one band" chain whose connector draws as you scroll (each stage links to that stage in the tool), tiles settle in from the centre, showing or hiding the 16 nominal factors uses Flip, and each rule card slides in from the direction you stepped
- Reduced motion (OS setting or `?reduced=1`), print and missing GSAP all show the final static state; phones get one-shot reveals instead of pins

### Fixed
- `docs/walkthrough.html`: a stray `<!doctype html>` sat after the site header in the body
- `docs/crosswalk.html`: an em dash in the lede replaced with a colon

## [0.1.0] - 2026-09-09

### Added
- OWL/Turtle ontology (867 lines) encoding IDHEAS-G's four-context PIF structure: task, system, operational, and human contexts with 20 performance-influencing factors
- Reified alignments with explicit match strengths and citations mapping factors to SPAR-H, CREAM, HFACS, and HSE PIF list frameworks (78 external factors, 90 correspondences)
- Stratified Datalog rule engine with bottom-up evaluation, no function symbols, and derivation traces showing every derived fact linked to scenario inputs and cited literature
- Crosswalk (Markdown and CSV) generated from ontology with enforcement that the published version matches the source, preventing silent drift
- Synthetic scenario corpus (fabricated, labelled) and worked example (reactor startup nonroutine) exercising the engine with full trace output
- Macrocognitive function assignments for each PIF (detection, understanding, decisionmaking, action execution, interteam coordination) with function-specific evaluation rules
