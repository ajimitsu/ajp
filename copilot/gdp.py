import requests
import pandas as pd
from functools import wraps
import datetime

# Decorator to log when the API is called
def log_api_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        print(f"[{datetime.datetime.now()}] Calling API...")
        return func(*args, **kwargs)
    return wrapper

class GDPFetcher:
    def __init__(self, countries):
        self.countries = countries
        self.indicator = 'NY.GDP.MKTP.CD'
        self.base_url = 'http://api.worldbank.org/v2'

    @log_api_call
    def fetch_data(self):
        url = f"{self.base_url}/country/{';'.join(self.countries)}/indicator/{self.indicator}?format=json&per_page=500"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()

    def parse_data(self, data):
        entries = data[1]
        gdp_data = [{
            'Country': entry['country']['value'],
            'Year': entry['date'],
            'GDP (current US$)': entry['value']
        } for entry in entries if entry['value'] is not None]
        return pd.DataFrame(gdp_data)

    def get_latest_gdp(self):
        raw_data = self.fetch_data()
        df = self.parse_data(raw_data)
        latest_gdp = df.sort_values(by='Year', ascending=False).drop_duplicates(subset='Country')
        return latest_gdp

# Usage
if __name__ == "__main__":
    countries = ['USA', 'CHN', 'JPN', 'DEU', 'IND', 'GBR', 'FRA', 'ITA', 'BRA', 'CAN']
    fetcher = GDPFetcher(countries)
    latest_gdp_df = fetcher.get_latest_gdp()
    print(latest_gdp_df)