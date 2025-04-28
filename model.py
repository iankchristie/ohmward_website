import xgboost as xgb
import pandas as pd


VARIABLES = [
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


def make_feature_names(num_steps: int = 12):
    names = []
    for step in range(1, num_steps + 1):
        for var in VARIABLES:
            names.append(f"{var}-{step}")
    return names


FEATURE_NAMES = make_feature_names(12)


def transform_to_model_input(ts: pd.DataFrame, num_steps: int = 12) -> pd.DataFrame:
    """
    Given a DataFrame `ts` with columns ["date"]+VARIABLES and one row per hour,
    return a single‐row DataFrame with columns FEATURE_NAMES, flattened in time order.

    ts: must contain at least `num_steps` rows (the most recent `num_steps` hours),
        sorted by ts["date"] ascending or will be sorted automatically.
    """
    # 1) Sort by date ascending
    ts_sorted = ts.sort_values("date").reset_index(drop=True)

    # 2) If there are more rows than num_steps, take the last num_steps
    if len(ts_sorted) < num_steps:
        raise ValueError(f"Expected at least {num_steps} rows, got {len(ts_sorted)}")
    ts_last = ts_sorted.iloc[-num_steps:]

    # 3) Build a flat dict
    flat = {}
    for i, (_, row) in enumerate(ts_last.iterrows(), start=1):
        for var in VARIABLES:
            flat[f"{var}-{i}"] = row[var]

    # 4) Create a one‐row DataFrame, enforcing column order
    return pd.DataFrame([flat], columns=FEATURE_NAMES)


booster = xgb.Booster()
booster.load_model("xgboost_best_model.json")


def model(ts: pd.DataFrame):
    # ts: the multi‐row hourly DataFrame for one location
    X = transform_to_model_input(ts, num_steps=12)
    dmat = xgb.DMatrix(X)  # convert to DMatrix
    pred = booster.predict(dmat)  # returns array of length 1
    return float(pred[0])
