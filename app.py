from flask import Flask, jsonify, render_template, request

from apscheduler.schedulers.background import BackgroundScheduler
import pandas as pd
import time
from datetime import datetime
from display_forecast import forecast_to_predictions
from historical_colorado import get_historical
from update_forecast import update_forecast_file

# import pdb


app = Flask(__name__)


def update_predictions():
    print(f"[{time.strftime('%X')}] Updating predictions...")
    update_forecast_file()


# Scheduler setup
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_predictions, trigger="interval", hours=1)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["GET"])
def predict():
    dt_str = request.args.get("datetime")
    if dt_str:
        try:
            dt = datetime.fromisoformat(dt_str)
            historical_df = get_historical(dt)
            predictions_df = forecast_to_predictions(historical_df, now_override=dt)
            points = predictions_df.to_dict(orient="records")
            # Use `dt` for filtering, model inference, etc.
        except ValueError:
            return jsonify({"error": "Invalid datetime format"}), 400
        return jsonify(points)

    csv_path = "data/colorado_outage_predictions.csv"
    # Load precomputed predictions or run model here
    df = pd.read_csv(csv_path)
    points = df.to_dict(orient="records")
    return jsonify(points)


if __name__ == "__main__":
    update_predictions()
    scheduler.start()
    app.run(host="0.0.0.0", port=8080)
