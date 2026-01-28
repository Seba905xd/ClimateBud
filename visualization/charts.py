"""Plotly chart generators for data visualization."""

from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import config


class ChartGenerator:
    """Generate interactive Plotly charts for environmental data."""

    def __init__(self):
        self.template = config.PLOTLY_TEMPLATE
        self.colors = {
            "primary": "#1f77b4",
            "secondary": "#ff7f0e",
            "success": "#2ca02c",
            "danger": "#d62728",
            "warning": "#ffbb00",
            "info": "#17becf",
        }

    def create_time_series(
        self,
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        title: str = "Time Series",
        color: str = None,
        show_trend: bool = True,
    ) -> go.Figure:
        """Create a time series line chart."""
        df = df.copy()
        df[date_col] = pd.to_datetime(df[date_col])
        df = df.sort_values(date_col)

        fig = go.Figure()

        # Main line
        fig.add_trace(
            go.Scatter(
                x=df[date_col],
                y=df[value_col],
                mode="lines+markers",
                name=value_col,
                line=dict(color=color or self.colors["primary"], width=2),
                marker=dict(size=6),
            )
        )

        # Add trend line if requested
        if show_trend and len(df) > 2:
            try:
                df["x_numeric"] = range(len(df))
                z = np.polyfit(df["x_numeric"], df[value_col], 1)
                p = np.poly1d(z)
                trend_y = p(df["x_numeric"])

                fig.add_trace(
                    go.Scatter(
                        x=df[date_col],
                        y=trend_y,
                        mode="lines",
                        name="Trend",
                        line=dict(color=self.colors["secondary"], dash="dash"),
                    )
                )
            except Exception:
                pass  # Skip trend line if calculation fails

        fig.update_layout(
            title=title,
            xaxis_title="Date",
            yaxis_title=value_col,
            template=self.template,
            hovermode="x unified",
        )

        return fig

    def create_violation_trend(
        self,
        violations: pd.DataFrame,
        aggregation: str = "month",
    ) -> go.Figure:
        """Create a time series of violation counts."""
        if violations.empty:
            return self._empty_chart("No violation data available")

        violations = violations.copy()
        violations["date"] = pd.to_datetime(violations["violation_date"])

        # Aggregate by time period
        if aggregation == "month":
            violations["period"] = violations["date"].dt.to_period("M").astype(str)
        elif aggregation == "quarter":
            violations["period"] = violations["date"].dt.to_period("Q").astype(str)
        elif aggregation == "year":
            violations["period"] = violations["date"].dt.to_period("Y").astype(str)
        else:
            violations["period"] = violations["date"].dt.to_period("W").astype(str)

        counts = violations.groupby("period").size().reset_index(name="count")
        counts["period_date"] = pd.to_datetime(counts["period"])

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=counts["period"],
                y=counts["count"],
                marker_color=self.colors["primary"],
                name="Violations",
            )
        )

        fig.update_layout(
            title=f"Violations by {aggregation.title()}",
            xaxis_title="Period",
            yaxis_title="Number of Violations",
            template=self.template,
        )

        return fig

    def create_bar_chart(
        self,
        df: pd.DataFrame,
        x_col: str,
        y_col: str,
        title: str = "Bar Chart",
        orientation: str = "v",
        color_col: str = None,
    ) -> go.Figure:
        """Create a bar chart."""
        if df.empty:
            return self._empty_chart("No data available")

        if orientation == "h":
            fig = px.bar(
                df,
                y=x_col,
                x=y_col,
                orientation="h",
                color=color_col,
                title=title,
                template=self.template,
            )
        else:
            fig = px.bar(
                df,
                x=x_col,
                y=y_col,
                color=color_col,
                title=title,
                template=self.template,
            )

        return fig

    def create_top_violators_chart(
        self,
        violators: pd.DataFrame,
        top_n: int = 10,
    ) -> go.Figure:
        """Create a horizontal bar chart of top violators."""
        if violators.empty:
            return self._empty_chart("No violator data available")

        top = violators.nlargest(top_n, "violation_count")

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                y=top["facility_name"],
                x=top["violation_count"],
                orientation="h",
                marker_color=self.colors["danger"],
            )
        )

        fig.update_layout(
            title=f"Top {top_n} Facilities by Violation Count",
            xaxis_title="Number of Violations",
            yaxis_title="Facility",
            template=self.template,
            height=max(400, top_n * 40),
            yaxis=dict(autorange="reversed"),
        )

        return fig

    def create_severity_pie(
        self,
        violations: pd.DataFrame,
    ) -> go.Figure:
        """Create a pie chart of violation severity distribution."""
        if violations.empty or "severity" not in violations.columns:
            return self._empty_chart("No severity data available")

        severity_counts = violations["severity"].value_counts()

        colors = {
            "high": self.colors["danger"],
            "medium": self.colors["warning"],
            "low": self.colors["success"],
            "unknown": "#808080",
        }

        fig = go.Figure(
            data=[
                go.Pie(
                    labels=severity_counts.index,
                    values=severity_counts.values,
                    marker_colors=[colors.get(s.lower(), "#808080") for s in severity_counts.index],
                    hole=0.4,
                )
            ]
        )

        fig.update_layout(
            title="Violations by Severity",
            template=self.template,
        )

        return fig

    def create_violation_type_chart(
        self,
        violations: pd.DataFrame,
    ) -> go.Figure:
        """Create a bar chart of violation types."""
        if violations.empty or "violation_type" not in violations.columns:
            return self._empty_chart("No violation type data available")

        type_counts = violations["violation_type"].value_counts().head(10)

        fig = go.Figure()

        fig.add_trace(
            go.Bar(
                x=type_counts.values,
                y=type_counts.index,
                orientation="h",
                marker_color=self.colors["info"],
            )
        )

        fig.update_layout(
            title="Violations by Type",
            xaxis_title="Count",
            yaxis_title="Violation Type",
            template=self.template,
            height=max(300, len(type_counts) * 35),
            yaxis=dict(autorange="reversed"),
        )

        return fig

    def create_weather_correlation_scatter(
        self,
        data: pd.DataFrame,
        precip_col: str = "precipitation_inches",
        violation_col: str = "violation_count",
    ) -> go.Figure:
        """Create a scatter plot of weather vs violations."""
        if data.empty:
            return self._empty_chart("No correlation data available")

        # Filter to days with some precipitation
        plot_data = data[data[precip_col] > 0].copy()

        if plot_data.empty:
            return self._empty_chart("No precipitation data available")

        fig = px.scatter(
            plot_data,
            x=precip_col,
            y=violation_col,
            trendline="ols",
            title="Precipitation vs Violations",
            labels={
                precip_col: "Precipitation (inches)",
                violation_col: "Number of Violations",
            },
            template=self.template,
        )

        fig.update_traces(marker=dict(size=8, opacity=0.6))

        return fig

    def create_weather_timeline(
        self,
        weather: pd.DataFrame,
        violations: pd.DataFrame,
    ) -> go.Figure:
        """Create a combined timeline of weather and violations."""
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.1,
            subplot_titles=("Daily Precipitation", "Daily Violations"),
        )

        # Weather data
        if not weather.empty and "precipitation_inches" in weather.columns:
            weather = weather.copy()
            weather["date"] = pd.to_datetime(weather["date"])
            weather = weather.sort_values("date")

            fig.add_trace(
                go.Bar(
                    x=weather["date"],
                    y=weather["precipitation_inches"],
                    name="Precipitation",
                    marker_color=self.colors["info"],
                ),
                row=1,
                col=1,
            )

        # Violations data
        if not violations.empty and "violation_date" in violations.columns:
            violations = violations.copy()
            violations["date"] = pd.to_datetime(violations["violation_date"])
            daily_counts = violations.groupby(
                violations["date"].dt.date
            ).size().reset_index(name="count")
            daily_counts["date"] = pd.to_datetime(daily_counts["date"])

            fig.add_trace(
                go.Scatter(
                    x=daily_counts["date"],
                    y=daily_counts["count"],
                    name="Violations",
                    mode="lines+markers",
                    line=dict(color=self.colors["danger"]),
                ),
                row=2,
                col=1,
            )

        fig.update_layout(
            title="Weather and Violations Timeline",
            template=self.template,
            height=500,
            showlegend=True,
        )

        fig.update_yaxes(title_text="Inches", row=1, col=1)
        fig.update_yaxes(title_text="Count", row=2, col=1)

        return fig

    def create_monthly_heatmap(
        self,
        violations: pd.DataFrame,
    ) -> go.Figure:
        """Create a heatmap of violations by month and year."""
        if violations.empty or "violation_date" not in violations.columns:
            return self._empty_chart("No violation data available")

        violations = violations.copy()
        violations["date"] = pd.to_datetime(violations["violation_date"])
        violations["year"] = violations["date"].dt.year
        violations["month"] = violations["date"].dt.month

        # Create pivot table
        pivot = violations.groupby(["year", "month"]).size().unstack(fill_value=0)

        # Ensure all months are present
        for m in range(1, 13):
            if m not in pivot.columns:
                pivot[m] = 0
        pivot = pivot[sorted(pivot.columns)]

        month_names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        fig = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=month_names,
                y=pivot.index,
                colorscale="Reds",
                hoverongaps=False,
            )
        )

        fig.update_layout(
            title="Violations by Month and Year",
            xaxis_title="Month",
            yaxis_title="Year",
            template=self.template,
        )

        return fig

    def create_correlation_heatmap(
        self,
        correlation_matrix: pd.DataFrame,
    ) -> go.Figure:
        """Create a correlation heatmap."""
        if correlation_matrix.empty:
            return self._empty_chart("No correlation data available")

        fig = go.Figure(
            data=go.Heatmap(
                z=correlation_matrix.values,
                x=correlation_matrix.columns,
                y=correlation_matrix.index,
                colorscale="RdBu",
                zmid=0,
            )
        )

        fig.update_layout(
            title="Correlation Matrix",
            template=self.template,
        )

        return fig

    def _empty_chart(self, message: str) -> go.Figure:
        """Create an empty chart with a message."""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="gray"),
        )
        fig.update_layout(
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False),
            template=self.template,
        )
        return fig
