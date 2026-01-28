"""AI-powered insight generation for environmental analysis."""

import json
from typing import Dict, Any, List
from openai import OpenAI

import config


class InsightGenerator:
    """Generate human-readable insights from analysis results."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = config.OPENAI_MODEL

    def generate_insights(
        self,
        analysis_results: Dict[str, Any],
        query_type: str,
        location: Dict[str, str],
    ) -> Dict[str, Any]:
        """Generate insights from analysis results."""
        if not self.client:
            return self._fallback_insights(analysis_results, query_type, location)

        system_prompt = """You are an environmental data analyst providing insights for non-technical users.
Based on the analysis results provided, generate clear, actionable insights.

Your response should be in JSON format with these sections:
{
    "summary": "A 2-3 sentence plain English summary of the key findings",
    "key_findings": ["List of 3-5 specific findings from the data"],
    "patterns": ["List of 2-3 patterns or trends identified"],
    "concerns": ["List of 1-3 areas of concern, if any"],
    "recommendations": ["List of 2-4 actionable recommendations"],
    "context": "Brief context about what this data means for the community"
}

Guidelines:
- Use plain, non-technical language
- Be specific with numbers and locations when available
- Focus on actionable insights
- Highlight both positive and negative findings
- Make recommendations practical and specific to the location"""

        user_prompt = f"""Analyze these environmental data results for {location.get('county', 'the')} County, {location.get('state', '')}.

Query type: {query_type}

Analysis results:
{json.dumps(analysis_results, indent=2, default=str)}

Generate insights in JSON format."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                response_format={"type": "json_object"},
            )

            insights = json.loads(response.choices[0].message.content)
            return insights

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_insights(analysis_results, query_type, location)

    def _fallback_insights(
        self,
        results: Dict[str, Any],
        query_type: str,
        location: Dict[str, str],
    ) -> Dict[str, Any]:
        """Generate basic insights without AI."""
        county = location.get("county", "the area")
        state = location.get("state", "")

        insights = {
            "summary": "",
            "key_findings": [],
            "patterns": [],
            "concerns": [],
            "recommendations": [],
            "context": "",
        }

        # Generate insights based on query type
        if query_type == "spill_analysis":
            insights = self._spill_insights(results, county, state)
        elif query_type == "repeat_violators":
            insights = self._violator_insights(results, county, state)
        elif query_type == "weather_correlation":
            insights = self._weather_insights(results, county, state)
        else:
            insights = self._general_insights(results, county, state)

        return insights

    def _spill_insights(self, results: Dict, county: str, state: str) -> Dict[str, Any]:
        """Generate insights for spill analysis."""
        total = results.get("total_incidents", 0)
        temporal = results.get("temporal", {})
        by_facility = results.get("by_facility", {})

        insights = {
            "summary": f"Analysis found {total} environmental incidents in {county} County, {state}.",
            "key_findings": [],
            "patterns": [],
            "concerns": [],
            "recommendations": [],
            "context": f"These incidents can impact water quality and public health in {county} County.",
        }

        # Add findings
        if total > 0:
            insights["key_findings"].append(f"Total of {total} incidents recorded in the analysis period")

        if by_facility:
            top_count = by_facility.get("repeat_violator_count", 0)
            if top_count > 0:
                insights["key_findings"].append(f"{top_count} facilities have multiple incidents")

            top_violators = by_facility.get("top_violators", {})
            if top_violators:
                top_name = list(top_violators.keys())[0]
                top_incidents = list(top_violators.values())[0]
                insights["key_findings"].append(f"Highest: {top_name} with {top_incidents} incidents")

        # Add patterns
        if temporal:
            peak_month = temporal.get("peak_month")
            if peak_month:
                month_names = ["", "January", "February", "March", "April", "May", "June",
                             "July", "August", "September", "October", "November", "December"]
                insights["patterns"].append(f"Peak incidents occur in {month_names[peak_month]}")

            trend = temporal.get("trend", "stable")
            if trend == "increasing":
                insights["patterns"].append("Incident rate is trending upward")
                insights["concerns"].append("Rising incident trend requires attention")
            elif trend == "decreasing":
                insights["patterns"].append("Incident rate is trending downward")

        # Add recommendations
        insights["recommendations"] = [
            "Monitor facilities with multiple incidents more closely",
            "Consider increased inspections during peak incident months",
            "Review infrastructure maintenance schedules for problem areas",
        ]

        return insights

    def _violator_insights(self, results: Dict, county: str, state: str) -> Dict[str, Any]:
        """Generate insights for repeat violator analysis."""
        chronic = results.get("chronic_violators", 0)
        repeat = results.get("repeat_violators", 0)
        top_violators = results.get("top_violators", [])

        insights = {
            "summary": f"Analysis identified {chronic} chronic and {repeat} repeat violators in {county} County.",
            "key_findings": [],
            "patterns": [],
            "concerns": [],
            "recommendations": [],
            "context": "Repeat violations often indicate systemic issues requiring infrastructure investment.",
        }

        if chronic > 0:
            insights["key_findings"].append(f"{chronic} facilities with 10+ violations (chronic violators)")
            insights["concerns"].append("Chronic violators need immediate intervention")

        if repeat > 0:
            insights["key_findings"].append(f"{repeat} facilities with 3-9 violations")

        if top_violators:
            top = top_violators[0]
            insights["key_findings"].append(
                f"Top violator: {top.get('facility_name', 'Unknown')} with {top.get('violation_count', 0)} violations"
            )

        insights["recommendations"] = [
            "Prioritize infrastructure upgrades for chronic violators",
            "Implement enhanced monitoring for repeat offenders",
            "Consider enforcement actions for non-responsive facilities",
            "Evaluate capacity issues at high-violation facilities",
        ]

        return insights

    def _weather_insights(self, results: Dict, county: str, state: str) -> Dict[str, Any]:
        """Generate insights for weather correlation analysis."""
        precip_corr = results.get("precipitation_correlation", {})
        threshold = results.get("threshold_analysis", {})

        insights = {
            "summary": f"Analysis examined weather-related patterns in {county} County violations.",
            "key_findings": [],
            "patterns": [],
            "concerns": [],
            "recommendations": [],
            "context": "Weather events, especially heavy rainfall, can overwhelm aging infrastructure.",
        }

        if precip_corr:
            coef = precip_corr.get("coefficient", 0)
            significant = precip_corr.get("significant", False)

            if significant and coef > 0.2:
                insights["key_findings"].append(
                    f"Significant correlation found (r={coef}) between rainfall and violations"
                )
                insights["patterns"].append("Violations increase with precipitation")
                insights["concerns"].append("Infrastructure may be vulnerable to wet weather")
            elif significant and coef < -0.2:
                insights["key_findings"].append("Violations decrease during rainy periods")
            else:
                insights["key_findings"].append("No strong correlation between rainfall and violations")

        if threshold:
            for key, value in threshold.items():
                if "above" in key and value.get("relative_risk", 1) > 1.5:
                    inches = key.split("_")[1]
                    risk = value["relative_risk"]
                    insights["patterns"].append(
                        f"Violation risk is {risk}x higher when rainfall exceeds {inches} inches"
                    )

        insights["recommendations"] = [
            "Increase monitoring during heavy rainfall events",
            "Consider infrastructure upgrades for wet weather capacity",
            "Develop rainfall-triggered inspection protocols",
            "Invest in stormwater management improvements",
        ]

        return insights

    def _general_insights(self, results: Dict, county: str, state: str) -> Dict[str, Any]:
        """Generate general overview insights."""
        return {
            "summary": f"Environmental overview for {county} County, {state}.",
            "key_findings": [
                f"Total incidents analyzed: {results.get('total_incidents', 'N/A')}",
            ],
            "patterns": ["Analysis in progress"],
            "concerns": [],
            "recommendations": [
                "Review specific analysis types for detailed insights",
                "Monitor facilities with compliance issues",
            ],
            "context": "This overview provides a starting point for detailed environmental analysis.",
        }

    def generate_report_summary(
        self,
        all_results: Dict[str, Any],
        location: Dict[str, str],
    ) -> str:
        """Generate a comprehensive report summary."""
        if not self.client:
            return self._fallback_report_summary(all_results, location)

        prompt = f"""Create a brief executive summary (3-4 paragraphs) for an environmental report on {location.get('county', '')} County, {location.get('state', '')}.

Data summary:
{json.dumps(all_results, indent=2, default=str)}

Write in clear, professional language suitable for local officials and community members."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=500,
            )
            return response.choices[0].message.content

        except Exception as e:
            return self._fallback_report_summary(all_results, location)

    def _fallback_report_summary(self, results: Dict, location: Dict) -> str:
        """Generate basic report summary without AI."""
        county = location.get("county", "the area")
        state = location.get("state", "")

        total_incidents = results.get("total_incidents", "multiple")

        return f"""Environmental Analysis Summary for {county} County, {state}

This report analyzes environmental compliance data including facility violations, sewage spills, and related incidents. The analysis covers {total_incidents} recorded incidents in the study period.

Key areas examined include violation patterns, repeat offenders, and correlations with weather events. The findings highlight opportunities for improved monitoring and infrastructure investment.

For detailed findings and recommendations, please review the specific analysis sections of this report."""
