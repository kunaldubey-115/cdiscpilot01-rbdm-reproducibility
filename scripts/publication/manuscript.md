# Source-anchored reduction of clinical data-review rules: a paired, dual-track feasibility study using CDISCPILOT01

{{STATUS}}

Author: Kunal Dubey

Affiliation, corresponding-author contact details and ORCID: to be supplied by the author.

## Abstract

Background: Risk-proportionate clinical data review aims to concentrate effort on information important to participant protection and reliable trial conclusions. Fewer queries, however, do not by themselves demonstrate preservation of critical data or statistical results.

Objective: To evaluate whether a source-anchored reduction of executable validation predicates decreases review-query burden without additional critical-mutation misses or changes in selected regenerated statistical outputs relative to a specified comparator.

Methods: We designed a paired, source-level perturbation experiment using public CDISCPILOT01 pilot materials. A frozen 125-rule audit identified 48 fully executable comparator rules; the reduced plan retained 40, with shared structural and partial safety safeguards. Independent source-to-analysis rebuilds were evaluated in reference-replication and SAP-first sensitivity tracks. Two fixed-seed scenarios used disjoint perturbed-subject pools. Both pathways received identical dirty inputs and the same simulated record-verification correction procedure. Outcomes were deduplicated review episodes, critical-mutation record capture, and key-aligned statistical and summary-output differences against both the comparator and the track-specific clean reference.

{{ABSTRACT_RESULTS}}

Conclusions: The experiment evaluates a bounded efficiency-versus-preservation trade-off, not universal clinical safety or complete submission concordance. Identical pathway results must be interpreted alongside shared detection failures and clean-reference comparisons. Findings are descriptive and specific to the implemented rule set, source materials and perturbations.

Keywords: clinical data management; risk-based quality management; SDTM; ADaM; data review; reproducibility; simulation.

## 1. Introduction

ICH E6(R3) encourages proportionate, risk-based approaches and identification of factors critical to trial quality [1]. FDA monitoring guidance similarly emphasizes planning, communication and adaptation of monitoring activities [2]. Neither document establishes a numerical threshold for acceptable query reduction, nor does either validate removal of a particular data-management rule.

A practical difficulty is that validation catalogues mix checks serving different purposes: key integrity, clinical plausibility, population assignment, protocol compliance, statistical derivation and formatting consistency. Counting all flags together can obscure which protections are essential. Conversely, numerical agreement between two review plans can conceal errors shared by both.

We therefore operationalized a two-gate framework. Gate 1 links proposed rule suppression to documentary need, executable source fields and downstream dependencies, retaining unresolved protections rather than declaring them unnecessary. Gate 2 challenges the resulting plans at the source-data level, rebuilds analysis datasets independently, and compares both plans with a clean operational reference. The present study tests feasibility of this framework within available materials; it does not implement a complete eCTD validation system.

The initial ambition of majority-rule elimination with universal mathematical concordance was narrowed before the completed paired experiment because many checks required unavailable fields, external adjudication or unresolved specifications. We report the narrower question rather than treating those coverage gaps as successful validation.

## 2. Methods

### 2.1 Design, materials and operational reference

This was a retrospective computational feasibility experiment using cached public CDISCPILOT01 clinical test data and documentation, including SDTM and ADaM transport files, define.xml specifications, data guides, the annotated CRF named blankcrf.pdf and the cached clinical study report. CDISC provides the pilot repository and cautions that the data are supplied without guarantees of accuracy or completeness [3]. The injected perturbations were synthetic; this description does not assert that every underlying pilot observation is synthetic.

Existing cached source files were preserved. The clean operational reference means the unperturbed cached source processed by the selected reconstruction conventions; it does not mean clinically adjudicated error-free patient data. Cached ADaM targets were used for the clean reconstruction audit, not as values to insert into dirty-pathway rebuilds.

The reference gate covered ADSL, ADQSADAS, ADQSCIBC, ADQSNPIX, ADAE, ADTTE, ADLBC, ADLBH and ADVS. Eight dataset comparisons passed without the special waiver. ADQSCIBC retained a narrowly accepted SAP-aligned imputation-provenance exception involving 35 LOCF records and six provenance fields; all 730 compared scores agreed. The exception is not an exact nine-dataset replication claim or authentication of the original SAS programs.

### 2.2 Documentary conflicts and analysis tracks

Reference replication and SAP-first sensitivity were evaluated separately. Target-calibrated conventions were disclosed rather than represented as independent validation. Material conflicts included the NPI-X mean-period interpretation, vital-sign end-of-treatment timing and the representation of some missing laboratory categories. Reference compatibility used selected weeks 6, 8, 10 and 12 for the NPI mean despite a broader label, and vital records through Week 26 rather than the SAP-first Week 24 boundary. A category matching a reference value does not establish clinical normality when its underlying measurement is missing.

The two tracks share the same study and injected records. They are sensitivity analyses, not independent replications. Each pathway was compared with its own track-specific clean rebuild.

### 2.3 Gate 1: executable rule scope and suppression policy

Of 125 catalogue entries, 48 were executable as complete predicates, 38 were blocked by specifications, 29 by missing source fields, and 10 required non-XPT information or external review. Blocked and external checks remained explicitly unresolved. Partial checks were reported separately and were not counted as full execution of their parent rules.

DRP-B removed eight predicates from the 48-rule comparator: six contiguous-sequence-number checks, an exact vital-sign clock-time completeness check, and an uppercase-only SC-category check. Positive-integer and duplicate-sequence safeguards remained in both pathways. Both also used supported exposure-date ordering, SAP-based laboratory thresholds and vital-value/unit completeness components. Missing laboratory limits were unassessable, not normal. All catalogue Tier 1/2 protections were retained in policy, but retention did not make unavailable checks executable.

Eight of 22 executable entries originally labelled Tier 3 were removed (36.4%); the reduction across all executable entries was 16.7%. Thus this design did not eliminate a majority of executable Tier 3 rules. Original tier labels were not an independent clinical-risk adjudication. Suppression was predicate-specific, not permission to delete records, renumber identifiers, ignore clinically meaningful timing, or waive all metadata review.

Before completed challenge execution, adding clock times and changing SC-category case was tested across all nine rebuilt datasets in both tracks. All 18 dataset-level comparisons matched. These checks establish the tested computational dependency, not universal clinical harmlessness of metadata.

### 2.4 Policy lock and documented amendment

The final policy, source/template hashes, Python code hashes, seeds, correction procedure and tolerances were frozen before the completed paired runs. This was an internal computational lock, not public prospective preregistration. Reconstruction conventions had previously been calibrated against cached targets.

{{AMENDMENT}}

### 2.5 Perturbation scenarios

Development and held-out seeds were 20261120 and 20261121. Subject pools were partitioned by stable hash parity; all source records remained in the study, but perturbed subjects were disjoint between scenarios. Sampling was without replacement within each family and a source row could receive at most one mutation within its domain. A subject could receive mutations in different domains, so mutation observations were not assumed independent.

Nine families were designated critical: planned and actual arm codes, baseline ADAS item dates and scores, disposition codes and dates, AE onset relative to exposure, reversed exposure intervals, and marked hepatic laboratory abnormalities. Seven analytic metadata families addressed vital clock, location and position fields; historical medical-history date precision; selected routine OTC medication route and dose fields; and SC-category text. These scenario classifications do not establish that position, location or medication metadata are clinically harmless.

Development requested eight mutations per family and held-out requested twelve, limited by eligible source records. Examples of stronger or different held-out perturbations included blank rather than unrecognized planned-arm codes, missing rather than out-of-range baseline ADAS item scores, larger date shifts, and hepatic values at 15 rather than 8 times the upper reference limit. Exact eligibility, injection counts and mutation identities are retained in the supplementary audit.

### 2.6 Paired detection and correction

Each pathway received an independent copy of identical dirty inputs. Detectors did not receive the mutation truth ledger. A separate simulated verification step restored injected cells to their original source values only when the corresponding source record had been uniquely flagged. The same single-pass procedure applied to both pathways. Other cells were not corrected, and target ADaM values were never substituted.

Capture therefore means identification of the mutated source record for review, not proof that a particular rule diagnosed the altered field. An unrelated flag could trigger successful whole-record verification. Ambiguous or subject-level flags did not authorize automatic correction of a specific source row. This idealized verification procedure is an experimental oracle, not a validated model of human query resolution.

### 2.7 Outcomes and statistical outputs

Outcome A was the number of deduplicated review episodes, with query reduction defined as 100 × (queries in A − queries in B) / queries in A. Multiple flags on the same identifiable source record were consolidated. The reported injected-error query yield was captured mutated records divided by review episodes; it was not clinically adjudicated positive predictive value or measured staff time.

Outcome B was critical-mutation record capture. The missed mutation-ID sets were compared directly, separating shared misses from misses unique to either pathway. Equal counts alone were insufficient to establish identical detection.

Outcome C evaluated four population flags, statistical model summaries, time-to-dermatologic-event Kaplan–Meier summaries, and regenerated demographic, NPI, laboratory-shift and vital-sign summaries. For Week 24 records with EFFFL and ANL01FL set to Y, the ADAS model was change from baseline regressed on three-arm treatment, pooled site and baseline score. CIBIC+ used a three-arm treatment-plus-site ANOVA and a continuous-dose-plus-site trend model. Audited model outputs included observation counts, coefficients, standard errors and p-values. Kaplan–Meier outputs included arm counts, events and survival estimates at event times.

Comparisons were A versus clean, B versus clean and B versus A within each track. Tables were aligned by declared keys. Numeric tolerance was absolute 10^-8 plus relative 10^-10; strings were compared exactly, and paired missing values were treated as equal. Missing rows counted as differences across their columns; model failures were not evaluable rather than zero differences.

The frozen cell denominator includes serialized table identifier columns as well as value columns; it is not a count solely of independent numeric estimates. Mismatch percentage is not statistical variance. These summaries are not a certified reproduction of every submitted CSR shell.

### 2.8 Interpretation and reproducibility

The report distinguishes aims, data generation, methods and performance measures, following the organizational principles recommended for simulation studies [4]. It is not a large Monte Carlo experiment: there is one realization for each of two fixed-seed scenarios. We did not estimate a general error-rate distribution, conduct a formal non-inferiority test, or treat correlated mutations or analysis tracks as independent trials. No non-inferiority margin was prespecified.

The held-out scenario is internal to the same pilot dataset and reconstruction framework; it is not external validation. Historical estimate-stability and power simulations in the application were not counted as evidence from this paired experiment.

## 3. Results

{{RESULTS}}

### Table 1. Review-query burden

{{QUERY_TABLE}}

Reduction is relative to the specified 48-rule comparator and includes pre-existing flags on the source data. It is not a reduction in independently adjudicated clinical errors.

### Table 2. Critical-mutation capture and identity-level overlap

{{CAPTURE_TABLE}}

Shared misses and pathway-only misses refer to mutation IDs, not only aggregate counts. Fractions use the actual critical injections in each scenario as denominators.

### Table 3. Aggregate serialized-cell audit

{{OUTPUT_TABLE}}

Totals combine the seven audited summary categories within each scenario/track/comparison. Any failed category is shown separately and is not assigned zero mismatches. Full category-specific results and differing cells are in the supplementary workbook.

### Table 4. Shared missed critical-mutation families

{{MISSES_TABLE}}

These are deliberately introduced deviations from the operational source reference. An AE before exposure or an abnormal laboratory value can be clinically legitimate in real data; such values cannot automatically be declared errors without corroborating information.

{{FIGURE}}

### 3.1 Scope of the zero-mismatch finding

Outcome C covers ADSL population/completion flags, three efficacy models, ADTTE time-to-dermatologic-event summaries and five Gate 2 tables. Its 0 / 118,482 mismatches applies to each seven-category comparison (twelve repeated comparisons, not 118,482 pooled independent observations). In the implemented reconstruction, ADSL.COMP24FL uses the specified SV visit date and RFENDT, rather than the shifted DSSTDTC. ADTTE selects the first qualifying dermatologic event using AOCC01FL='Y'; changing arbitrary AE onset dates need not change that selected event or its aggregated Kaplan–Meier summaries. In these realizations the audited TTDE summaries remained unchanged. This observation does not estimate how frequently such changes would matter in other samples. The 15 development and 17 held-out shared critical misses therefore coexist with zero differences in the selected summaries; this is a limitation of Outcome C's coverage, not evidence of clinical harmlessness.

### 3.2 Attribution of query reduction and non-critical capture

Post-experiment descriptive tabulation of the saved flag ledgers shows that DRP-A-089 (VS.VSDTC missing HH:MM) uniquely accounted for 10,503 of 10,511 removed development episodes (99.924%) and 10,500 of 10,512 removed held-out episodes (99.886%). The six suppressed sequence-gap predicates (022, 051, 093, 104, 118, 125) fired zero times. DRP-A-122 (SCCAT uppercase) fired 8 and 12 times and accounts for the remaining removed episodes. Thus clock-time completeness dominated the 34.13%–34.14% query reduction, but its held-out contribution was slightly below 99.9%. Raw rule-089 flag totals (29,635 and 29,631) exceed uniquely removed episodes because other rules co-flagged many records.

Total mutated records captured were 87 versus 77 in development and 134 versus 119 in held-out. The 10- and 15-record differences were non-critical-designated perturbations: B captured no SCCAT mutations (0/8 and 0/12), while A captured all; B captured 6/8 and 9/12 VSPOS mutations versus A's 8/8 and 12/12. Both pathways captured 6/8 development and 7/12 held-out VSDTC clock perturbations incidentally through whole-record verification on records flagged by retained DRP-A-084/085 checks. Historical MH date and selected CM route/dose perturbations were uncaptured in both pathways (0/8 per family in development; 0/12 in held-out); no executable predicate in this study targeted those particular metadata perturbations. This is not a claim that all MH/CM rules were absent. These family-specific results were identical across the two tracks.

## 4. Discussion

### 4.1 Efficiency and preservation are separate claims

This framework makes the basis for removing a predicate inspectable and evaluates the resulting plan after source-level perturbation rather than merely editing already-derived analysis datasets. Any observed reduction in queries is informative about this implemented comparator. Its scientific importance depends on which protections were preserved, which critical mutations were missed, and whether outputs remained consistent with the clean operational reference.

Shared missed mutations are compatible with equal observed detection performance, but not with complete critical-error protection. Likewise, agreement between A and B can represent either successful preservation or identical contamination. The clean-reference comparisons are therefore essential. An unchanged primary model does not certify that an uncaptured safety-data mutation is harmless.

In particular, the RFENDT-based completion derivation and first-qualifying-dermatologic-event selection restrict which date errors can influence the audited outputs. These mechanisms explain why a narrow summary audit can miss changes to source information relevant to clinical interpretation. A broader safety review would need record-level and additional safety-output endpoints, rather than interpreting the observed zero cell mismatch as a universal safety result.

### 4.2 Comparator and query interpretation

Prior empirical work supports studying proportionate monitoring, but it does not directly validate this rule catalogue. ADAMON compared risk-adapted with extensive on-site monitoring in a cluster-randomized design using independent audits and a prespecified non-inferiority margin [5]. A Cochrane review reported moderate-certainty evidence for the risk-based versus extensive on-site comparison, while noting limitations in the number and precision of studies [6]. Those clinical monitoring outcomes differ from our simulated record-capture and computational-concordance endpoints. Their findings cannot supply a missing non-inferiority margin or external validation for the present experiment.

The comparator contains sequence-gap and formatting predicates whose clinical value may be limited. A reviewer should not interpret their removal as demonstrating superiority over every conventional DRP or a fully optimized industry comparator. Calibration of source-specific uniqueness checks does not resolve all clinical or operational choices in the catalogue.

Review episodes are an operational counting construct. A reduction in episodes need not translate proportionally into time saved, and the experiment did not measure query adjudication time, site burden, reviewer agreement, actual correction success or monetary cost. Whole-record oracle correction can make an incidental flag useful, exaggerating the diagnostic value of that flag compared with a real workflow.

The single-rule dominance is especially important: over 99.8% of removed episodes in each scenario came uniquely from the clock-time predicate (99.924% development; 99.886% held-out). The experiment consequently provides much stronger evidence about this particular clock-time requirement than about the collective value of a broad rule library. The zero-firing sequence-gap checks cannot establish empirical query savings here. Losing SCCAT and some unco-flagged VSPOS captures also illustrates that fewer queries entail deliberately reduced metadata review; incidental clock capture through retained checks should not be described as direct clock-error detection.

This distinction is consistent with the need to evaluate the utility of data-cleaning activities rather than count them indiscriminately. Sheetz and colleagues examined generalized source data verification using literature, trial data and audit findings [7]. Stokman and colleagues, including Bitzer, studied generalized query-based cleaning in 20 Phase III studies and distinguished direct and indirect data changes [8]. These studies motivate risk-based CDM and scrutiny of edit-check yield, but their observational findings do not validate our specific suppression policy or establish that any particular unqueried field is clinically harmless.

### 4.3 Reconstruction and documentary limitations

Target agreement is necessary for the selected reconstruction objective but insufficient to establish that the recovered algorithms are the original ones. Documentation conflicts can yield identical clean scores while responding differently to perturbations. The CIBIC+ provenance exception and the separate SAP-first track preserve this uncertainty rather than resolving it through numerical calibration alone.

The scope excludes 77 original catalogue entries from full execution. Missing-field, specification and external-adjudication gaps may explain some residual vulnerabilities and prevent conclusions about a complete clinical review system. Source annotations, protocol references and eCTD organization guide traceability; they do not by themselves validate a rule or certify an entire submission.

### 4.4 Generalizability and next validation steps

One public pilot dataset, selected perturbation families and two fixed seeds provide limited coverage of realistic error mechanisms, interactions and prevalence. Mutations may be correlated within subjects. Stronger evidence would require independently adjudicated criticality, source-verification realism, prospectively fixed acceptance margins where appropriate, and repeated evaluations across independent studies with new held-out perturbations.

Any remediation motivated by the present misses should be developed under a new versioned protocol and evaluated on genuinely new data or challenge sets. Retuning against the current held-out realization and then calling it untouched validation would overstate the evidence.

## 5. Conclusion

{{CONCLUSION}}

## Declarations and submission requirements

Ethics and data governance: This work uses public pilot materials and computational perturbations; no new participants were recruited by this analysis. The authors must confirm applicable institutional ethics requirements and should not assert an exemption without an appropriate determination.

Data-use permission: CDISC's published repository terms include restrictions on modifying the data and conditions concerning attribution and distribution [3]. The applicability of those terms to the perturbation experiments and planned sharing must be resolved by the authors, with permission obtained where needed, before submission or redistribution. This draft does not certify that permission has been obtained.

Data and code availability: Original materials are attributable to CDISC and other provenance sources documented in the frozen manifest. The local reproducibility record contains policy and source/code hashes, mutation audits, pathway hashes and output comparisons. A public archival location, license review and persistent identifier remain to be supplied; the local files are not represented as a public repository.

Funding, competing interests and author contributions: Author confirmation required. Do not infer absence of funding or conflicts from missing information.

AI assistance: AI assistance was used for software development and manuscript drafting. The human authors must verify the methods, results, citations and wording, accept responsibility for the work, and adapt this disclosure to the selected journal's policy.

Submission status: This is an author-review draft, not a statement of journal acceptance, regulatory endorsement or submission readiness. Author details, independent scientific review, data-use permissions, final result completeness and journal-specific formatting remain release requirements.

## References

1. International Council for Harmonisation. Guideline for Good Clinical Practice E6(R3). Principles and Annex 1 endorsed at Step 4 on 6 January 2025; consolidated guideline incorporating Annex 2 adopted 16 June 2026. https://database.ich.org/sites/default/files/ICH%20E6%28R3%29_Step4_FinalConsolidatedGuideline_2026_0616_.pdf

2. US Food and Drug Administration. A Risk-Based Approach to Monitoring of Clinical Investigations: Questions and Answers. Guidance for Industry. April 2023. https://www.fda.gov/regulatory-information/search-fda-guidance-documents/risk-based-approach-monitoring-clinical-investigations-questions-and-answers

3. Clinical Data Interchange Standards Consortium. SDTM/ADaM pilot project repository: clinical test data, documentation, disclaimer and terms of use. https://github.com/cdisc-org/sdtm-adam-pilot-project. Accessed 15 November 2026.

4. Morris TP, White IR, Crowther MJ. Using simulation studies to evaluate statistical methods. Statistics in Medicine. 2019;38(11):2074–2102. doi:10.1002/sim.8086.

5. Brosteanu O, Schwarz G, Houben P, et al. Risk-adapted monitoring is not inferior to extensive on-site monitoring: Results of the ADAMON cluster-randomised study. Clinical Trials. 2017;14(6):584–596. doi:10.1177/1740774517724165.

6. Klatte K, Pauli-Magnus C, Love SB, et al. Monitoring strategies for clinical intervention studies. Cochrane Database of Systematic Reviews. 2021;12:MR000051. doi:10.1002/14651858.MR000051.pub2.

7. Sheetz N, Wilson B, Benedict J, et al. Evaluating Source Data Verification as a Quality Control Measure in Clinical Trials. Therapeutic Innovation & Regulatory Science. 2014;48:671–680. doi:10.1177/2168479014554400.

8. Stokman PG, Ensign L, Langeneckhardt D, et al. Risk-based Quality Management in CDM: An inquiry into the value of generalized query-based data cleaning. Journal of the Society for Clinical Data Management. 2021;1(1). doi:10.47912/jscdm.20.

## Supplementary material

The accompanying results workbook contains the preserved Blueprint/CRF material, complete rule-scope audit, frozen policy and hashes, query and capture outcomes, identity-level miss comparisons, family-specific counts, category-specific output comparisons and cell differences. The publication snapshot identifies exactly which saved result file was used. No new clinical analyses are run to assemble this document.

