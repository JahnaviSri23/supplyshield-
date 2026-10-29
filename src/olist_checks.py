from pathlib import Path

import pandas as pd


def late_summary(data):
    results = {"usable_orders": len(data)}

    for days in [0, 3, 7, 14]:
        # Compare exact timestamp differences.
        late = data["delay"] > pd.Timedelta(days=days)

        results[f"late_over_{days}d_count"] = int(late.sum())
        results[f"late_over_{days}d_pct"] = (
            100 * late.mean() if len(data) else float("nan")
        )

    return results


def main():
    root = Path(__file__).resolve().parents[1]
    raw = root / "data" / "raw"
    processed = root / "data" / "processed"

    orders = pd.read_csv(raw / "olist_orders_dataset.csv")
    customers = pd.read_csv(
        raw / "olist_customers_dataset.csv",
        usecols=["customer_id", "customer_state"]
    )

    print("Original orders:", len(orders))

    date_columns = [
        "order_delivered_customer_date",
        "order_estimated_delivery_date"
    ]

    for column in date_columns:
        orders[column] = pd.to_datetime(
            orders[column], errors="coerce"
        )

    usable = orders.dropna(subset=date_columns).copy()

    print("Orders excluded for missing/invalid dates:",
          len(orders) - len(usable))

    usable["delay"] = (
        usable["order_delivered_customer_date"]
        - usable["order_estimated_delivery_date"]
    )

    # Attach the customer's state without multiplying order rows.
    usable = usable.merge(
        customers,
        on="customer_id",
        how="left",
        validate="many_to_one"
    )

    print("Usable orders:", len(usable))
    print("Orders missing customer state:",
          usable["customer_state"].isna().sum())

    overall = pd.DataFrame([late_summary(usable)])

    state_results = []

    for state, group in usable.groupby(
        "customer_state", dropna=False
    ):
        result = {"customer_state": state}
        result.update(late_summary(group))
        state_results.append(result)

    by_state = pd.DataFrame(state_results).sort_values(
        "late_over_0d_pct",
        ascending=False
    )

    overall.to_csv(
        processed / "olist_late_overall.csv",
        index=False
    )
    by_state.to_csv(
        processed / "olist_late_by_state.csv",
        index=False
    )

    print("\nOVERALL LATE-DELIVERY RESULTS")
    print(overall.round(2).to_string(index=False))

    print("\nRESULTS BY CUSTOMER STATE")
    print(by_state.round(2).to_string(index=False))

    print("\nSaved: olist_late_overall.csv")
    print("Saved: olist_late_by_state.csv")


if __name__ == "__main__":
    main()