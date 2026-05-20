# Scenario-first Multidomain Smoke v2 Completion Audit（2026-05-20）

## Scope

- User correction: Grid2Op-only / 2-row adapter sanity check is not enough for smoke testing.
- Required smoke scope: all six domains, about 10 rows per domain.

## Completed

- Built `60` rows.
- Domain counts: `{"grid2op": 10, "citylearn": 10, "traffic": 10, "water": 10, "aiopslab": 10, "finrl": 10}`.
- Source tiers: `{"real_grid2op_pair_adapter": 2, "controlled_scenario_first_generator": 58}`.
- All domains meet minimum: `True`.
- Wrote JSONL, SFT JSONL, Chinese report with figures, and audit target path.

## Remaining Limitation

This is a cross-domain data-protocol smoke, not a complete real-simulator smoke. Only Grid2Op currently contributes real-adapter rows, and those rows are still just adapter sanity cases. Each domain still needs a real adapter/exporter path with around 10 natural QA rows.
