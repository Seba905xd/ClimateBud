"""Folium map generators for geographic visualization."""

from typing import List, Dict, Any, Optional
import pandas as pd
import folium
from folium import plugins

import config


class MapGenerator:
    """Generate interactive maps for environmental data."""

    def __init__(self):
        self.default_center = config.MAP_DEFAULT_CENTER
        self.default_zoom = config.MAP_DEFAULT_ZOOM

    def create_base_map(
        self,
        center: List[float] = None,
        zoom: int = None,
    ) -> folium.Map:
        """Create a base Folium map."""
        center = center or self.default_center
        zoom = zoom or self.default_zoom

        m = folium.Map(
            location=center,
            zoom_start=zoom,
            tiles="cartodbpositron",
        )

        # Add layer control
        folium.LayerControl().add_to(m)

        return m

    def create_violation_map(
        self,
        violations: pd.DataFrame,
        center: List[float] = None,
        show_heatmap: bool = True,
    ) -> folium.Map:
        """Create a map showing violation locations."""
        # Calculate center from data if not provided
        if center is None and not violations.empty:
            valid = violations.dropna(subset=["latitude", "longitude"])
            if not valid.empty:
                center = [valid["latitude"].mean(), valid["longitude"].mean()]

        m = self.create_base_map(center=center)

        if violations.empty:
            return m

        # Add markers layer
        marker_cluster = plugins.MarkerCluster(name="Violations")

        for _, row in violations.iterrows():
            if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
                continue

            # Determine marker color based on severity
            severity = row.get("severity", "unknown").lower()
            color = self._severity_to_color(severity)

            # Create popup content
            popup_html = self._create_violation_popup(row)

            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=8,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(marker_cluster)

        marker_cluster.add_to(m)

        # Add heatmap layer
        if show_heatmap:
            heat_data = [
                [row["latitude"], row["longitude"]]
                for _, row in violations.iterrows()
                if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude"))
            ]

            if heat_data:
                plugins.HeatMap(
                    heat_data,
                    name="Density Heatmap",
                    min_opacity=0.3,
                    radius=15,
                    blur=10,
                ).add_to(m)

        # Add legend
        self._add_legend(m)

        return m

    def create_facility_map(
        self,
        facilities: pd.DataFrame,
        violations: pd.DataFrame = None,
        center: List[float] = None,
    ) -> folium.Map:
        """Create a map showing facility locations with violation counts."""
        if center is None and not facilities.empty:
            valid = facilities.dropna(subset=["latitude", "longitude"])
            if not valid.empty:
                center = [valid["latitude"].mean(), valid["longitude"].mean()]

        m = self.create_base_map(center=center)

        if facilities.empty:
            return m

        # Count violations per facility if provided
        violation_counts = {}
        if violations is not None and not violations.empty:
            if "facility_name" in violations.columns:
                violation_counts = violations["facility_name"].value_counts().to_dict()

        # Add facility markers
        for _, row in facilities.iterrows():
            if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
                continue

            facility_name = row.get("facility_name", "Unknown Facility")
            count = violation_counts.get(facility_name, 0)

            # Size and color based on violation count
            if count >= 10:
                color = "#FF0000"
                radius = 15
            elif count >= 5:
                color = "#FFA500"
                radius = 12
            elif count >= 1:
                color = "#FFFF00"
                radius = 9
            else:
                color = "#00FF00"
                radius = 6

            popup_html = self._create_facility_popup(row, count)

            folium.CircleMarker(
                location=[row["latitude"], row["longitude"]],
                radius=radius,
                color=color,
                fill=True,
                fillColor=color,
                fillOpacity=0.7,
                popup=folium.Popup(popup_html, max_width=300),
            ).add_to(m)

        return m

    def create_hotspot_map(
        self,
        hotspots: List[Dict[str, Any]],
        violations: pd.DataFrame = None,
        center: List[float] = None,
    ) -> folium.Map:
        """Create a map highlighting violation hotspots."""
        m = self.create_base_map(center=center)

        # Add violation points if provided
        if violations is not None and not violations.empty:
            heat_data = [
                [row["latitude"], row["longitude"]]
                for _, row in violations.iterrows()
                if pd.notna(row.get("latitude")) and pd.notna(row.get("longitude"))
            ]

            if heat_data:
                plugins.HeatMap(
                    heat_data,
                    name="Incident Density",
                    min_opacity=0.4,
                    radius=20,
                    blur=15,
                ).add_to(m)

        # Add hotspot markers
        for i, hotspot in enumerate(hotspots, 1):
            if "lat" not in hotspot or "lon" not in hotspot:
                continue

            folium.Marker(
                location=[hotspot["lat"], hotspot["lon"]],
                popup=f"Hotspot #{i}: {hotspot.get('count', 'N/A')} incidents<br>{hotspot.get('name', '')}",
                icon=folium.Icon(color="red", icon="warning-sign", prefix="glyphicon"),
            ).add_to(m)

            # Add circle around hotspot
            folium.Circle(
                location=[hotspot["lat"], hotspot["lon"]],
                radius=500,  # meters
                color="red",
                fill=True,
                fillOpacity=0.2,
            ).add_to(m)

        return m

    def create_time_animated_map(
        self,
        violations: pd.DataFrame,
        center: List[float] = None,
    ) -> folium.Map:
        """Create a map with time-based animation of violations."""
        m = self.create_base_map(center=center)

        if violations.empty or "violation_date" not in violations.columns:
            return m

        # Prepare data for time slider
        violations = violations.copy()
        violations["date"] = pd.to_datetime(violations["violation_date"])
        violations = violations.dropna(subset=["latitude", "longitude", "date"])

        if violations.empty:
            return m

        # Group by month
        violations["month"] = violations["date"].dt.to_period("M").astype(str)

        features = []
        for _, row in violations.iterrows():
            feature = {
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [row["longitude"], row["latitude"]],
                },
                "properties": {
                    "time": row["month"],
                    "popup": f"{row.get('facility_name', 'Unknown')}<br>{row['date'].strftime('%Y-%m-%d')}",
                    "style": {"color": self._severity_to_color(row.get("severity", "unknown"))},
                },
            }
            features.append(feature)

        # Add TimestampedGeoJson
        plugins.TimestampedGeoJson(
            {
                "type": "FeatureCollection",
                "features": features,
            },
            period="P1M",
            add_last_point=True,
            auto_play=False,
            loop=False,
            max_speed=5,
        ).add_to(m)

        return m

    def _severity_to_color(self, severity: str) -> str:
        """Convert severity level to marker color."""
        colors = {
            "high": "#FF0000",
            "medium": "#FFA500",
            "low": "#FFFF00",
            "unknown": "#808080",
        }
        return colors.get(severity.lower(), colors["unknown"])

    def _create_violation_popup(self, row: pd.Series) -> str:
        """Create HTML popup for violation marker."""
        html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px;">
            <b>{row.get('facility_name', 'Unknown Facility')}</b><br>
            <hr style="margin: 5px 0;">
            <b>Date:</b> {row.get('violation_date', 'N/A')}<br>
            <b>Type:</b> {row.get('violation_type', 'N/A')}<br>
            <b>Severity:</b> {row.get('severity', 'N/A')}<br>
        """

        if pd.notna(row.get("volume_gallons")):
            html += f"<b>Volume:</b> {int(row['volume_gallons']):,} gallons<br>"

        if pd.notna(row.get("parameter")):
            html += f"<b>Parameter:</b> {row['parameter']}<br>"

        html += "</div>"
        return html

    def _create_facility_popup(self, row: pd.Series, violation_count: int) -> str:
        """Create HTML popup for facility marker."""
        html = f"""
        <div style="font-family: Arial, sans-serif; font-size: 12px;">
            <b>{row.get('facility_name', 'Unknown Facility')}</b><br>
            <hr style="margin: 5px 0;">
            <b>Violations:</b> {violation_count}<br>
            <b>City:</b> {row.get('city', 'N/A')}<br>
            <b>Status:</b> {row.get('permit_status', 'N/A')}<br>
        """

        if pd.notna(row.get("compliance_status")):
            html += f"<b>Compliance:</b> {row['compliance_status']}<br>"

        html += "</div>"
        return html

    def _add_legend(self, m: folium.Map) -> None:
        """Add a legend to the map."""
        legend_html = """
        <div style="
            position: fixed;
            bottom: 50px;
            left: 50px;
            z-index: 1000;
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            border: 2px solid gray;
            font-family: Arial, sans-serif;
            font-size: 12px;
        ">
            <b>Severity</b><br>
            <i style="background: #FF0000; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> High<br>
            <i style="background: #FFA500; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> Medium<br>
            <i style="background: #FFFF00; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> Low<br>
            <i style="background: #808080; width: 12px; height: 12px; display: inline-block; border-radius: 50%;"></i> Unknown
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
