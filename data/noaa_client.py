"""NOAA Climate Data Online API client for weather data."""

import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

import config
from utils.cache import Cache


class NOAAClient:
    """Client for NOAA Climate Data Online (CDO) API."""

    def __init__(self, api_key: str = None):
        self.base_url = config.NOAA_BASE_URL
        self.api_key = api_key or config.NOAA_API_KEY
        self.cache = Cache()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[Dict]:
        """Make a request to the NOAA API."""
        if not self.api_key:
            print("NOAA API key not configured, using mock data")
            return None

        url = f"{self.base_url}/{endpoint}"
        headers = {"token": self.api_key}

        # Check cache first
        cache_key = f"noaa_{endpoint}_{str(sorted((params or {}).items()))}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.cache.set(cache_key, data)
            return data
        except requests.RequestException as e:
            print(f"NOAA API error: {e}")
            return None

    def get_stations(
        self,
        state: str = None,
        county_fips: str = None,
        dataset: str = "GHCND",
        limit: int = 100,
    ) -> pd.DataFrame:
        """Get weather stations in an area."""
        params = {
            "datasetid": dataset,
            "limit": limit,
        }

        if state:
            params["locationid"] = f"FIPS:{self._get_state_fips(state)}"

        data = self._make_request("stations", params)

        if not data or "results" not in data:
            return pd.DataFrame()

        return pd.DataFrame(data["results"])

    def get_precipitation(
        self,
        station_id: str = None,
        location_fips: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """Get daily precipitation data."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        params = {
            "datasetid": "GHCND",
            "datatypeid": "PRCP",  # Precipitation
            "startdate": start_date.strftime("%Y-%m-%d"),
            "enddate": end_date.strftime("%Y-%m-%d"),
            "units": "standard",
            "limit": 1000,
        }

        if station_id:
            params["stationid"] = station_id
        elif location_fips:
            params["locationid"] = f"FIPS:{location_fips}"

        data = self._make_request("data", params)

        if not data or "results" not in data:
            return self._get_mock_precipitation(start_date, end_date)

        df = pd.DataFrame(data["results"])
        df["date"] = pd.to_datetime(df["date"])
        df["precipitation_inches"] = df["value"] / 254  # Convert from tenths of mm
        return df

    def _get_mock_precipitation(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate mock precipitation data for demo."""
        import numpy as np

        np.random.seed(123)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        # Simulate Gulf Coast precipitation patterns
        precipitation = []
        for date in date_range:
            month = date.month
            # Higher rainfall in summer/early fall (hurricane season) and spring
            if month in [6, 7, 8, 9]:  # Summer/hurricane
                base_prob = 0.45
                heavy_prob = 0.15
            elif month in [3, 4, 5]:  # Spring
                base_prob = 0.35
                heavy_prob = 0.10
            elif month in [11, 12, 1, 2]:  # Winter
                base_prob = 0.30
                heavy_prob = 0.08
            else:
                base_prob = 0.25
                heavy_prob = 0.05

            if np.random.random() < base_prob:
                if np.random.random() < heavy_prob:
                    # Heavy rain event
                    amount = np.random.exponential(2.0) + 1.0
                else:
                    # Normal rain
                    amount = np.random.exponential(0.5)
                precipitation.append(min(amount, 10.0))  # Cap at 10 inches
            else:
                precipitation.append(0.0)

        return pd.DataFrame({
            "date": date_range,
            "precipitation_inches": precipitation,
            "station": "GHCND:USW00013894",  # Mobile Regional Airport
        })

    def get_temperature(
        self,
        station_id: str = None,
        location_fips: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """Get daily temperature data."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365)
        if not end_date:
            end_date = datetime.now()

        params = {
            "datasetid": "GHCND",
            "datatypeid": ["TMAX", "TMIN", "TAVG"],
            "startdate": start_date.strftime("%Y-%m-%d"),
            "enddate": end_date.strftime("%Y-%m-%d"),
            "units": "standard",
            "limit": 1000,
        }

        if station_id:
            params["stationid"] = station_id
        elif location_fips:
            params["locationid"] = f"FIPS:{location_fips}"

        data = self._make_request("data", params)

        if not data or "results" not in data:
            return self._get_mock_temperature(start_date, end_date)

        df = pd.DataFrame(data["results"])
        df["date"] = pd.to_datetime(df["date"])
        # Pivot to get TMAX, TMIN, TAVG as columns
        df = df.pivot(index="date", columns="datatype", values="value").reset_index()
        return df

    def _get_mock_temperature(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate mock temperature data for demo."""
        import numpy as np

        np.random.seed(456)
        date_range = pd.date_range(start=start_date, end=end_date, freq="D")

        temps = []
        for date in date_range:
            # Gulf Coast temperature pattern
            day_of_year = date.dayofyear
            # Sinusoidal pattern with peak in July
            base_temp = 68 + 18 * np.sin((day_of_year - 100) * 2 * np.pi / 365)
            daily_variation = np.random.normal(0, 3)

            avg_temp = base_temp + daily_variation
            temps.append({
                "date": date,
                "TAVG": avg_temp,
                "TMAX": avg_temp + np.random.uniform(8, 15),
                "TMIN": avg_temp - np.random.uniform(8, 15),
            })

        return pd.DataFrame(temps)

    def get_weather_events(
        self,
        state: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """Get severe weather events (storms, hurricanes, etc.)."""
        # NOAA Storm Events database - simplified for demo
        return self._get_mock_weather_events(state, start_date, end_date)

    def _get_mock_weather_events(
        self,
        state: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Generate mock severe weather events."""
        events = [
            {"date": "2023-08-30", "event_type": "Hurricane", "name": "Idalia", "severity": "high"},
            {"date": "2023-06-15", "event_type": "Tropical Storm", "name": "TS3", "severity": "medium"},
            {"date": "2023-04-12", "event_type": "Severe Thunderstorm", "name": None, "severity": "medium"},
            {"date": "2022-09-28", "event_type": "Hurricane", "name": "Ian", "severity": "high"},
            {"date": "2022-06-20", "event_type": "Flood", "name": None, "severity": "medium"},
            {"date": "2021-08-29", "event_type": "Hurricane", "name": "Ida", "severity": "high"},
            {"date": "2021-05-15", "event_type": "Severe Thunderstorm", "name": None, "severity": "low"},
        ]

        df = pd.DataFrame(events)
        df["date"] = pd.to_datetime(df["date"])

        if start_date:
            df = df[df["date"] >= start_date]
        if end_date:
            df = df[df["date"] <= end_date]

        return df

    def _get_state_fips(self, state_abbrev: str) -> str:
        """Get FIPS code for state abbreviation."""
        from utils.helpers import get_state_fips
        return get_state_fips(state_abbrev) or "01"
