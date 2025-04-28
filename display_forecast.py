import os
import pdb
import pandas as pd
from datetime import datetime, timedelta, timezone

from model import model

# from model import model


def forecast_to_predictions(df=None, file_path=None, now_override=None):
    if file_path:
        if not os.path.exists(file_path):
            print("File does not exist")
            return
        df = pd.read_csv(file_path, parse_dates=["date"])

    # Parse as UTC then drop timezone (so we have tz‐naive times in UTC)
    df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_convert(None)

    # Determine “now” in UTC, then drop tzinfo
    if now_override is not None:
        now = now_override
        if now.tzinfo is not None:
            now = now.astimezone(timezone.utc).replace(tzinfo=None)
    else:
        now = datetime.now(timezone.utc).replace(tzinfo=None)

    window_end = now + timedelta(hours=12)

    predictions = {}
    for (lat, lon), group in df.groupby(["latitude", "longitude"]):
        sel = group[(group["date"] >= now) & (group["date"] < window_end)].sort_values(
            "date"
        )
        if not sel.empty:
            predictions[(lat, lon)] = model(sel)

    # Assemble output DataFrame
    preds_df = pd.DataFrame(
        [
            {"latitude": lat, "longitude": lon, "probability": prob}
            for (lat, lon), prob in predictions.items()
        ]
    )
    return preds_df


# if __name__ == "__main__":
# pass
# custom_time = datetime(2025, 4, 9, 12, 0, tzinfo=timezone.utc)
# predictions_df = forecast_to_predictions(
#     None, "app/historical_2025-04-09.csv", custom_time
# )
# predictions_df.to_csv("forecasting/colorado_outage_predictions.csv", index=False)


# Plot
# fig = px.scatter_geo(
#     predictions_df,
#     lat="latitude",
#     lon="longitude",
#     color="probability",
#     color_continuous_scale="RdYlGn_r",  # red = high prob, green = low
#     size="probability",
#     size_max=12,
#     scope="usa",
#     title="Outage Probability by Location",
# )

# fig.update_layout(
#     geo=dict(
#         center=dict(lat=39.0, lon=-105.5),  # Centered on Colorado
#         projection_scale=6,
#         showland=True,
#         landcolor="rgb(240, 240, 240)",
#     )
# )

# fig.show()
