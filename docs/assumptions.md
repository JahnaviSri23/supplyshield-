# SupplyShield assumptions

<!-- CORE_SELECTION_START -->

## Core network selection and location limitations

- Selection uses trip_creation_time and keeps whole trips together.
- Training starts 2018-09-12 and ends before 2018-09-26.
- Person B must use the same split for compatible evaluation.
- Lane eligibility: at least 3 distinct training trips.
- Core size was chosen from training-only comparisons.
- Traffic-based connected growth is a heuristic, not an optimal solution.
- Frozen core: 100 hubs and 292 directed lanes.
- Training legs retained: 5395 (30.53%).
- Later legs retained on frozen lanes: 2422 (27.86%).
- Later-period results do not influence the frozen selection.
- Locations available: 95; unresolved:
  5.
- Locations are city approximations, not verified warehouse coordinates.
- Reviewed city proxies and their evidence are preserved in
  config/hub_location_snapshot.csv.
- Postal validation remains incomplete.
- Unknown coordinates and weather remain missing, never zero rainfall.
- Endpoint weather does not measure weather along the entire route.
- Historical daily weather is retrospective, not a departure-time forecast.
- Capacity estimates, when added, are traffic proxies rather than measured
  physical warehouse capacities.

### Core journey-leg location coverage

  period  core_legs  both_ends_located  both_ends_located_pct
training       5395               4886                  90.57
   later       2422               2265                  93.52

<!-- CORE_SELECTION_END -->
