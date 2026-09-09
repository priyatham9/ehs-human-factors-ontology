# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog and this project uses semantic versioning.

## [0.1.0] - 2026-09-09

### Added
- OWL/Turtle ontology (867 lines) encoding IDHEAS-G's four-context PIF structure: task, system, operational, and human contexts with 20 performance-influencing factors
- Reified alignments with explicit match strengths and citations mapping factors to SPAR-H, CREAM, HFACS, and HSE PIF list frameworks (78 external factors, 90 correspondences)
- Stratified Datalog rule engine with bottom-up evaluation, no function symbols, and derivation traces showing every derived fact linked to scenario inputs and cited literature
- Crosswalk (Markdown and CSV) generated from ontology with enforcement that the published version matches the source, preventing silent drift
- Synthetic scenario corpus (fabricated, labelled) and worked example (reactor startup nonroutine) exercising the engine with full trace output
- Macrocognitive function assignments for each PIF (detection, understanding, decisionmaking, action execution, interteam coordination) with function-specific evaluation rules
