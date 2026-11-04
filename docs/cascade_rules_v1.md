# SupplyShield: Cascade Simulator Rules & Specification (v1)

## 1. Core Rules (Motter-Lai Style Load Redistribution)
1. **Hub Representation:** Every hub has a defined **capacity** and current **load**.
2. **Initial Disruption:** A scenario initializes by failing one or more target hubs (`check_initial=True` safeguards against invalid starting states where load exceeds tolerance × capacity).
3. **Load Redistribution:** A failed hub distributes its accumulated load to its **alive neighbors** in direct proportion to their **spare room** (capacity minus current load). If all neighboring hubs are at or over capacity, the load is shared in proportion to their total capacities.
4. **Failure Criterion:** A hub fails if its updated load exceeds `tolerance * capacity` (where tolerance represents the resilience threshold, e.g., `1.0` or `1.1`).
5. **Iterative Rounds:** The process repeats in discrete rounds until no new hubs fail or `max_rounds` is reached.
6. **Unserved Load:** Any load originating from a failed hub that has no remaining alive neighbors to route through is classified as **unserved load**.

---

## 2. Definition of a Simulation "Round"
* A **round** represents a single discrete propagation step within a simulation day where all newly overloaded hubs simultaneously shed and redistribute their excess load to their local alive neighbors. 
* The cascade terminates when a round produces zero newly failed hubs (convergence) or reaches `max_rounds`.

---

## 3. Parameters
* **`tolerance`**: Default `1.0` (hubs fail immediately when load exceeds capacity; e.g., `1.1` allows a 10% overload buffer).
* **`max_rounds`**: Default `20` (maximum propagation steps for cascade evaluation).

---

## 4. Input & Output Formats
* **Inputs:** 
  * `capacity`: Dictionary mapping hub identifiers to numerical capacity values.
  * `load`: Dictionary mapping hub identifiers to baseline numerical load values.
  * `neighbors`: Adjacency list mapping each hub to its connected peers.
  * `initial_failed`: List of hub IDs targeted for initial failure.
* **Outputs:** 
  * `failed`: Sorted list of all hubs that failed during the cascade.
  * `n_failed`: Total count of failed hubs.
  * `n_rounds`: Total number of rounds taken for the cascade to settle.
  * `rounds`: Step-by-step audit trail of newly failed hubs and shifted loads per round.
  * `unserved_load`: Total load that could not be redistributed.
  * `unserved_share`: Ratio of unserved load to total network load.
  * `conserved`: Boolean verification flag ensuring total load equals unserved load plus alive load.

---

## 5. Modeling & Validation Summary
> Capacities and baseline loads are derived from daily core network traffic (`train_legs_v1.csv`). Unit-consistent validation (`single_failure_real_loads_v3.csv`) confirms that under real daily load profiles, the network is robust, resulting in **0 multi-hub cascades** once capacity-load boundary artifacts are reconciled.

## Two simulation modes
- `simulate_cascade` (structural stress test): hub graph with base loads; a failed hub's load is passed to
  alive neighbours in proportion to spare room; a hub fails when load > tolerance x capacity.
- `simulate_scenario` (plan evaluator, for the optimizer): evaluates a flow plan under a scenario
  (failed hubs with remaining capacity fraction, closed lanes). Excess at a hub is dropped; stranded parcels
  count as unmet; shipping is charged only for lanes actually travelled; optional `overload_factor` makes
  overloaded hubs fail in later rounds. Passes C's toy acceptance table (optimizer and do-nothing columns).

## Data alignment
- Load and capacity both use outgoing journey legs per hub per day on frozen-core lanes, 12-25 Sep 2018.
- Destination-only hubs (IND201007AAA, IND110095AAB, IND560064AAA) have zero dispatch capacity and zero load;
  they are treated as sinks that cannot absorb redistributed dispatch load.
- Superseded: single_failure_real_loads_v1/v2 and cascade_vs_centrality_v1 (inconsistent load definition,
  and a capacity-0 hub starting above capacity). v3 used a capacity workaround; v4 uses Person A's series.

## Split compatibility
- Person A's training window: trips created before 2018-09-26. Person B: train until 2018-09-24 13:19,
  calibration until 2018-09-28 22:36, test afterwards. B's test pile lies inside A's "later" period, so test
  results are compatible; B's calibration pile partly overlaps A's training period.