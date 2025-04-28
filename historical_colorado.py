import os
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from cover_colorado import latitudes, longitudes

# from cover_colorado import latitudes, longitudes
from datetime import datetime, timedelta
from tqdm import tqdm
import time


def get_historical(date: datetime, batch_size: int = 50) -> pd.DataFrame:
    """
    Fetch historical weather data for a given date, batching large lat/lon lists into multiple API requests,
    with file-level caching to avoid re-fetching.

    Args:
        date (datetime): The date (UTC) for which to retrieve historical data.
        batch_size (int): Number of locations to include per API call.

    Returns:
        pd.DataFrame: Hourly weather data for all lat/lon points for the specified date.
    """
    # Prepare date strings and cache path
    date_str = date.strftime("%Y-%m-%d")
    cache_dir = "forecasting"
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"historical_{date_str}.csv")

    # If cache exists, load and return
    if os.path.exists(cache_file):
        print(f"Loading cached historical data for {date_str} from {cache_file}")
        return pd.read_csv(cache_file, parse_dates=["date"])

    # Setup HTTP-level cache and retry
    cache_session = requests_cache.CachedSession(
        cache_name=".cache_http", backend="sqlite", expire_after=-1
    )
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Prepare batching of locations
    assert len(latitudes) == len(longitudes), "Latitude and longitude lists must match"
    locations = list(zip(latitudes, longitudes))
    batches = [
        locations[i : i + batch_size] for i in range(0, len(locations), batch_size)
    ]

    url = "https://archive-api.open-meteo.com/v1/archive"
    hourly_vars = [
        "temperature_2m",
        "precipitation",
        "rain",
        "snowfall",
        "surface_pressure",
        "wind_speed_10m",
        "wind_gusts_10m",
        "wind_direction_10m",
        "soil_moisture_0_to_7cm",
        "cloud_cover",
        "soil_temperature_0_to_7cm",
        "terrestrial_radiation",
    ]

    all_dfs = []
    points_queried = 0

    for batch in tqdm(batches, desc="Fetching historical batches"):
        batch_lats, batch_lons = zip(*batch)

        # Rate limit protection
        if points_queried >= 500:
            print("Sleeping to respect rate limits...")
            time.sleep(60)
            points_queried = 0

        params = {
            "latitude": batch_lats,
            "longitude": batch_lons,
            "start_date": date_str,
            "end_date": (date + timedelta(days=1)).strftime("%Y-%m-%d"),
            "hourly": hourly_vars,
        }
        responses = openmeteo.weather_api(url, params=params)
        points_queried += len(batch_lats)

        for response in responses:
            hourly = response.Hourly()
            time_index = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )
            data = {
                "latitude": response.Latitude(),
                "longitude": response.Longitude(),
                "date": time_index,
            }
            for idx, var in enumerate(hourly_vars):
                data[var] = hourly.Variables(idx).ValuesAsNumpy()
            all_dfs.append(pd.DataFrame(data))

    # Concatenate results and save cache
    if all_dfs:
        full_df = pd.concat(all_dfs, ignore_index=True)
        return full_df
    else:
        print("No data fetched for given date.")
        return pd.DataFrame()


# if __name__ == "__main__":
#     # Example usage for Feb 10, 2025
#     specific_date = datetime(2025, 2, 10)
#     df = get_historical(specific_date, batch_size=100)
#     print(df.head())
