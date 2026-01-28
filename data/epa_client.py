"""EPA ECHO API client for environmental compliance data."""

import requests
from datetime import datetime
from typing import Optional, List, Dict, Any
import pandas as pd

import config
from utils.cache import Cache


class EPAClient:
    """Client for EPA ECHO (Enforcement and Compliance History Online) API."""

    def __init__(self):
        self.base_url = "https://echodata.epa.gov/echo"
        self.cache = Cache()

    def _make_request(self, endpoint: str, params: Dict[str, Any]) -> Optional[Dict]:
        """Make a request to the EPA ECHO API."""
        url = f"{self.base_url}/{endpoint}"

        # Check cache first
        cache_key = f"epa_{endpoint}_{str(sorted(params.items()))}"
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
            print(f"EPA API error: {e}")
            return None

    def get_facilities(
        self,
        state: str = None,
        county: str = None,
        program: str = "CWA",  # Clean Water Act
        rows: int = 100,
    ) -> pd.DataFrame:
        """Get facilities with environmental permits."""
        params = {
            "output": "JSON",
            "p_act": "Y",  # Active facilities
            "responseset": rows,
        }

        if state:
            params["p_st"] = state
        if county:
            params["p_co"] = county

        # Use facility search endpoint
        endpoint = "cwa_rest_services.get_facilities"
        if program == "CWA":
            endpoint = "cwa_rest_services.get_facilities"
        elif program == "CAA":
            endpoint = "air_rest_services.get_facilities"

        data = self._make_request(endpoint, params)

        if not data or "Results" not in data:
            return pd.DataFrame()

        facilities = data.get("Results", {}).get("Facilities", [])
        if not facilities:
            return pd.DataFrame()

        df = pd.DataFrame(facilities)
        return self._normalize_facility_data(df)

    def _normalize_facility_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Normalize facility data columns."""
        column_mapping = {
            "CWPName": "facility_name",
            "FacLat": "latitude",
            "FacLong": "longitude",
            "CWPStreet": "address",
            "CWPCity": "city",
            "CWPState": "state",
            "CWPZip": "zip_code",
            "CWPCounty": "county",
            "RegistryID": "registry_id",
            "CWPPermitStatusDesc": "permit_status",
            "CWPSNCStatus": "compliance_status",
            "CWPQtrsWithNC": "quarters_noncompliance",
            "CWPInspectionCount": "inspection_count",
            "CWPFormalEaCount": "formal_enforcement_count",
        }

        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]

        # Convert coordinates to numeric
        for col in ["latitude", "longitude"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def get_violations(
        self,
        state: str = None,
        county: str = None,
        start_date: datetime = None,
        end_date: datetime = None,
        rows: int = 500,
    ) -> pd.DataFrame:
        """Get environmental violations/effluent exceedances."""
        params = {
            "output": "JSON",
            "responseset": rows,
        }

        if state:
            params["p_st"] = state
        if county:
            params["p_co"] = county
        if start_date:
            params["p_ysl"] = "5Y"  # Last 5 years

        # Get effluent chart data which includes violations
        endpoint = "eff_rest_services.get_effluent_chart"
        data = self._make_request(endpoint, params)

        if not data:
            return self._get_mock_violations(state, county, start_date, end_date)

        return self._parse_violations(data)

    def _parse_violations(self, data: Dict) -> pd.DataFrame:
        """Parse violation data from API response."""
        violations = []

        if "Results" in data and "Violations" in data["Results"]:
            for v in data["Results"]["Violations"]:
                violations.append({
                    "facility_name": v.get("FacilityName", "Unknown"),
                    "violation_date": v.get("ViolationDate"),
                    "violation_type": v.get("ViolationType", "Unknown"),
                    "parameter": v.get("Parameter", "Unknown"),
                    "limit_value": v.get("LimitValue"),
                    "actual_value": v.get("ActualValue"),
                    "exceedance_pct": v.get("ExceedancePct"),
                    "latitude": v.get("Latitude"),
                    "longitude": v.get("Longitude"),
                })

        return pd.DataFrame(violations)

    def _get_mock_violations(
        self,
        state: str,
        county: str,
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame:
        """Return mock violation data for demo purposes."""
        import numpy as np

        # Generate realistic mock data for Baldwin County, AL
        np.random.seed(42)
        n_violations = 150

        facilities = [
            ("Bay Minette WWTP", 30.8830, -87.7731),
            ("Foley WWTP", 30.4066, -87.6836),
            ("Fairhope WWTP", 30.5227, -87.9033),
            ("Gulf Shores WWTP", 30.2460, -87.7008),
            ("Daphne Utilities", 30.6035, -87.9036),
            ("Orange Beach WWTP", 30.2944, -87.5731),
            ("Loxley WWTP", 30.6177, -87.7528),
            ("Robertsdale WWTP", 30.5544, -87.7117),
        ]

        start = start_date or datetime(2021, 1, 1)
        end = end_date or datetime.now()
        date_range = (end - start).days

        violations = []
        for i in range(n_violations):
            facility = facilities[np.random.randint(0, len(facilities))]
            days_offset = np.random.randint(0, date_range)
            violation_date = start + pd.Timedelta(days=days_offset)

            # Weight violations more heavily during wet months
            month = violation_date.month
            if month in [3, 4, 5, 11, 12]:  # Wet season
                severity_weights = [0.3, 0.4, 0.3]  # more high severity
            else:
                severity_weights = [0.5, 0.35, 0.15]

            severity = np.random.choice(["low", "medium", "high"], p=severity_weights)

            violation_type = np.random.choice([
                "Effluent Limit Exceedance",
                "SSO - Sanitary Sewer Overflow",
                "Reporting Violation",
                "Permit Violation",
            ], p=[0.4, 0.35, 0.15, 0.1])

            # Set volume for SSO events
            if "SSO" in violation_type:
                volume = int(np.random.choice([
                    np.random.randint(100, 10000),
                    np.random.randint(10000, 100000),
                    np.random.randint(100000, 1000000),
                ], p=[0.5, 0.35, 0.15]))
            else:
                volume = None

            violations.append({
                "facility_name": facility[0],
                "latitude": facility[1] + np.random.uniform(-0.01, 0.01),
                "longitude": facility[2] + np.random.uniform(-0.01, 0.01),
                "violation_date": violation_date.strftime("%Y-%m-%d"),
                "violation_type": violation_type,
                "parameter": np.random.choice([
                    "Total Suspended Solids",
                    "BOD5",
                    "E. coli",
                    "Ammonia",
                    "Chlorine",
                    "pH",
                ]),
                "severity": severity,
                "volume_gallons": volume,
            })

        return pd.DataFrame(violations)

    def get_discharge_monitoring(
        self,
        facility_id: str = None,
        state: str = None,
        start_date: datetime = None,
        rows: int = 100,
    ) -> pd.DataFrame:
        """Get discharge monitoring report data."""
        params = {
            "output": "JSON",
            "responseset": rows,
        }

        if facility_id:
            params["p_pid"] = facility_id
        if state:
            params["p_st"] = state

        endpoint = "dmr_rest_services.get_dmrs"
        data = self._make_request(endpoint, params)

        if not data:
            return pd.DataFrame()

        return self._parse_dmr_data(data)

    def _parse_dmr_data(self, data: Dict) -> pd.DataFrame:
        """Parse discharge monitoring report data."""
        if "Results" not in data:
            return pd.DataFrame()

        records = data.get("Results", {}).get("DMRs", [])
        return pd.DataFrame(records)

    def get_enforcement_actions(
        self,
        state: str = None,
        county: str = None,
        rows: int = 100,
    ) -> pd.DataFrame:
        """Get enforcement actions for facilities."""
        params = {
            "output": "JSON",
            "responseset": rows,
        }

        if state:
            params["p_st"] = state
        if county:
            params["p_co"] = county

        endpoint = "case_rest_services.get_cases"
        data = self._make_request(endpoint, params)

        if not data:
            return pd.DataFrame()

        cases = data.get("Results", {}).get("Cases", [])
        return pd.DataFrame(cases)
