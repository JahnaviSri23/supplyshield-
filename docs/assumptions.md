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

## Geocoding and weather

- Accepted automatic matches require a unique normalised city-and-state match.
- Ambiguous matches are left unresolved rather than choosing the first result.
- Existing saved matches were preserved; not all were independently revalidated.
- The location snapshot includes explicitly labelled reviewed city proxies.
- Of 100 core hubs, 95 have approximate locations and five remain unresolved.
- Hub ID digits are not assumed to be validated postal codes.
- Weather source: Open-Meteo Historical Weather API, explicitly using ERA5.
- Weather dates: 12 September–7 October 2018.
- Daily boundaries use Asia/Kolkata.
- Source weather uses the journey departure date.
- Destination weather uses the journey arrival date.
- Weather represents approximate endpoints, not the full route.
- Missing coordinates or weather remain missing, never zero rainfall.
- Both-end weather coverage is 90.57% for training and 93.52% for later legs.
- Historical weather is retrospective information. Same-day totals and
  arrival-day weather must not be presented as forecasts available at departure.
- Dataset timestamps are provisionally treated as Indian local time;
  source timezone confirmation remains pending.
- Historical weather was joined successfully; the rain-delay association
  has not yet been tested.
- Weather documentation: https://open-meteo.com/en/docs/historical-weather-api

## Capacity status

Capacity estimation has not been run.
Any future estimate based on observed throughput is a simulator proxy,
not a measured physical warehouse capacity.
Its units, observation window, zero-day handling and excluded traffic
must be documented when implemented.

## Dispatch-capacity estimate

- Capacity and simulator demand use outgoing journey legs per hub per day.
- A journey leg is not an individual parcel.
- Observations cover 12–25 September 2018, including zero-departure days.
- Only frozen-core lanes and training trips are used.
- Departures outside this calendar window are excluded from capacity counts.
- legs_per_day_p95 uses the linearly interpolated 95th percentile.
- capacity_est is ceil(legs_per_day_p95), with no extra headroom.
- Zero estimates remain zero and require review before simulation.
- Estimates exclude external traffic and are not physical warehouse capacities.
- The short observation period and missing pre-dataset trips limit accuracy.
- Edge statistics use training-trip legs only.
- median_actual_time is in minutes.
- median_ratio and p90_ratio are dimensionless actual-time/OSRM-time ratios.
- distance_km is the median OSRM distance in kilometres.
- trips counts distinct training trips on each directed lane.
- C must confirm that the optimizer models outgoing-leg dispatch capacity.

### Destination-only core hubs

IND201007AAA, IND110095AAB and IND560064AAA have incoming lanes
but no outgoing lanes in the frozen core. Their estimated dispatch
capacity is zero because no outgoing departures were observed.

This does not imply zero physical warehouse capacity.
They may receive legs, but cannot forward them within the frozen graph.
Dispatch capacity must not be applied as a receiving-capacity constraint.
Receiving and storage capacities remain unestimated.

### Rain comparison finding

Training-only within-lane comparisons showed near-zero median differences
at rainfall thresholds of 1 and 5 mm. At 10 mm, the median travel-time-ratio
difference was +0.0594 across 54 lanes, with 62.96% showing an increase.
Requiring at least two dates per condition retained 44 lanes and a positive
median difference of +0.0468.

These descriptive results suggest a possible association under heavier
rainfall, but do not establish causation or statistical significance.
The lane sample changes with the rainfall threshold. Weather-based
capacity reductions or delay penalties have not been calibrated from
these results.
