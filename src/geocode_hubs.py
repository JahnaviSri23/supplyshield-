import json
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def normalise(value):
    """Compare names without accents, case or extra spaces."""
    if pd.isna(value):
        return ""

    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(
        character
        for character in text
        if not unicodedata.combining(character)
    )

    return " ".join(text.casefold().split())


def save_cache(cache, cache_file):
    """Save the cache safely."""
    temporary_file = cache_file.with_suffix(".tmp")

    temporary_file.write_text(
        json.dumps(cache, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    temporary_file.replace(cache_file)


def save_table(data, output_file):
    """Save progress without replacing the CSV halfway through."""
    temporary_file = output_file.with_suffix(".tmp")
    data.to_csv(temporary_file, index=False)
    temporary_file.replace(output_file)


def create_session():
    """Retry temporary connection and server failures."""
    session = requests.Session()

    retry_policy = Retry(
        total=3,
        connect=3,
        read=3,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        respect_retry_after_header=True,
    )

    session.mount(
        "https://",
        HTTPAdapter(max_retries=retry_policy),
    )

    return session


def lookup(city, state, session, cache, cache_file):
    """Accept only one distinct matching city-and-state location."""
    if not normalise(city) or not normalise(state):
        return {"match": "missing_city_or_state"}

    key = f"{normalise(city)}|{normalise(state)}"

    # Reuse completed searches, but retry cached errors if any exist.
    if key in cache:
        cached = cache[key]

        if cached.get("match") != "request_error":
            return cached

    try:
        response = session.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": str(city).strip(),
                "count": 100,
                "language": "en",
                "format": "json",
                "countryCode": "IN",
            },
            timeout=(15, 60),
        )

        response.raise_for_status()
        payload = response.json()

        if payload.get("error"):
            raise ValueError(
                payload.get("reason", "Geocoding API error")
            )

        candidates = []

        for place in payload.get("results", []):
            matches = (
                normalise(place.get("name")) == normalise(city)
                and normalise(place.get("admin1")) == normalise(state)
                and place.get("country_code") == "IN"
                and place.get("latitude") is not None
                and place.get("longitude") is not None
            )

            if matches:
                candidates.append(place)

        # Do not count repeated coordinates as separate locations.
        unique_candidates = {}

        for place in candidates:
            coordinates = (
                place["latitude"],
                place["longitude"],
            )
            unique_candidates[coordinates] = place

        candidates = list(unique_candidates.values())

        if len(candidates) == 1:
            place = candidates[0]

            result = {
                "match": "city+state",
                "matched_name": place.get("name"),
                "matched_state": place.get("admin1"),
                "latitude": float(place["latitude"]),
                "longitude": float(place["longitude"]),
                "coordinate_method": "city_approximation",
            }

        elif len(candidates) > 1:
            result = {
                "match": "ambiguous_city_state",
            }

        else:
            result = {
                "match": "no_exact_match",
            }

        cache[key] = result
        save_cache(cache, cache_file)

        return result

    except (requests.RequestException, ValueError) as error:
        # Do not cache failures: the next run can retry them.
        return {
            "match": "request_error",
            "error": str(error),
        }

    finally:
        time.sleep(0.5)


def prepare_columns(hubs):
    """Create columns before assigning individual cells."""
    text_columns = [
        "match",
        "matched_name",
        "matched_state",
        "coordinate_method",
        "error",
    ]

    for column in text_columns:
        if column not in hubs.columns:
            hubs[column] = pd.Series(
                index=hubs.index,
                dtype="object",
            )
        else:
            hubs[column] = hubs[column].astype("object")

    for column in ["latitude", "longitude"]:
        if column not in hubs.columns:
            hubs[column] = float("nan")
        else:
            hubs[column] = pd.to_numeric(
                hubs[column],
                errors="coerce",
            )

    return hubs


def prepare_search_names(hubs):
    """Extract city and state while retaining original names."""
    names = hubs["name"].astype("string")

    # Handles names such as "Rohtak (Haryana)" too.
    clean_names = (
        names
        .str.replace(r"\s*\([^)]*\)", "", regex=True)
        .str.strip()
    )

    hubs["city"] = clean_names.str.split("_").str[0].str.strip()

    hubs["state"] = (
        names
        .str.extract(r"\(([^)]+)\)", expand=False)
        .str.strip()
    )

    hubs["search_city"] = hubs["city"].replace({
        "Gurgaon": "Gurugram",
        "Bangalore": "Bengaluru",
        "MAA": "Chennai",
        "CCU": "Kolkata",
        "AMD": "Ahmedabad",
        "BLR": "Bengaluru",
        "Cjb": "Coimbatore",
        "Del": "Delhi",
        "FBD": "Faridabad",
    })

    hubs["search_state"] = hubs["state"].replace({
        "Orissa": "Odisha",
        "Pondicherry": "Puducherry",
        "Delhi": "National Capital Territory of Delhi",
    })
    additional_aliases = {
        "Muzaffrpur": "Muzaffarpur",
        "Bhubaneshwar": "Bhubaneswar",
        "Trivandrum": "Thiruvananthapuram",
        "Cochin": "Kochi",
        "Mumbai Hub": "Mumbai",
        "Mumbai Antop Hill": "Mumbai",
        "LowerParel": "Mumbai",
        "BOM": "Mumbai",
        "GZB": "Ghaziabad",
        "Hyd": "Hyderabad",
        "Blr": "Bengaluru",
        "PNQ Vadgaon Sheri DPC": "Pune",
        "PNQ Rahatani DPC": "Pune",
        "PNQ Pashan DPC": "Pune",
        "Pune Balaji Nagar": "Pune",
        "Bhopal MP Nagar": "Bhopal",
    }

    hubs["search_city"] = hubs["search_city"].replace(
        additional_aliases
    )

    hubs["search_state"] = hubs["state"].replace({
        "Orissa": "Odisha",
        "Pondicherry": "Puducherry",
        "Delhi": "National Capital Territory of Delhi",
    })
    return hubs


def main():
    root = Path(__file__).resolve().parents[1]
    processed = root / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)

    output_file = processed / "hubs_threshold3.csv"
    starting_file = processed / "hubs_threshold3_working.csv"
    review_file = processed / "hubs_threshold3_review.csv"
    cache_file = processed / "geocode_cache_threshold3.json"

    # Resume from the latest saved results.
    source_file = (
        output_file if output_file.exists() else starting_file
    )

    if not source_file.exists():
        raise FileNotFoundError(
            f"Cannot find the starting hub table: {source_file}"
        )

    hubs = pd.read_csv(
        source_file,
        dtype={"hub": "string"},
    )

    required_columns = {"hub", "name"}

    if not required_columns.issubset(hubs.columns):
        raise ValueError(
            "The hub table must contain 'hub' and 'name' columns."
        )

    if hubs["hub"].isna().any() or hubs["hub"].duplicated().any():
        raise ValueError("Hub IDs must be present and unique.")

    hubs = prepare_columns(hubs)
    hubs = prepare_search_names(hubs)

    if cache_file.exists():
        cache = json.loads(
            cache_file.read_text(encoding="utf-8")
        )
    else:
        cache = {}

    preserved = 0
    processed_count = 0

    print("Project:", root)
    print("Input:", source_file)
    print("Total hubs:", len(hubs))
    print("Existing matches will be preserved.")
    print("Connection failures may take longer because of retries.\n")

    with create_session() as session:
        try:
            for position, index in enumerate(hubs.index, start=1):
                status = hubs.at[index, "match"]

                existing_match = (
                    pd.notna(status)
                    and status == "city+state"
                    and pd.notna(hubs.at[index, "latitude"])
                    and pd.notna(hubs.at[index, "longitude"])
                )

                if existing_match:
                    preserved += 1

                    if pd.isna(
                        hubs.at[index, "coordinate_method"]
                    ):
                        hubs.at[index, "coordinate_method"] = (
                            "previous_city_match_not_revalidated"
                        )

                    hubs.at[index, "error"] = None

                else:
                    result = lookup(
                        hubs.at[index, "search_city"],
                        hubs.at[index, "search_state"],
                        session,
                        cache,
                        cache_file,
                    )

                    # Clear previous lookup values.
                    for column in [
                        "matched_name",
                        "matched_state",
                        "coordinate_method",
                        "error",
                    ]:
                        hubs.at[index, column] = None

                    hubs.at[index, "latitude"] = float("nan")
                    hubs.at[index, "longitude"] = float("nan")

                    for column, value in result.items():
                        hubs.at[index, column] = value

                processed_count = position

                if position % 100 == 0:
                    save_table(hubs, output_file)
                    print(
                        f"Processed {position}/{len(hubs)} hubs",
                        flush=True,
                    )

        except KeyboardInterrupt:
            save_table(hubs, output_file)
            print(
                f"\nStopped after {processed_count} hubs. "
                "Progress saved; run the command again to resume."
            )
            return

    save_table(hubs, output_file)

    review = hubs.loc[
        ~hubs["match"].eq("city+state")
    ].copy()

    save_table(review, review_file)

    located = (
        hubs["match"].eq("city+state")
        & hubs["latitude"].notna()
        & hubs["longitude"].notna()
    )

    print("\nPreviously saved matches preserved:", preserved)

    print("\nMatch counts:")
    print(hubs["match"].value_counts(dropna=False))

    coverage = 100 * located.mean() if len(hubs) else 0

    print(f"\nCoordinate coverage: {coverage:.2f}%")

    print("\nFirst 20 hubs needing review:")
    print(
        review[
            [
                "hub",
                "name",
                "search_city",
                "search_state",
                "match",
            ]
        ].head(20).to_string(index=False)
    )

    errors = hubs.loc[
        hubs["match"].eq("request_error"),
        ["hub", "search_city", "search_state", "error"],
    ]

    if not errors.empty:
        print("\nRemaining request errors:")
        print(errors.to_string(index=False))

    print("\nSaved:", output_file)
    print("Saved:", review_file)


if __name__ == "__main__":
    main()