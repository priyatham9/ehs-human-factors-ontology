# Crosswalk: local factors to established PSF/PIF frameworks

**This file is generated.** It is rendered from `ontology/ehs-hfo.ttl` by
`tools/build_crosswalk.py`. Edit the Turtle, not this file; `tests/test_crosswalk.py`
fails if the two disagree.

Every row states a correspondence that already exists in the published
literature. The purpose of the table is to make it hard to mistake this
vocabulary for a new taxonomy. It is not one. The four context dimensions are
the four PIF context categories of IDHEAS-G (NUREG-2198), and the twenty
factors are IDHEAS-G's twenty PIFs, adopted unchanged.

## How to read a cell

A cell names the counterpart factor in that framework and, in italics, how
close the correspondence is. Strengths are **analyst judgements made against
transcribed source wording**, not measured agreement. Nobody has adjudicated
them but the author, and there is no inter-rater reliability figure to quote.

- **exact** - Same construct, same scope, wording effectively identical.
- **close** - Same construct; wording or scope differs in ways unlikely to change an assessment.
- **broader** - The external factor subsumes the local factor along with other content.
- **narrower** - The external factor covers only part of the local factor.
- **partial** - Overlapping but non-nested constructs; the correspondence is interpretive.

`**no counterpart**` is an assertion, not a blank. It says the framework has
no factor corresponding to this one, and it is recorded so that it can be
argued with.

IDHEAS-G has no column. It binds to the four dimensions as whole categories
rather than factor by factor; those bindings are listed per dimension below.

## Factor tables

### Task context

Renames the IDHEAS-G context category **Task** (`xw:idheas-Task`).

Characteristics of the task being performed and of the information it requires.

| Factor (this ontology) | SPAR-H | CREAM CPC | HFACS | HSE PIF |
| --- | --- | --- | --- | --- |
| **Information availability and reliability** | Ergonomics and human-machine interface _(partial)_ | Adequacy of MMI and operational support _(partial)_ | Technological environment _(partial)_ | Clarity of signs, signals, instructions and other information _(close)_ |
| **Mental fatigue** | Fitness for duty _(broader)_ | Time of day (circadian rhythm) _(partial)_ | Adverse mental states _(close)_; Adverse physiological states _(partial)_ | Fatigue _(close)_ |
| **Multitasking, interruptions and distractions** | Complexity _(partial)_ | Number of simultaneous goals _(close)_ | Adverse mental states _(partial)_ | Divided attention _(close)_ |
| **Physical demands** | Fitness for duty _(partial)_ | Working conditions _(partial)_ | Adverse physiological states _(partial)_; Physical/mental limitations _(close)_ | Physical capability and condition _(close)_; Work overload/underload _(partial)_ |
| **Scenario familiarity** | Experience and training _(partial)_ | Adequacy of training and experience _(partial)_ | **no counterpart** | Routine or unusual _(close)_ |
| **Task complexity** | Complexity _(close)_ | Number of simultaneous goals _(partial)_ | Planned inappropriate operations _(partial)_ | Difficulty/complexity of task _(close)_ |
| **Time pressure and stress** | Available time _(close)_; Stress and stressors _(close)_ | Available time _(close)_ | Adverse mental states _(partial)_ | Stress/morale _(close)_; Time available/required _(close)_; Work pressures _(partial)_ |

### Operational context

Renames the IDHEAS-G context category **Environment and situation** (`xw:idheas-EnvironmentAndSituation`).

Physical conditions of the place where the work occurs.

| Factor (this ontology) | SPAR-H | CREAM CPC | HFACS | HSE PIF |
| --- | --- | --- | --- | --- |
| **Noise and communication pathways** | **no counterpart** | Crew collaboration quality _(partial)_; Working conditions _(broader)_ | Physical environment _(broader)_ | Communication (job) _(partial)_; Working environment _(broader)_ |
| **Resistance to physical movement** | **no counterpart** | Working conditions _(broader)_ | Physical environment _(broader)_ | Working environment _(broader)_ |
| **Thermal conditions** | **no counterpart** | Working conditions _(broader)_ | Physical environment _(broader)_ | Working environment _(broader)_ |
| **Workplace accessibility and habitability** | **no counterpart** | Working conditions _(broader)_ | Physical environment _(broader)_ | Working environment _(broader)_ |
| **Workplace visibility** | **no counterpart** | Working conditions _(broader)_ | Physical environment _(broader)_ | Working environment _(broader)_ |

### Human context

Renames the IDHEAS-G context category **Personnel** (`xw:idheas-Personnel`).

Attributes of the people, teams and organisational processes performing the work.

| Factor (this ontology) | SPAR-H | CREAM CPC | HFACS | HSE PIF |
| --- | --- | --- | --- | --- |
| **Procedures, guidance and instructions** | Procedures _(close)_ | Availability of procedures and plans _(close)_ | Operational process _(broader)_ | Preparation for task _(partial)_; Procedures inadequate or inappropriate _(close)_ |
| **Staffing** | Work processes _(partial)_ | Adequacy of organisation _(broader)_ | Resource management _(close)_ | Manning levels _(close)_ |
| **Team and organisation factors** | Work processes _(partial)_ | Adequacy of organisation _(close)_; Crew collaboration quality _(close)_ | Crew resource management _(close)_; Organizational climate _(partial)_ | Clarity of roles and responsibilities _(partial)_; Communication (organisation) _(partial)_; Level and nature of supervision/leadership _(partial)_; Organisational or safety culture _(partial)_ |
| **Training** | Experience and training _(close)_ | Adequacy of training and experience _(close)_ | Inadequate supervision _(partial)_; Resource management _(partial)_ | Competence _(close)_ |
| **Work processes** | Work processes _(close)_ | Adequacy of organisation _(broader)_ | Operational process _(close)_ | Consequences of failure to follow rules/procedures _(partial)_; Work pressures _(partial)_ |

### System context

Renames the IDHEAS-G context category **System** (`xw:idheas-System`).

Attributes of the plant, equipment, tools and interfaces the work is performed through.

| Factor (this ontology) | SPAR-H | CREAM CPC | HFACS | HSE PIF |
| --- | --- | --- | --- | --- |
| **Equipment and tools** | Ergonomics and human-machine interface _(partial)_ | Adequacy of MMI and operational support _(partial)_ | Technological environment _(broader)_ | Tools appropriate for task _(close)_ |
| **Human-system interface** | Ergonomics and human-machine interface _(close)_ | Adequacy of MMI and operational support _(close)_ | Technological environment _(close)_ | System/equipment interface _(close)_ |
| **System transparency to personnel** | Ergonomics and human-machine interface _(broader)_ | Adequacy of MMI and operational support _(broader)_ | Technological environment _(broader)_ | Clarity of signs, signals, instructions and other information _(close)_ |

## Notes on individual rows

Rows where the correspondence needed qualifying. These are the places a
reviewer is most likely to disagree, which is why they are listed rather
than buried in the Turtle.

- **Equipment and tools → Ergonomics and human-machine interface** (partial) - SPAR-H has no tools-and-parts PSF; the correspondence is to the ergonomics PSF only in so far as tools form part of the interface.
- **Mental fatigue → Time of day (circadian rhythm)** (partial) - CREAM's circadian CPC is the only explicit time-of-day factor in any of the five frameworks, and it is not the same construct as mental fatigue.
- **Multitasking, interruptions and distractions → Adverse mental states** (partial) - HFACS lists distraction among adverse mental states, which conflates an environmental demand with an operator state.
- **Noise and communication pathways → Crew collaboration quality** (partial) - Only the communication-pathway half of the local factor overlaps.
- **Procedures, guidance and instructions → Operational process** (broader) - HFACS has no procedures category at the precondition level; the nearest home is the organisational-level operational process.
- **Scenario familiarity → Experience and training** (partial) - SPAR-H treats novelty as a property of the operator (experience) rather than of the scenario. The two are not the same construct.
- **Staffing → Resource management** (close) - Note the level shift: a precondition-level factor here maps to an organisational-level HFACS category.
- **Staffing → Work processes** (partial) - SPAR-H has no staffing PSF. Staffing adequacy falls inside its work-processes PSF only by implication.
- **Task complexity → Planned inappropriate operations** (partial) - Weak. HFACS has no task-complexity category; the nearest is a supervisory failure to match task to crew.
- **Team and organisation factors → Communication (organisation)** (partial) - One local factor absorbing four HSE organisation factors is a sign of coarseness, not of coverage.
- **Time pressure and stress → Stress and stressors** (close) - One IDHEAS-G factor spans two SPAR-H PSFs. Anyone porting SPAR-H multipliers across this boundary is double counting.
- **Training → Resource management** (partial) - Interpretive. HFACS distributes training deficiency across organisational resource management and supervisory failure rather than giving it a precondition category.
- **Work processes → Work processes** (close) - Identical label in both frameworks; IDHEAS-G took the term from SPAR-H.
- **Workplace accessibility and habitability → Working environment** (broader) - HSE bundles noise, heat, space, lighting and ventilation into one factor; IDHEAS-G splits them across four.

## Coverage gaps

External factors this ontology does not cover. Recorded explicitly, because a
crosswalk that lists only its successes is a sales document.

### Time of day (circadian rhythm) (CREAM)

No local factor represents time of day or circadian phase. IDHEAS-G has no such PIF either, so the gap is inherited rather than introduced. This is the gap that matters most for shift-based occupational settings, and closing it would require an exposure denominator by hour of shift that no public dataset currently supplies (Hanecke et al. 1998; Folkard and Tucker 2003).

Sources: `hollnagel1998`, `folkard2003`, `hanecke1998`

### Failed to correct problem (HFACS)

No local factor represents a supervisor's failure to correct a known deficiency.

Sources: `shappell2000`

### Personal readiness (HFACS)

No local factor represents personal readiness in the HFACS sense: an individual's off-duty preparation for work, including rest, diet and compliance with alcohol and self-medication rules. The gap is inherited rather than introduced. IDHEAS-G has no fitness-for-duty PIF, whereas SPAR-H does, and the twenty factors here are IDHEAS-G's twenty adopted unchanged. ehs:MentalFatigue is the nearest local factor and is deliberately not aligned to this one: fatigue is a state during the task, personal readiness is conduct before it, and one causes the other rather than being it.

Sources: `shappell2000`, `shappell2006`, `nureg2198`, `gertman2005`

### Supervisory violations (HFACS)

No local factor represents wilful supervisory disregard of rules.

Sources: `shappell2000`

### Motivation vs. other priorities (HSE Performance Influencing Factors)

No local factor represents motivation or competing priorities as an attribute of the individual.

Sources: `hse_pifs`

### Effectiveness of organisational learning (HSE Performance Influencing Factors)

No local factor represents the effectiveness of organisational learning.

Sources: `hse_pifs`

### Peer pressure (HSE Performance Influencing Factors)

No local factor represents peer pressure. Team and organisation factors is too coarse to stand in for it.

Sources: `hse_pifs`

## Deliberately not crosswalked

Entries in the external inventories that are outcomes, structural
containers or headings rather than context factors. Listed so the
completeness check in `tests/test_crosswalk.py` has something to check
against, and so their absence is not read as an oversight.

| External entry | Framework | Reason |
| --- | --- | --- |
| Condition of operators | HFACS | Structural container; its children are crosswalked individually. |
| Decision errors | HFACS | Corresponds to the mistake classes in section 6, not to a factor. |
| Environmental factors | HFACS | Structural container; its children are crosswalked individually. |
| Errors | HFACS | Outcome category, not context. |
| Exceptional violations | HFACS | See parent. |
| Organizational influences | HFACS | Structural container; its children are crosswalked individually. |
| Perceptual errors | HFACS | Outcome category, not context. |
| Personnel factors | HFACS | Structural container; its children are crosswalked individually. |
| Preconditions for unsafe acts | HFACS | Structural container; its children are crosswalked individually. |
| Routine violations | HFACS | See parent. |
| Skill-based errors | HFACS | Corresponds to ehs:SkillBasedSlipOrLapse, not to a factor. |
| Unsafe acts | HFACS | Unsafe acts are outcomes, not context. Modelled here as error modes (section 6), not as performance-influencing factors. |
| Unsafe supervision | HFACS | Structural container; its children are crosswalked individually. |
| Violations | HFACS | Violations are intentional deviations and are outside the error taxonomy this ontology encodes. |
| Job factors | HSE Performance Influencing Factors | Heading, not a factor. |
| Organisation factors | HSE Performance Influencing Factors | Heading, not a factor. |
| Person factors | HSE Performance Influencing Factors | Heading, not a factor. |
| Environment and situation | IDHEAS-G | Bound to a context dimension by ehs:correspondsToIdheasCategory, not by a factor-level alignment. |
| Personnel | IDHEAS-G | Bound to a context dimension by ehs:correspondsToIdheasCategory. |
| System | IDHEAS-G | Bound to a context dimension by ehs:correspondsToIdheasCategory. |
| Task | IDHEAS-G | Bound to a context dimension by ehs:correspondsToIdheasCategory. |

## Source documents

- **CREAM** - Hollnagel, E. (1998). Cognitive Reliability and Error Analysis Method (CREAM). Oxford: Elsevier Science. [`hollnagel1998`]
 - The nine CPC labels used here were transcribed from an open-access secondary source (Shirali et al. 2019, MethodsX) because the book text was not consulted directly. See ../docs/PROVENANCE.md.
- **HFACS** - Shappell, S.A. & Wiegmann, D.A. (2000). The Human Factors Analysis and Classification System--HFACS. DOT/FAA/AM-00/7. Revised taxonomy as figured in Shappell et al. (2006), DOT/FAA/AM-06/18. [`shappell2000`, `shappell2006`]
 - Two versions matter here. The 2000 report subdivides Preconditions into Substandard Conditions and Substandard Practices of Operators. The revised taxonomy figured in the 2006 report uses Environmental Factors, Condition of Operators and Personnel Factors. The crosswalk maps to the revised taxonomy and says so.
- **HSE Performance Influencing Factors** - Health and Safety Executive. Performance Influencing Factors (PIFs). HSE human factors guidance, https://www.hse.gov.uk/humanfactors/assets/docs/pifs.pdf [`hse_pifs`]
 - HSE states of its own list: 'NB. This list is not exhaustive'.
- **IDHEAS-G** - U.S. Nuclear Regulatory Commission (2021). The General Methodology of an Integrated Human Event Analysis System (IDHEAS-G). NUREG-2198. [`nureg2198`]
- **SPAR-H** - Gertman, D.I., Blackman, H.S., Marble, J.L., Byers, J.C. & Smith, C.L. (2005). The SPAR-H Human Reliability Analysis Method. NUREG/CR-6883, INL/EXT-05-00509. [`gertman2005`]

Full bibliography with verification status: `../CITATIONS.md`.
