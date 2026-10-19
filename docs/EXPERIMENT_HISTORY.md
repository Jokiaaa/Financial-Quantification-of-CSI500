# Research development and experimental decisions

This is a thematic reconstruction of the supplied research archive. Version labels identify historical branches, not a guaranteed chronological sequence. Earlier notes sometimes call a different configuration “final”; those decisions are local to that experiment and are not silently relabeled as the current T40/D2 configuration.

The bundled evidence consists of 11 original research-note snapshots. They include narrative and conversation-derived analysis, so a written conclusion is evidence of the recorded research process, not independent confirmation of its numerical or causal claims. File hashes establish snapshot integrity. Experiment identifiers, configurations, and raw outputs remain the appropriate next level of evidence.

## Research map

| Stage | Question | Recorded experiment / decision | Evidence |
|---|---|---|---|
| Baseline evaluation | Does an early Alpha158/LightGBM strategy generalize? | V1 evaluation records marked degradation across 2021–2024 and recommends developing a new version rather than proceeding to live trading. | [E01](../research_archive/sources/baseline_evaluation.txt) |
| Recency weighting | How quickly should old observations lose influence? | Compared 252-, 378-, and 504-day half-lives. A 252-day candidate looked strongest in 2025H2 but deteriorated on other inspected periods. | [E02](../research_archive/sources/recency_half_life_comparison.txt) |
| Model configuration | Which weighted branch becomes the reference? | A later selection note records HL378/MW2e4 as the main configuration and MW3e4 as a defensive alternative. | [E03](../research_archive/sources/hl378_selection.txt) |
| Rolling versus static | Should downside features and a static model be retained? | Another branch favors semiannual rolling, excludes downside additions, and selects T45/D2 in that branch. This is historical context, not the current T40/D2 decision. | [E04](../research_archive/sources/rolling_model_decision.txt) |
| Feature ablation | Which additional feature groups matter? | Compared raw confirm features, a core subset, removing VWAP, and removing volume means. The note records different outcomes for the groups. | [E05](../research_archive/sources/feature_ablation.txt) |
| Information timing | Can model routing use the candidate features at decision time? | Identified retrospective best-model labels and post-period statistics; recorded restrictions and subsequent fixes. | [E06](../research_archive/sources/router_information_audit.txt) |
| Model handover | Do conservative guards improve relay predictions? | Compared current-only, full relay, and conservative relay on nine periods. Broad guards hurt strong periods; a narrower rule was explicitly labeled an in-sample hypothesis. | [E07](../research_archive/sources/relay_guard_experiment.md) |
| Failure diagnosis | Is weak performance due to the model, holdings, execution, or costs? | Developed a failure-aware router using shadow diagnosis, dry-run policy, and replay stages; later restricted eligible actions. | [E08](../research_archive/sources/failure_router_report.md) |
| Two-stage risk selection | Does a downside model improve the return model's candidates? | Tested retaining the leading candidates and reranking the remainder. The report records mixed early results and substantial deterioration in several later periods. | [E09](../research_archive/sources/downside_risk_experiment.md) |
| Portfolio health | Can lagged deterioration in a shadow baseline guide exits? | Compared market-state TopK rules and baseline-health exits. B3 was a promising historical candidate; broader market-state rules were rejected. | [E10](../research_archive/sources/portfolio_health_experiment.md) |
| Artifact preservation | Can a selected model be recovered later? | A May 28 freeze note documents YAMLs, local modules, prediction/MLflow artifacts, analysis outputs, and a file manifest in the external frozen package. | [E11](../research_archive/sources/freeze_description.txt) |
| Presented portfolio results | Does a narrow PCF overlay change the relay portfolio? | 23 paired delayed evaluation windows are extracted from report section 15; an overlapping 2026H1 row is separated. | [Results](../results/RESULTS.md) |

## Selected experimental lessons

### A single winning period did not settle the half-life

E02 reports 2025H2 net annualized excess of −9.17% for the original candidate, +6.28% for HL252, +4.63% for HL378, and −4.49% for HL504 at minimum weight `1e-4`. However, the same note later reports HL252 deteriorating on 2025H1 and 2026YTD. The useful research finding is the instability across periods, rather than the best single number. These historical development metrics use their own configurations and cannot be pooled with the section-15 window returns.

### Feature removal was investigated, not assumed beneficial

E05 records raw, core-only, no-VWAP, and no-volume variants. Its displayed annualized metric is 7.10%, 3.21%, 3.73%, and 7.52%, respectively. The excerpt does not fully establish a common period or execution manifest, so this comparison is presented as a documented ablation lead. It is not used as proof that removing volume features improves the released model. The released handler still includes both volume-mean features.

### More risk intervention sometimes damaged the signal

E07 reports that broad relay guards reduced results over its nine inspected periods. E09 records risk reranking worsening several later periods, including 2024H2–2026YTD. These branches demonstrate why a risk model's standalone score does not automatically justify overriding a return model's strongest candidates.

### Timing checks changed research decisions

E06 explicitly separates retrospective labels from online inputs and records follow-up corrections. E10 records that certain market-state rules were unattractive after enforcing T−1 information. These findings concern exploratory router and risk branches; they should not be described as proof that every released pipeline is either compromised or fully audited.

## Evidence integrity and scope

[The evidence manifest](../research_archive/manifest.json) records each original relative path, byte count, and SHA256. Snapshots are byte-preserving copies of selected research notes. The rest of the external archive—including model binaries, market datasets, personal documents, and unrelated materials—is not copied into this presentation.

```bash
python tools/import_research_archive.py --check
```

The archive supports a substantive history of experimentation. Repeated inspection of historical periods also makes these periods development evidence; a fresh prospective evaluation should be separately frozen and reported.
