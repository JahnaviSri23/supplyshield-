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
