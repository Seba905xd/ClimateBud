"""Census Bureau API client for demographic and infrastructure data."""

import requests
from typing import Optional, Dict, Any
import pandas as pd

import config
from utils.cache import Cache
from utils.helpers import get_state_fips, get_county_fips


class CensusClient:
    """Client for US Census Bureau API."""

    def __init__(self, api_key: str = None):
        self.base_url = config.CENSUS_BASE_URL
        self.api_key = api_key or config.CENSUS_API_KEY
        self.cache = Cache()

    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Optional[list]:
        """Make a request to the Census API."""
        url = f"{self.base_url}/{endpoint}"

        if self.api_key:
            params = params or {}
            params["key"] = self.api_key

        # Check cache first
        cache_key = f"census_{endpoint}_{str(sorted((params or {}).items()))}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        try:
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            self.cache.set(cache_key, data)
            return data
        except requests.RequestException as e:
            print(f"Census API error: {e}")
            return None

    def get_population(
        self,
        state: str,
        county: str = None,
        year: int = 2022,
    ) -> pd.DataFrame:
        """Get population data for an area."""
        state_fips = get_state_fips(state)
        if not state_fips:
            return self._get_mock_population(state, county)

        # ACS 5-year estimates
        endpoint = f"{year}/acs/acs5"
        params = {
            "get": "NAME,B01001_001E",  # Total population
            "for": f"county:*" if not county else None,
            "in": f"state:{state_fips}",
        }

        if county:
            county_fips = get_county_fips(state, county)
            if county_fips:
                params["for"] = f"county:{county_fips[-3:]}"

        data = self._make_request(endpoint, params)

        if not data or len(data) < 2:
            return self._get_mock_population(state, county)

        # Convert to DataFrame
        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)
        df = df.rename(columns={"B01001_001E": "population", "NAME": "name"})
        df["population"] = pd.to_numeric(df["population"], errors="coerce")

        return df

    def _get_mock_population(self, state: str, county: str) -> pd.DataFrame:
        """Return mock population data."""
        if county and county.upper() == "BALDWIN":
            return pd.DataFrame([{
                "name": "Baldwin County, Alabama",
                "population": 231767,
                "state": "01",
                "county": "003",
            }])
        return pd.DataFrame([{
            "name": f"{county or 'Unknown'} County, {state}",
            "population": 100000,
            "state": get_state_fips(state) or "00",
            "county": "000",
        }])

    def get_housing_age(
        self,
        state: str,
        county: str = None,
        year: int = 2022,
    ) -> pd.DataFrame:
        """Get housing age data (proxy for infrastructure age)."""
        state_fips = get_state_fips(state)
        if not state_fips:
            return self._get_mock_housing_age(state, county)

        endpoint = f"{year}/acs/acs5"
        # Year structure built variables
        variables = [
            "B25034_001E",  # Total
            "B25034_002E",  # Built 2020 or later
            "B25034_003E",  # Built 2010-2019
            "B25034_004E",  # Built 2000-2009
            "B25034_005E",  # Built 1990-1999
            "B25034_006E",  # Built 1980-1989
            "B25034_007E",  # Built 1970-1979
            "B25034_008E",  # Built 1960-1969
            "B25034_009E",  # Built 1950-1959
            "B25034_010E",  # Built 1940-1949
            "B25034_011E",  # Built 1939 or earlier
        ]

        params = {
            "get": f"NAME,{','.join(variables)}",
            "for": "county:*",
            "in": f"state:{state_fips}",
        }

        data = self._make_request(endpoint, params)

        if not data or len(data) < 2:
            return self._get_mock_housing_age(state, county)

        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)

        # Convert numeric columns
        for var in variables:
            if var in df.columns:
                df[var] = pd.to_numeric(df[var], errors="coerce")

        return df

    def _get_mock_housing_age(self, state: str, county: str) -> pd.DataFrame:
        """Return mock housing age data."""
        return pd.DataFrame([{
            "name": f"{county or 'Baldwin'} County, {state}",
            "total_housing": 110000,
            "built_2010_later": 25000,
            "built_2000_2009": 30000,
            "built_1990_1999": 20000,
            "built_1980_1989": 15000,
            "built_1970_1979": 10000,
            "built_pre_1970": 10000,
            "median_year_built": 2001,
        }])

    def get_income_demographics(
        self,
        state: str,
        county: str = None,
        year: int = 2022,
    ) -> pd.DataFrame:
        """Get income and demographic data."""
        state_fips = get_state_fips(state)
        if not state_fips:
            return self._get_mock_demographics(state, county)

        endpoint = f"{year}/acs/acs5"
        params = {
            "get": "NAME,B19013_001E,B17001_001E,B17001_002E",  # Median income, poverty
            "for": "county:*",
            "in": f"state:{state_fips}",
        }

        data = self._make_request(endpoint, params)

        if not data or len(data) < 2:
            return self._get_mock_demographics(state, county)

        headers = data[0]
        rows = data[1:]
        df = pd.DataFrame(rows, columns=headers)

        df = df.rename(columns={
            "B19013_001E": "median_household_income",
            "B17001_001E": "total_for_poverty",
            "B17001_002E": "below_poverty",
        })

        for col in ["median_household_income", "total_for_poverty", "below_poverty"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        if "total_for_poverty" in df.columns and "below_poverty" in df.columns:
            df["poverty_rate"] = df["below_poverty"] / df["total_for_poverty"] * 100

        return df

    def _get_mock_demographics(self, state: str, county: str) -> pd.DataFrame:
        """Return mock demographic data."""
        return pd.DataFrame([{
            "name": f"{county or 'Baldwin'} County, {state}",
            "median_household_income": 62500,
            "poverty_rate": 10.5,
            "total_for_poverty": 220000,
            "below_poverty": 23100,
        }])

    def get_environmental_justice_indicators(
        self,
        state: str,
        county: str = None,
    ) -> pd.DataFrame:
        """Get environmental justice related indicators."""
        # Combine multiple data sources
        pop_df = self.get_population(state, county)
        income_df = self.get_income_demographics(state, county)
        housing_df = self.get_housing_age(state, county)

        # Merge and calculate EJ indicators
        result = {
            "area": f"{county or 'State'}, {state}",
            "population": pop_df["population"].iloc[0] if not pop_df.empty else None,
            "median_income": income_df["median_household_income"].iloc[0] if not income_df.empty else None,
            "poverty_rate": income_df["poverty_rate"].iloc[0] if "poverty_rate" in income_df.columns else None,
        }

        return pd.DataFrame([result])
