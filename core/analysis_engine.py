"""Statistical analysis engine for environmental data."""

from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np
from scipy import stats


class AnalysisEngine:
    """Perform statistical analysis on environmental data."""

    def analyze_spill_patterns(
        self,
        violations: pd.DataFrame,
        weather: pd.DataFrame = None,
    ) -> Dict[str, Any]:
        """Analyze patterns in spill/violation data."""
        if violations.empty:
            return {"error": "No violation data available"}

        results = {
            "total_incidents": len(violations),
            "date_range": self._get_date_range(violations),
        }

        # Temporal patterns
        if "violation_date" in violations.columns:
            violations["date"] = pd.to_datetime(violations["violation_date"])
            results["temporal"] = self._analyze_temporal_patterns(violations)

        # Spatial patterns
        if "latitude" in violations.columns and "longitude" in violations.columns:
            results["spatial"] = self._analyze_spatial_patterns(violations)

        # Severity distribution
        if "severity" in violations.columns:
            results["severity"] = violations["severity"].value_counts().to_dict()

        # Type distribution
        if "violation_type" in violations.columns:
            results["types"] = violations["violation_type"].value_counts().to_dict()

        # Facility analysis
        if "facility_name" in violations.columns:
            results["by_facility"] = self._analyze_by_facility(violations)

        return results

    def _get_date_range(self, df: pd.DataFrame) -> Dict[str, str]:
        """Get date range of data."""
        date_col = "violation_date" if "violation_date" in df.columns else "date"
        if date_col not in df.columns:
            return {}

        dates = pd.to_datetime(df[date_col])
        return {
            "start": dates.min().strftime("%Y-%m-%d"),
            "end": dates.max().strftime("%Y-%m-%d"),
        }

    def _analyze_temporal_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze temporal patterns in violations."""
        df = df.copy()
        df["month"] = df["date"].dt.month
        df["year"] = df["date"].dt.year
        df["day_of_week"] = df["date"].dt.dayofweek
        df["quarter"] = df["date"].dt.quarter

        return {
            "by_month": df.groupby("month").size().to_dict(),
            "by_year": df.groupby("year").size().to_dict(),
            "by_quarter": df.groupby("quarter").size().to_dict(),
            "peak_month": int(df.groupby("month").size().idxmax()),
            "trend": self._calculate_trend(df),
        }

    def _calculate_trend(self, df: pd.DataFrame) -> str:
        """Calculate if violations are increasing or decreasing."""
        monthly = df.groupby([df["date"].dt.to_period("M")]).size()
        if len(monthly) < 3:
            return "insufficient_data"

        x = np.arange(len(monthly))
        y = monthly.values

        slope, _, r_value, p_value, _ = stats.linregress(x, y)

        if p_value > 0.05:
            return "stable"
        elif slope > 0:
            return "increasing"
        else:
            return "decreasing"

    def _analyze_spatial_patterns(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze spatial clustering of violations."""
        valid_coords = df.dropna(subset=["latitude", "longitude"])

        if len(valid_coords) < 2:
            return {"clusters": []}

        center_lat = valid_coords["latitude"].mean()
        center_lon = valid_coords["longitude"].mean()

        # Simple clustering by proximity to center
        valid_coords = valid_coords.copy()
        valid_coords["distance_from_center"] = np.sqrt(
            (valid_coords["latitude"] - center_lat) ** 2 +
            (valid_coords["longitude"] - center_lon) ** 2
        )

        return {
            "center": {"lat": center_lat, "lon": center_lon},
            "spread": valid_coords["distance_from_center"].std(),
            "hotspots": self._identify_hotspots(valid_coords),
        }

    def _identify_hotspots(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """Identify geographic hotspots of violations."""
        if df.empty:
            return []

        # Group by rounded coordinates
        df = df.copy()
        df["lat_bin"] = (df["latitude"] * 100).round() / 100
        df["lon_bin"] = (df["longitude"] * 100).round() / 100

        hotspots = df.groupby(["lat_bin", "lon_bin"]).agg({
            "latitude": "mean",
            "longitude": "mean",
            "facility_name": "first" if "facility_name" in df.columns else "count",
        }).reset_index()

        hotspots["count"] = df.groupby(["lat_bin", "lon_bin"]).size().values

        # Return top 5 hotspots
        top_hotspots = hotspots.nlargest(5, "count")

        return [
            {
                "lat": row["latitude"],
                "lon": row["longitude"],
                "count": int(row["count"]),
                "name": row.get("facility_name", "Unknown"),
            }
            for _, row in top_hotspots.iterrows()
        ]

    def _analyze_by_facility(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze violations by facility."""
        facility_counts = df["facility_name"].value_counts()

        return {
            "total_facilities": len(facility_counts),
            "top_violators": facility_counts.head(10).to_dict(),
            "single_incident_facilities": int((facility_counts == 1).sum()),
            "repeat_violator_count": int((facility_counts > 1).sum()),
        }

    def analyze_weather_correlation(
        self,
        violations: pd.DataFrame,
        weather: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Analyze correlation between violations and weather."""
        if violations.empty or weather.empty:
            return {"error": "Insufficient data for correlation analysis"}

        # Prepare data
        violations = violations.copy()
        violations["date"] = pd.to_datetime(violations["violation_date"])

        # Count violations per day
        daily_violations = violations.groupby(
            violations["date"].dt.date
        ).size().reset_index(name="violation_count")
        daily_violations["date"] = pd.to_datetime(daily_violations["date"])

        # Merge with weather
        weather = weather.copy()
        weather["date"] = pd.to_datetime(weather["date"])

        merged = pd.merge(
            weather,
            daily_violations,
            on="date",
            how="left",
        )
        merged["violation_count"] = merged["violation_count"].fillna(0)

        results = {
            "data_points": len(merged),
        }

        # Calculate correlations
        if "precipitation_inches" in merged.columns:
            precip = merged["precipitation_inches"]
            violations_col = merged["violation_count"]

            # Remove NaN values
            valid_idx = ~(precip.isna() | violations_col.isna())
            if valid_idx.sum() > 10:
                corr, p_value = stats.pearsonr(
                    precip[valid_idx],
                    violations_col[valid_idx]
                )
                results["precipitation_correlation"] = {
                    "coefficient": round(corr, 3),
                    "p_value": round(p_value, 4),
                    "significant": p_value < 0.05,
                }

                # Add rolling window correlation
                merged["precip_3day"] = merged["precipitation_inches"].rolling(3).sum()
                valid_idx_3d = ~(merged["precip_3day"].isna() | violations_col.isna())
                if valid_idx_3d.sum() > 10:
                    corr_3d, p_3d = stats.pearsonr(
                        merged["precip_3day"][valid_idx_3d],
                        violations_col[valid_idx_3d]
                    )
                    results["precipitation_3day_correlation"] = {
                        "coefficient": round(corr_3d, 3),
                        "p_value": round(p_3d, 4),
                        "significant": p_3d < 0.05,
                    }

        # Threshold analysis
        if "precipitation_inches" in merged.columns:
            results["threshold_analysis"] = self._analyze_precipitation_thresholds(merged)

        return results

    def _analyze_precipitation_thresholds(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Analyze violation rates at different precipitation thresholds."""
        thresholds = [0.1, 0.5, 1.0, 2.0]
        results = {}

        for threshold in thresholds:
            above = df[df["precipitation_inches"] >= threshold]
            below = df[df["precipitation_inches"] < threshold]

            if len(above) > 0 and len(below) > 0:
                rate_above = above["violation_count"].mean()
                rate_below = below["violation_count"].mean()

                results[f"above_{threshold}_inches"] = {
                    "days": len(above),
                    "avg_violations": round(rate_above, 2),
                    "relative_risk": round(rate_above / max(rate_below, 0.01), 2),
                }

        return results

    def analyze_repeat_violators(
        self,
        violations: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Detailed analysis of repeat violators."""
        if violations.empty or "facility_name" not in violations.columns:
            return {"error": "No facility data available"}

        violations = violations.copy()
        violations["date"] = pd.to_datetime(violations["violation_date"])

        # Count by facility
        facility_stats = violations.groupby("facility_name").agg({
            "date": ["count", "min", "max"],
            "violation_type": lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else "Unknown",
            "latitude": "first",
            "longitude": "first",
        }).reset_index()

        facility_stats.columns = [
            "facility_name", "violation_count", "first_violation",
            "last_violation", "primary_violation_type", "latitude", "longitude"
        ]

        # Calculate days between first and last
        facility_stats["active_days"] = (
            facility_stats["last_violation"] - facility_stats["first_violation"]
        ).dt.days

        # Violation frequency
        facility_stats["violations_per_year"] = (
            facility_stats["violation_count"] /
            (facility_stats["active_days"] / 365).clip(lower=1)
        ).round(2)

        # Classify violators
        facility_stats["category"] = facility_stats["violation_count"].apply(
            lambda x: "chronic" if x >= 10 else ("repeat" if x >= 3 else "occasional")
        )

        return {
            "total_facilities": len(facility_stats),
            "chronic_violators": int((facility_stats["category"] == "chronic").sum()),
            "repeat_violators": int((facility_stats["category"] == "repeat").sum()),
            "occasional_violators": int((facility_stats["category"] == "occasional").sum()),
            "top_violators": facility_stats.nlargest(10, "violation_count").to_dict("records"),
            "highest_frequency": facility_stats.nlargest(5, "violations_per_year").to_dict("records"),
        }

    def generate_summary_stats(
        self,
        data: Dict[str, pd.DataFrame],
    ) -> Dict[str, Any]:
        """Generate comprehensive summary statistics."""
        summary = {}

        violations = data.get("violations", pd.DataFrame())
        if not violations.empty:
            summary["violations"] = {
                "total": len(violations),
                "unique_facilities": violations["facility_name"].nunique() if "facility_name" in violations.columns else 0,
            }

            if "severity" in violations.columns:
                summary["violations"]["by_severity"] = violations["severity"].value_counts().to_dict()

            if "violation_type" in violations.columns:
                summary["violations"]["by_type"] = violations["violation_type"].value_counts().to_dict()

        precip = data.get("precipitation", pd.DataFrame())
        if not precip.empty and "precipitation_inches" in precip.columns:
            summary["weather"] = {
                "total_rainfall_inches": round(precip["precipitation_inches"].sum(), 2),
                "avg_daily_rainfall": round(precip["precipitation_inches"].mean(), 3),
                "rainy_days": int((precip["precipitation_inches"] > 0.1).sum()),
                "heavy_rain_days": int((precip["precipitation_inches"] > 1.0).sum()),
            }

        population = data.get("population", pd.DataFrame())
        if not population.empty and "population" in population.columns:
            pop_value = population["population"].iloc[0]
            summary["demographics"] = {
                "population": int(pop_value) if pd.notna(pop_value) else None,
            }

            # Calculate per capita metrics if we have violations
            if summary.get("violations") and summary["demographics"]["population"]:
                summary["per_capita"] = {
                    "violations_per_100k": round(
                        summary["violations"]["total"] / summary["demographics"]["population"] * 100000, 2
                    ),
                }

        return summary
