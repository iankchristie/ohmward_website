import pdb
import openmeteo_requests

import requests_cache
import pandas as pd
from retry_requests import retry

from cover_colorado import latitudes, longitudes

# from cover_colorado import latitudes, longitudes
import openmeteo_requests
import requests_cache
import pandas as pd
from retry_requests import retry
from tqdm import tqdm
import time


def get_forecast():
    # Setup the Open-Meteo API client with cache and retry on error
    cache_session = requests_cache.CachedSession(".cache", expire_after=3600)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    openmeteo = openmeteo_requests.Client(session=retry_session)

    # Make sure all required weather variables are listed here
    # The order of variables in hourly or daily is important to assign them correctly below
    url = "https://api.open-meteo.com/v1/forecast"
    weather_vars = [
        "temperature_2m",
        "wind_direction_10m",
        "wind_speed_10m",
        "surface_pressure",
        "precipitation",
        "wind_gusts_10m",
        "rain",
        "snowfall",
        "cloud_cover",
        "soil_temperature_6cm",
        "soil_moisture_1_to_3cm",
        "terrestrial_radiation",
    ]

    # Validate size
    assert len(latitudes) == len(longitudes)

    # Batch size
    batch_size = 100

    # Combine into pairs
    locations = list(zip(latitudes, longitudes))

    # Batch locations
    batches = [
        locations[i : i + batch_size] for i in range(0, len(locations), batch_size)
    ]

    # Results
    all_hourly_dataframes = []

    points_queried = 0  # track how many points have been requested

    for batch in tqdm(batches, desc="Fetching weather batches"):
        batch_lats, batch_lons = zip(*batch)

        # Insert sleep if we're approaching the limit
        if points_queried >= 500:
            print("Sleeping to respect rate limits...")
            time.sleep(60)
            points_queried = 0  # reset counter

        params = {
            "latitude": batch_lats,
            "longitude": batch_lons,
            "hourly": weather_vars,
            "forecast_days": 2,
        }

        responses = openmeteo.weather_api(url, params=params)
        points_queried += len(batch_lats)

        for i, response in enumerate(responses):
            hourly = response.Hourly()

            time_index = pd.date_range(
                start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
                end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
                freq=pd.Timedelta(seconds=hourly.Interval()),
                inclusive="left",
            )

            hourly_data = {
                "latitude": response.Latitude(),
                "longitude": response.Longitude(),
                "date": time_index,
            }

            for idx, var in enumerate(weather_vars):
                hourly_data[var] = hourly.Variables(idx).ValuesAsNumpy()

            df = pd.DataFrame(hourly_data)
            all_hourly_dataframes.append(df)

    final_df = pd.concat(all_hourly_dataframes, ignore_index=True)
    final_df.rename(
        columns={
            "soil_temperature_6cm": "soil_moisture_0_to_7cm",
            "soil_moisture_1_to_3cm": "soil_temperature_0_to_7cm",
        },
        inplace=True,
    )
    return final_df


# if __name__ == "__main__":
# Combine and save
# weather_df = get_forecast()
# weather_df.to_csv("forecasting/colorado_weather_grid.csv", index=False)
# print(weather_df.head())
