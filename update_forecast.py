import pdb
from display_forecast import forecast_to_predictions
from forecast_colorado import get_forecast


def update_forecast_file():
    forecast_df = get_forecast()
    predictions_df = forecast_to_predictions(forecast_df)
    predictions_df.to_csv("data/colorado_outage_predictions.csv", index=False)
