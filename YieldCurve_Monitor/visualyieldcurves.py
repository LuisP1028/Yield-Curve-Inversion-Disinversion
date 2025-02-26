import pandas as pd
import requests
import matplotlib.pyplot as plt
from datetime import datetime

# Configuration Section
config = {
    "api_key": "",  ################ Your FRED API key
    "series_ids": ['DGS10', 'DGS2'],  # Treasury series to compare (e.g., 10-year and 2-year yields)
    "start_date": "2000-01-01",  # Start date for data fetch
    "frequency": 'd',  # Frequency of data ('d' for daily, 'm' for monthly)
    "plot_title": "10-Year vs 2-Year Treasury Yield Curve with Inversions and Disinversions",
    "x_label": "Date",
    "y_label": "Yield (%)",
    "highlight_color_inversion": "black",  # Color for inversion points
    "highlight_color_disinversion": "green",  # Color for disinversion points
    "line_colors": ['blue', 'red'],  # Colors for the yield curves (10-year, 2-year)
    "inversion_marker": "o",  # Marker style for inversion points
    "disinversion_marker": "s",  # Marker style for disinversion points
}

# FRED API endpoint
url = "https://api.stlouisfed.org/fred/series/observations"

# Function to fetch data from FRED API with error handling
def fetch_treasury_data(series_id, start_date=config['start_date']):
    params = {
        'series_id': series_id,
        'api_key': config['api_key'],
        'file_type': 'json',
        'frequency': config['frequency'],
        'start_date': start_date
    }
    response = requests.get(url, params=params)
    data = response.json()

    # Check if 'observations' exists in the response, otherwise print the response
    if 'observations' not in data:
        print(f"Error fetching data for series {series_id}: {data}")
        return pd.DataFrame()  # Return an empty DataFrame in case of error

    # Convert data to pandas DataFrame
    observations = data['observations']
    df = pd.DataFrame(observations)
    df['date'] = pd.to_datetime(df['date'])
    
    # Replace invalid values (such as ".") with NaN, then convert the 'value' column to numeric
    df['value'] = pd.to_numeric(df['value'], errors='coerce')
    
    # Interpolate missing values (NaN) using linear interpolation
    df['value'] = df['value'].interpolate(method='linear', axis=0)
    
    return df

# Fetch yield data for different maturities
df_10yr = fetch_treasury_data(config['series_ids'][0])
df_2yr = fetch_treasury_data(config['series_ids'][1])

# If there's an issue fetching data, return early
if df_10yr.empty or df_2yr.empty:
    print("Error: One or both of the datasets could not be fetched.")
    exit()

# Merge data on date
df = pd.merge(df_10yr[['date', 'value']], df_2yr[['date', 'value']], on='date', suffixes=('_10yr', '_2yr'))

# Initialize variables to track inversion and disinversion events
inversion_dates = []
disinversion_dates = []

# Track the current state (normal or inverted)
previous_state = 'normal'  # Initially, the curve is considered normal

# Loop through the data to detect transitions
for i in range(1, len(df)):
    # Check for inversion (2-year yield > 10-year yield)
    if df['value_2yr'].iloc[i] > df['value_10yr'].iloc[i]:
        if previous_state == 'normal':  # Only highlight if previously normal
            inversion_dates.append(df.iloc[i])
            previous_state = 'inverted'
    # Check for disinversion (10-year yield > 2-year yield)
    elif df['value_10yr'].iloc[i] > df['value_2yr'].iloc[i]:
        if previous_state == 'inverted':  # Only highlight if previously inverted
            disinversion_dates.append(df.iloc[i])
            previous_state = 'normal'

# Plot the data
plt.figure(figsize=(10, 6))
plt.plot(df['date'], df['value_10yr'], label='10-Year Yield', color=config['line_colors'][0])
plt.plot(df['date'], df['value_2yr'], label='2-Year Yield', color=config['line_colors'][1])

# Highlight inversion points
if inversion_dates:
    inversion_df = pd.DataFrame(inversion_dates)
    plt.scatter(inversion_df['date'], inversion_df['value_2yr'], 
                color=config['highlight_color_inversion'], 
                label='Inversion Points', marker=config['inversion_marker'], zorder=5)

# Highlight disinversion points
if disinversion_dates:
    disinversion_df = pd.DataFrame(disinversion_dates)
    plt.scatter(disinversion_df['date'], disinversion_df['value_2yr'], 
                color=config['highlight_color_disinversion'], 
                label='Disinversion Points', marker=config['disinversion_marker'], zorder=5)

# Customize the plot
plt.title(config['plot_title'])
plt.xlabel(config['x_label'])
plt.ylabel(config['y_label'])
plt.legend()
plt.grid(True)
plt.show()

# Print inversion and disinversion dates
print("Inversion Dates:\n", pd.DataFrame(inversion_dates)[['date', 'value_2yr', 'value_10yr']])
print("\nDisinversion Dates:\n", pd.DataFrame(disinversion_dates)[['date', 'value_2yr', 'value_10yr']])
