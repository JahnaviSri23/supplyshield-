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

### Baseline-relative disruption and rain analysis

Shared target definitions are implemented in src/targets.py.
Baselines are fitted on valid journeys created, departed and completed
within 12–25 September 2018. Each route-type × distance-bucket group
requires at least 30 training observations.

Excess is the travel-time ratio minus its training-group median.
A journey is disrupted when its ratio strictly exceeds the group's
training p90. Unsupported targets remain missing.

Among 5,005 eligible training core journeys with source weather,
the disrupted share was 6.59% for dry days, 7.84% for light-rain days
and 9.80% for days with at least 10 mm of rain. This descriptive
association does not establish causation or statistical significance.

The frozen core contains 100 hubs and 292 directed lanes. It covers
5,395 of 17,674 training legs (30.53%) and 2,422 of 8,695 later-period
legs (27.86%). These coverage counts differ from the rain-analysis
sample, which additionally requires completed training outcomes
and available source weather.

### Planned cascade simulation rule

The simulator advances one day at a time. New demand enters an
origin backlog, and traffic moves through hub queues along its
assigned route. Each hub dispatches at most its available daily
capacity, shared across all outgoing traffic; edge limits also
apply. A failed hub has reduced dispatch capacity for a specified
duration, after which its original capacity returns. Traffic that
cannot move stays queued rather than disappearing. Intermediate
hubs have finite storage buffers: when downstream storage is full
or the next hub is fully closed, traffic waits upstream, creating
back-pressure. Transit arrivals reserve downstream storage, and
traffic cannot traverse multiple edges within one daily step.
Destination arrivals complete delivery without consuming dispatch
capacity. Storage limits, failure durations, waiting costs and
unmet-demand penalties are explicit simulation assumptions, not
measured warehouse properties. Demand is measured in parcels for
C's toy graph and truck-leg units for the core graph.

### Initial core simulator validation

The simulator was tested on the frozen 100-hub, 292-lane core.
Daily demand is 5,357 training-window departures divided by
14 days, giving 382.6429 fractional truck-leg units per day.
Seven demand days generate 2,678.5 units.

Scenarios include no failure, a three-day full closure of
Gurgaon_Bilaspur_HB, and an equivalent closure of the degree-one
Delhi_Jhilmil_L hub. Failures begin on simulation day 2.
Dispatch capacity multipliers are 1.0, 1.2 and 1.5.
Storage buffers remain fixed across these tests.

Flow conservation and no-failure drainage passed at all multipliers.
All scenarios delivered their generated demand within the 60-day
horizon. Busy-hub failure added 22,462.29, 21,017.49 and 18,020.57
hour-equivalent cost units respectively; leaf-hub failure added
257.14 at each multiplier. Runtime was approximately 0.031–0.038
seconds per scenario on the tested laptop.

These are initial implementation checks, not empirical validation
of real disruption behaviour. Each edge currently takes one day.
Shortest-cost simulated routes can differ from observed routes,
while capacities are estimated from observed outgoing core legs.
Buffers, failure duration and cost penalties are assumed.
Recovery_days measures backlog-drain time after demand stops and
the failure ends, not additional delay attributable to the failure.
The core tests use plan=None; multi-commodity optimizer-plan
integration remains pending.
## Core exports: columns and training rules

Run `python -m src.estimate_capacities` after core selection.
Core selection can recreate the minimal edge file; this export
step restores the optimizer columns.

### core_edges.csv

| Column | Meaning |
|---|---|
| source, destination | Directed lane's hub identifiers |
| trips | Distinct training-trip count used for frozen lane membership; includes subsequent legs belonging to those trips |
| median_actual_time | Median actual travel time, in minutes, from eligible completed training legs |
| median_ratio | Median actual_time_min / osrm_time_min |
| p90_ratio | 90th percentile of that ratio, using linear interpolation |
| distance_km | Median OSRM route distance in kilometres; not straight-line distance |
| stats_legs | Number of valid completed training legs supporting these statistics |
| stats_cutoff_exclusive | Outcomes on or after this date are excluded |
| source_center, destination_center | Compatibility aliases for source and destination |
| leg_count, trip_count | Original frozen-core membership counts |

Travel statistics use trips created within 12–25 September 2018,
with departure and completion also within that window. Completion
must not precede departure. Actual time must be finite and nonnegative,
OSRM time finite and positive, and distance finite and nonnegative.
A lane without eligible observations retains missing statistics;
later-period outcomes are never substituted.