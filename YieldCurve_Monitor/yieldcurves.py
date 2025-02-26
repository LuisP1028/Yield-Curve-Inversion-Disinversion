import pandas as pd
import requests
import json
from datetime import datetime
from plyer import notification
import logging

# Configuration Section
config = {
    "api_key": "",  # Replace with your FRED API key
    "pairs": [
        {"series1": "DGS10", "series2": "DGS2", "name": "10Y vs 2Y"},
        {"series1": "DGS30", "series2": "DGS3MO", "name": "30Y vs 3M"},
        # Add more pairs as needed
    ],
    "frequency": "d",  # Daily frequency
    "state_file": "yield_curve_state.json",  # File to store state between runs
}

# Set up logging for headless execution
logging.basicConfig(
    filename="yield_curve.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# FRED API endpoint
url = "https://api.stlouisfed.org/fred/series/observations"

# Function to fetch latest data from FRED API
def fetch_treasury_data(series_id, latest_only=True):
    params = {
        "series_id": series_id,
        "api_key": config["api_key"],
        "file_type": "json",
        "frequency": config["frequency"],
        "limit": 1,
        "sort_order": "desc"  # Get the latest observation
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()
    except Exception as e:
        logging.error(f"Request failed for {series_id}: {e}")
        return pd.DataFrame()

    if "observations" not in data:
        logging.error(f"Error fetching data for {series_id}: {data}")
        return pd.DataFrame()

    observations = data["observations"]
    df = pd.DataFrame(observations)
    df["date"] = pd.to_datetime(df["date"])
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["value"] = df["value"].interpolate(method="linear", axis=0)
    return df

# Function to load previous state
def load_state():
    try:
        with open(config["state_file"], "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Function to save current state
def save_state(state):
    with open(config["state_file"], "w") as f:
        json.dump(state, f, indent=4)

# Function to check for inversions and disinversions
def check_inversions(pair, state):
    series1 = pair["series1"]
    series2 = pair["series2"]
    name = pair["name"]

    # Fetch latest data
    df1 = fetch_treasury_data(series1)
    df2 = fetch_treasury_data(series2)

    if df1.empty or df2.empty:
        logging.error(f"Error fetching latest data for {name}")
        return

    latest_date = df1["date"].iloc[0]
    yield1 = df1["value"].iloc[0]
    yield2 = df2["value"].iloc[0]

    # Determine current state
    current_state = "inverted" if yield2 > yield1 else "normal"

    # Load previous state for this pair
    pair_state = state.get(name, {})
    previous_state = pair_state.get("previous_state", None)
    last_check_date = pair_state.get("last_check_date", None)

    # Skip if no new data since last check
    if last_check_date and last_check_date >= latest_date.strftime("%Y-%m-%d"):
        return

    # Notify if state has changed
    if previous_state and previous_state != current_state:
        event = "Inversion" if current_state == "inverted" else "Disinversion"
        try:
            notification.notify(
                title=f"Yield Curve {event} Alert",
                message=f"{event} detected for {name} on {latest_date.strftime('%Y-%m-%d')}",
                timeout=10
            )
            logging.info(f"{event} detected for {name} on {latest_date.strftime('%Y-%m-%d')}")
        except Exception as e:
            logging.error(f"Notification failed for {name}: {e}")

    # Update state
    state[name] = {
        "previous_state": current_state,
        "last_check_date": latest_date.strftime("%Y-%m-%d")
    }

# Main function
def main():
    state = load_state()
    for pair in config["pairs"]:
        check_inversions(pair, state)
    save_state(state)

if __name__ == "__main__":
    main()