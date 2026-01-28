"""Unified data access layer for ClimateBud."""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import pandas as pd

from .epa_client import EPAClient
from .noaa_client import NOAAClient
from .census_client import CensusClient
from utils.cache import Cache


class DataManager:
    """Unified interface for all data sources."""

    def __init__(self):
        self.epa = EPAClient()
        self.noaa = NOAAClient()
        self.census = CensusClient()
        self.cache = Cache()

    def get_environmental_data(
        self,
        state: str,
        county: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        data_types: List[str] = None,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch comprehensive environmental data for an area.

        Args:
            state: State abbreviation (e.g., 'AL')
            county: County name (e.g., 'Baldwin')
            start_date: Start of date range
            end_date: End of date range
            data_types: List of data types to fetch
                       Options: 'violations', 'facilities', 'weather', 'demographics'

        Returns:
            Dictionary of DataFrames for each data type
        """
        if not start_date:
            start_date = datetime.now() - timedelta(days=365 * 3)
        if not end_date:
            end_date = datetime.now()

        data_types = data_types or ["violations", "facilities", "weather", "demographics"]
        results = {}

        if "violations" in data_types:
            results["violations"] = self.epa.get_violations(
                state=state,
                county=county,
                start_date=start_date,
                end_date=end_date,
            )

        if "facilities" in data_types:
            results["facilities"] = self.epa.get_facilities(
                state=state,
                county=county,
            )

        if "weather" in data_types:
            results["precipitation"] = self.noaa.get_precipitation(
                location_fips=self._get_location_fips(state, county),
                start_date=start_date,
                end_date=end_date,
            )
            results["temperature"] = self.noaa.get_temperature(
                location_fips=self._get_location_fips(state, county),
                start_date=start_date,
                end_date=end_date,
            )
            results["weather_events"] = self.noaa.get_weather_events(
                state=state,
                start_date=start_date,
                end_date=end_date,
            )

        if "demographics" in data_types:
            results["population"] = self.census.get_population(state, county)
            results["income"] = self.census.get_income_demographics(state, county)
            results["housing"] = self.census.get_housing_age(state, county)

        return results

    def get_spill_data(
        self,
        state: str,
        county: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """Get sewage spill/SSO data specifically."""
        violations = self.epa.get_violations(
            state=state,
            county=county,
            start_date=start_date,
            end_date=end_date,
        )

        # Filter for SSO events
        if not violations.empty and "violation_type" in violations.columns:
            spills = violations[
                violations["violation_type"].str.contains("SSO|Overflow|Spill", case=False, na=False)
            ].copy()
            return spills

        return violations

    def get_repeat_violators(
        self,
        state: str,
        county: str = None,
        min_violations: int = 3,
    ) -> pd.DataFrame:
        """Identify facilities with repeated violations."""
        violations = self.epa.get_violations(
            state=state,
            county=county,
            start_date=datetime.now() - timedelta(days=365 * 3),
            end_date=datetime.now(),
        )

        if violations.empty:
            return pd.DataFrame()

        # Count violations per facility
        violation_counts = violations.groupby("facility_name").agg({
            "violation_date": "count",
            "latitude": "first",
            "longitude": "first",
            "violation_type": lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Unknown",
        }).reset_index()

        violation_counts = violation_counts.rename(columns={
            "violation_date": "violation_count",
            "violation_type": "most_common_violation",
        })

        # Filter for repeat violators
        repeat_violators = violation_counts[
            violation_counts["violation_count"] >= min_violations
        ].sort_values("violation_count", ascending=False)

        return repeat_violators

    def get_weather_correlation_data(
        self,
        state: str,
        county: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
    ) -> pd.DataFrame:
        """Get combined violation and weather data for correlation analysis."""
        if not start_date:
            start_date = datetime.now() - timedelta(days=365 * 2)
        if not end_date:
            end_date = datetime.now()

        # Get violations
        violations = self.epa.get_violations(
            state=state,
            county=county,
            start_date=start_date,
            end_date=end_date,
        )

        # Get precipitation
        precip = self.noaa.get_precipitation(
            location_fips=self._get_location_fips(state, county),
            start_date=start_date,
            end_date=end_date,
        )

        if violations.empty or precip.empty:
            return pd.DataFrame()

        # Convert dates
        violations["date"] = pd.to_datetime(violations["violation_date"])
        precip["date"] = pd.to_datetime(precip["date"])

        # Aggregate violations by date
        daily_violations = violations.groupby(
            violations["date"].dt.date
        ).size().reset_index(name="violation_count")
        daily_violations["date"] = pd.to_datetime(daily_violations["date"])

        # Merge with precipitation
        merged = pd.merge(
            precip[["date", "precipitation_inches"]],
            daily_violations,
            on="date",
            how="left",
        )
        merged["violation_count"] = merged["violation_count"].fillna(0)

        # Add rolling precipitation (last 3 days)
        merged["precip_3day"] = merged["precipitation_inches"].rolling(window=3).sum()

        return merged

    def _get_location_fips(self, state: str, county: str = None) -> str:
        """Get FIPS code for a location."""
        from utils.helpers import get_state_fips, get_county_fips

        if county:
            fips = get_county_fips(state, county)
            if fips:
                return fips

        state_fips = get_state_fips(state)
        return state_fips or "01"

    def search_facilities(
        self,
        query: str,
        state: str = None,
        limit: int = 50,
    ) -> pd.DataFrame:
        """Search for facilities by name or location."""
        facilities = self.epa.get_facilities(state=state, rows=limit * 2)

        if facilities.empty:
            return pd.DataFrame()

        # Filter by query
        if "facility_name" in facilities.columns:
            mask = facilities["facility_name"].str.contains(query, case=False, na=False)
            return facilities[mask].head(limit)

        return facilities.head(limit)

    def get_summary_statistics(
        self,
        state: str,
        county: str = None,
    ) -> Dict[str, Any]:
        """Get summary statistics for an area."""
        data = self.get_environmental_data(
            state=state,
            county=county,
            data_types=["violations", "facilities", "demographics"],
        )

        stats = {
            "total_violations": len(data.get("violations", [])),
            "total_facilities": len(data.get("facilities", [])),
        }

        violations = data.get("violations", pd.DataFrame())
        if not violations.empty:
            if "violation_type" in violations.columns:
                stats["violation_types"] = violations["violation_type"].value_counts().to_dict()
            if "severity" in violations.columns:
                stats["severity_breakdown"] = violations["severity"].value_counts().to_dict()

        pop = data.get("population", pd.DataFrame())
        if not pop.empty and "population" in pop.columns:
            stats["population"] = int(pop["population"].iloc[0])

        return stats
