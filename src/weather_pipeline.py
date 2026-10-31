"""Fetch historical weather and enrich the frozen core journey legs."""

from pathlib import Path
import time

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
CACHE = PROCESSED / "weather_cache_era5"

VARIABLES = ["rain_mm", "precipitation_mm", "temperature_mean_c"]
MODEL = "era5"
TIMEZONE = "Asia/Kolkata"


def atomic_csv(frame, path):
    temporary = path.with_suffix(".tmp")
    frame.to_csv(temporary, index=False)
    temporary.replace(path)


def valid_weather(table, hub, dates):
    required = {
        "hub", "date", "requested_latitude", "requested_longitude",
        "weather_model", "timezone", *VARIABLES
    }

    if not required.issubset(table.columns):
        return False

    return (
        len(table) == len(dates)
        and set(table["date"]) == dates
        and table["date"].is_unique
        and table["hub"].eq(hub.hub).all()
        and table["weather_model"].eq(MODEL).all()
        and table["timezone"].eq(TIMEZONE).all()
        and pd.to_numeric(
            table["requested_latitude"], errors="coerce"
        ).sub(hub.latitude).abs().lt(1e-8).all()
        and pd.to_numeric(
            table["requested_longitude"], errors="coerce"
        ).sub(hub.longitude).abs().lt(1e-8).all()
        and table[VARIABLES].apply(
            pd.to_numeric, errors="coerce"
        ).notna().all().all()
    )


def main():
    CACHE.mkdir(parents=True, exist_ok=True)

    nodes = pd.read_csv(PROCESSED / "core_nodes.csv")

    if not nodes["hub"].is_unique:
        raise ValueError("Duplicate core hub IDs.")

    for column in ["latitude", "longitude"]:
        nodes[column] = pd.to_numeric(nodes[column], errors="coerce")

    accepted = nodes["match"].isin(
        ["city+state", "reviewed_city_proxy"]
    )
    located = (
        accepted
        & nodes["latitude"].between(-90, 90)
        & nodes["longitude"].between(-180, 180)
    )

    weather_hubs = nodes.loc[
        located, ["hub", "latitude", "longitude"]
    ].copy()

    if weather_hubs.empty:
        raise ValueError("No core hubs have accepted coordinates.")

    train = pd.read_csv(PROCESSED / "core_train_legs.csv")
    later = pd.read_csv(PROCESSED / "core_later_legs.csv")
    train["split"] = "training"
    later["split"] = "later"

    legs = pd.concat([train, later], ignore_index=True)

    if legs.empty:
        raise ValueError("Core journey-leg tables are empty.")

    starts = pd.to_datetime(legs["od_start_time"], errors="raise")
    ends = pd.to_datetime(legs["od_end_time"], errors="raise")

    if starts.isna().any() or ends.isna().any():
        raise ValueError("Missing journey timestamps.")
    if (ends < starts).any():
        raise ValueError("A journey ends before it starts.")

    start_date = str(starts.min().date())
    end_date = str(ends.max().date())
    dates = set(
        pd.date_range(start_date, end_date).strftime("%Y-%m-%d")
    )

    weather_file = PROCESSED / "weather_daily.csv"
    existing = (
        pd.read_csv(weather_file, dtype={"date": str})
        if weather_file.exists()
        else pd.DataFrame()
    )

    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))

    tables = []
    failures = []
    reused = 0
    downloaded = 0

    try:
        for number, hub in enumerate(
            weather_hubs.itertuples(index=False), start=1
        ):
            cache_file = (
                CACHE / f"{hub.hub}_{start_date}_{end_date}.csv"
            )

            try:
                table = pd.DataFrame()

                if {"hub", "date"}.issubset(existing.columns):
                    table = existing.loc[
                        existing["hub"].eq(hub.hub)
                        & existing["date"].isin(dates)
                    ].copy()

                if not valid_weather(table, hub, dates):
                    table = pd.DataFrame()

                    if cache_file.exists():
                        try:
                            table = pd.read_csv(
                                cache_file, dtype={"date": str}
                            )
                        except (OSError, ValueError):
                            table = pd.DataFrame()

                if valid_weather(table, hub, dates):
                    reused += 1
                else:
                    response = session.get(
                        "https://archive-api.open-meteo.com/v1/archive",
                        params={
                            "latitude": hub.latitude,
                            "longitude": hub.longitude,
                            "start_date": start_date,
                            "end_date": end_date,
                            "daily": (
                                "rain_sum,precipitation_sum,"
                                "temperature_2m_mean"
                            ),
                            "timezone": TIMEZONE,
                            "models": MODEL,
                        },
                        timeout=(15, 60),
                    )
                    response.raise_for_status()
                    payload = response.json()

                    if payload.get("error"):
                        raise ValueError(payload.get("reason"))

                    daily = payload["daily"]
                    table = pd.DataFrame({
                        "date": daily["time"],
                        "rain_mm": daily["rain_sum"],
                        "precipitation_mm": daily["precipitation_sum"],
                        "temperature_mean_c":
                            daily["temperature_2m_mean"],
                    })

                    table["hub"] = hub.hub
                    table["requested_latitude"] = hub.latitude
                    table["requested_longitude"] = hub.longitude
                    table["grid_latitude"] = payload["latitude"]
                    table["grid_longitude"] = payload["longitude"]
                    table["weather_model"] = MODEL
                    table["timezone"] = TIMEZONE

                    if not valid_weather(table, hub, dates):
                        raise ValueError(
                            "Incomplete or invalid weather response."
                        )

                    downloaded += 1
                    time.sleep(1)

                # Convert numeric values consistently before joining.
                table[VARIABLES] = table[VARIABLES].apply(
                    pd.to_numeric, errors="raise"
                )

                if (table[["rain_mm", "precipitation_mm"]] < 0).any().any():
                    raise ValueError("Negative precipitation returned.")

                atomic_csv(table, cache_file)
                tables.append(table)

            except (
                requests.RequestException, ValueError, KeyError, OSError
            ) as error:
                failures.append({
                    "hub": hub.hub,
                    "error": str(error),
                })
                print("Failed:", hub.hub, str(error)[:150])

            if number % 10 == 0 or number == len(weather_hubs):
                print(f"Processed {number}/{len(weather_hubs)} hubs")
    finally:
        session.close()

    atomic_csv(
        pd.DataFrame(failures, columns=["hub", "error"]),
        PROCESSED / "weather_download_errors.csv",
    )

    if failures:
        raise RuntimeError(
            f"{len(failures)} hubs failed. Successful results are cached. "
            "Existing final weather/enriched files were not replaced. "
            "Rerun to retry."
        )

    weather = pd.concat(tables, ignore_index=True)
    weather["date"] = pd.to_datetime(weather["date"]).dt.normalize()

    if weather.duplicated(["hub", "date"]).any():
        raise ValueError("Duplicate hub-date weather records.")

    legs["departure_date"] = starts.dt.normalize()
    legs["arrival_date"] = ends.dt.normalize()
    original_count = len(legs)

    for prefix, hub_column, date_column in [
        ("source", "source_center", "departure_date"),
        ("destination", "destination_center", "arrival_date"),
    ]:
        endpoint_weather = weather[["hub", "date"] + VARIABLES].rename(
            columns={
                "hub": hub_column,
                "date": date_column,
                **{v: f"{prefix}_{v}" for v in VARIABLES},
            }
        )

        legs = legs.merge(
            endpoint_weather,
            on=[hub_column, date_column],
            how="left",
            validate="many_to_one",
        )

        legs[f"{prefix}_weather_available"] = legs[
            [f"{prefix}_{v}" for v in VARIABLES]
        ].notna().all(axis=1)

    if len(legs) != original_count:
        raise ValueError("Weather join changed the journey-leg count.")

    legs["both_weather_available"] = (
        legs["source_weather_available"]
        & legs["destination_weather_available"]
    )

    summary = (
        legs.groupby("split", as_index=False)
        .agg(
            journey_legs=("trip_uuid", "size"),
            source_weather_available=("source_weather_available", "sum"),
            destination_weather_available=(
                "destination_weather_available", "sum"
            ),
            both_weather_available=("both_weather_available", "sum"),
        )
    )
    summary["both_weather_pct"] = (
        100 * summary["both_weather_available"] / summary["journey_legs"]
    ).round(2)

    atomic_csv(weather_hubs, PROCESSED / "weather_hubs.csv")
    atomic_csv(weather, weather_file)
    atomic_csv(legs, PROCESSED / "legs_enriched.csv")
    atomic_csv(summary, PROCESSED / "weather_join_coverage.csv")

    print(f"\nWeather dates: {start_date} to {end_date}")
    print("Reused hubs:", reused)
    print("Downloaded hubs:", downloaded)
    print("Weather rows:", len(weather))
    print("Enriched journey legs:", len(legs))
    print(summary.to_string(index=False))
    print("\nMissing weather was kept as missing.")


if __name__ == "__main__":
    main()