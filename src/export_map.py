from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"


def main():
    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")
    edges = pd.read_csv(PROCESSED / "core_edges.csv")

    assert nodes["hub"].is_unique
    assert not edges.duplicated(["source", "destination"]).any()

    nodes["lat"] = pd.to_numeric(nodes["lat"], errors="coerce")
    nodes["lon"] = pd.to_numeric(nodes["lon"], errors="coerce")

    located = (
        np.isfinite(nodes["lat"])
        & np.isfinite(nodes["lon"])
        & nodes["lat"].between(-90, 90)
        & nodes["lon"].between(-180, 180)
        & nodes["location_quality"].notna()
        & nodes["location_quality"].ne("unresolved")
    )

    columns = [
        "hub", "name", "state", "lat", "lon",
        "location_quality", "capacity_est",
    ]

    markers = nodes.loc[located, columns].copy()
    markers["map_notice"] = (
        "Approximate location; not a verified warehouse address"
    )

    unresolved = nodes.loc[~located, columns].copy()

    # Keep only lanes whose two endpoints have map markers.
    mapped_hubs = set(markers["hub"])
    drawable = (
        edges["source"].isin(mapped_hubs)
        & edges["destination"].isin(mapped_hubs)
    )

    lanes = edges.loc[drawable].copy()

    coordinates = markers.set_index("hub")[["lat", "lon"]]

    for endpoint in ["source", "destination"]:
        lanes[f"{endpoint}_lat"] = lanes[endpoint].map(
            coordinates["lat"]
        )
        lanes[f"{endpoint}_lon"] = lanes[endpoint].map(
            coordinates["lon"]
        )

    lanes["map_notice"] = (
        "Network connection; straight line is not a road route"
    )

    markers.to_csv(PROCESSED / "map_hubs.csv", index=False)
    lanes.to_csv(PROCESSED / "map_lanes.csv", index=False)
    unresolved.to_csv(
        PROCESSED / "map_unresolved_hubs.csv", index=False
    )

    print("Map markers:", len(markers))
    print("Unresolved hubs:", len(unresolved))
    print("Drawable lanes:", len(lanes))
    print("Lanes omitted for missing endpoints:", int((~drawable).sum()))
    print("\nSaved map_hubs.csv, map_lanes.csv, map_unresolved_hubs.csv")
    print("Research coordinates and weather files were not changed.")


if __name__ == "__main__":
    main()