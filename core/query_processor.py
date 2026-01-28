"""GPT-4 powered query processor for natural language understanding."""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from openai import OpenAI

import config


class QueryProcessor:
    """Process natural language queries into structured data requests."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or config.OPENAI_API_KEY
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = config.OPENAI_MODEL

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Parse a natural language query into structured parameters.

        Returns:
            Dictionary with:
            - query_type: Type of analysis requested
            - location: Geographic parameters
            - time_range: Date range for data
            - data_sources: Which APIs to query
            - visualization_type: Recommended visualization
            - filters: Any specific filters
        """
        if not self.client:
            return self._fallback_parse(query)

        system_prompt = """You are a query parser for an environmental data analysis system.
Parse the user's natural language query into structured parameters.

Available query types:
- spill_analysis: Analyze sewage spills/SSO events
- violation_trends: Show violation patterns over time
- repeat_violators: Find facilities with repeated violations
- weather_correlation: Correlate environmental issues with weather
- facility_search: Find specific facilities
- general_overview: General environmental summary

Available data sources:
- epa: EPA ECHO data (violations, facilities, compliance)
- noaa: Weather data (precipitation, temperature)
- census: Demographics and infrastructure

Visualization types:
- map: Geographic visualization
- time_series: Trend over time
- bar_chart: Comparison between categories
- scatter: Correlation plot
- heatmap: Density or correlation matrix
- combined: Multiple visualizations

Respond ONLY with valid JSON matching this schema:
{
    "query_type": "string",
    "location": {
        "state": "two-letter code or null",
        "county": "county name or null",
        "city": "city name or null"
    },
    "time_range": {
        "start_date": "YYYY-MM-DD or null",
        "end_date": "YYYY-MM-DD or null",
        "relative": "e.g., 'last 3 years' or null"
    },
    "data_sources": ["list of sources needed"],
    "visualization_type": "recommended viz type",
    "filters": {
        "violation_types": ["list or null"],
        "severity": ["list or null"],
        "facility_name": "string or null"
    },
    "original_query": "the original query"
}"""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": query},
                ],
                temperature=0.1,
                response_format={"type": "json_object"},
            )

            result = json.loads(response.choices[0].message.content)
            result = self._validate_and_enhance(result, query)
            return result

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return self._fallback_parse(query)

    def _validate_and_enhance(self, parsed: Dict, original_query: str) -> Dict:
        """Validate and enhance the parsed query."""
        # Ensure required fields
        parsed["original_query"] = original_query

        # Set defaults for location if not specified
        if not parsed.get("location"):
            parsed["location"] = {}
        if not parsed["location"].get("state"):
            parsed["location"]["state"] = config.DEFAULT_STATE
        if not parsed["location"].get("county"):
            parsed["location"]["county"] = config.DEFAULT_COUNTY

        # Parse relative time ranges
        time_range = parsed.get("time_range", {})
        if time_range.get("relative") and not time_range.get("start_date"):
            parsed["time_range"] = self._parse_relative_time(time_range["relative"])

        # Set default time range
        if not parsed.get("time_range") or not parsed["time_range"].get("start_date"):
            parsed["time_range"] = {
                "start_date": (datetime.now() - timedelta(days=365 * 3)).strftime("%Y-%m-%d"),
                "end_date": datetime.now().strftime("%Y-%m-%d"),
            }

        # Ensure data sources
        if not parsed.get("data_sources"):
            parsed["data_sources"] = self._infer_data_sources(parsed.get("query_type", "general_overview"))

        # Ensure visualization type
        if not parsed.get("visualization_type"):
            parsed["visualization_type"] = self._infer_visualization(parsed.get("query_type", "general_overview"))

        return parsed

    def _parse_relative_time(self, relative: str) -> Dict[str, str]:
        """Convert relative time expressions to dates."""
        relative = relative.lower()
        end_date = datetime.now()

        if "year" in relative:
            try:
                years = int("".join(filter(str.isdigit, relative)) or "1")
            except ValueError:
                years = 1
            start_date = end_date - timedelta(days=365 * years)
        elif "month" in relative:
            try:
                months = int("".join(filter(str.isdigit, relative)) or "1")
            except ValueError:
                months = 1
            start_date = end_date - timedelta(days=30 * months)
        elif "week" in relative:
            try:
                weeks = int("".join(filter(str.isdigit, relative)) or "1")
            except ValueError:
                weeks = 1
            start_date = end_date - timedelta(weeks=weeks)
        else:
            start_date = end_date - timedelta(days=365)

        return {
            "start_date": start_date.strftime("%Y-%m-%d"),
            "end_date": end_date.strftime("%Y-%m-%d"),
        }

    def _infer_data_sources(self, query_type: str) -> list:
        """Infer required data sources from query type."""
        source_map = {
            "spill_analysis": ["epa"],
            "violation_trends": ["epa"],
            "repeat_violators": ["epa"],
            "weather_correlation": ["epa", "noaa"],
            "facility_search": ["epa"],
            "general_overview": ["epa", "census"],
        }
        return source_map.get(query_type, ["epa"])

    def _infer_visualization(self, query_type: str) -> str:
        """Infer best visualization type from query type."""
        viz_map = {
            "spill_analysis": "combined",
            "violation_trends": "time_series",
            "repeat_violators": "bar_chart",
            "weather_correlation": "scatter",
            "facility_search": "map",
            "general_overview": "combined",
        }
        return viz_map.get(query_type, "combined")

    def _fallback_parse(self, query: str) -> Dict[str, Any]:
        """Fallback parsing when API is unavailable."""
        query_lower = query.lower()

        # Detect query type
        if any(word in query_lower for word in ["spill", "sso", "overflow", "sewage"]):
            query_type = "spill_analysis"
        elif any(word in query_lower for word in ["repeat", "chronic", "multiple", "frequent"]):
            query_type = "repeat_violators"
        elif any(word in query_lower for word in ["weather", "rain", "storm", "correlat"]):
            query_type = "weather_correlation"
        elif any(word in query_lower for word in ["trend", "over time", "history"]):
            query_type = "violation_trends"
        elif any(word in query_lower for word in ["find", "search", "where is"]):
            query_type = "facility_search"
        else:
            query_type = "general_overview"

        # Extract location
        location = self._extract_location(query)

        # Extract time range
        time_range = self._extract_time_range(query)

        return {
            "query_type": query_type,
            "location": location,
            "time_range": time_range,
            "data_sources": self._infer_data_sources(query_type),
            "visualization_type": self._infer_visualization(query_type),
            "filters": {},
            "original_query": query,
        }

    def _extract_location(self, query: str) -> Dict[str, Optional[str]]:
        """Extract location from query text."""
        # State abbreviations
        states = {
            "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
            "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
            "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
            "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
            "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
            "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
            "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
            "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
            "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
            "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
            "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
            "vermont": "VT", "virginia": "VA", "washington": "WA", "west virginia": "WV",
            "wisconsin": "WI", "wyoming": "WY",
        }

        query_lower = query.lower()
        state = None
        county = None

        # Check for state names
        for state_name, abbrev in states.items():
            if state_name in query_lower:
                state = abbrev
                break

        # Check for state abbreviations
        import re
        abbrev_match = re.search(r'\b([A-Z]{2})\b', query)
        if abbrev_match and abbrev_match.group(1) in states.values():
            state = abbrev_match.group(1)

        # Check for county
        county_match = re.search(r'(\w+)\s+county', query_lower)
        if county_match:
            county = county_match.group(1).title()

        # Defaults
        if not state:
            state = config.DEFAULT_STATE
        if not county:
            county = config.DEFAULT_COUNTY

        return {"state": state, "county": county, "city": None}

    def _extract_time_range(self, query: str) -> Dict[str, str]:
        """Extract time range from query text."""
        query_lower = query.lower()

        # Look for year patterns
        import re
        year_match = re.search(r'(\d{4})', query)
        years_match = re.search(r'(last\s+)?(\d+)\s+years?', query_lower)

        if years_match:
            num_years = int(years_match.group(2))
            return self._parse_relative_time(f"last {num_years} years")
        elif year_match:
            year = int(year_match.group(1))
            return {
                "start_date": f"{year}-01-01",
                "end_date": f"{year}-12-31",
            }

        # Default to last 3 years
        return self._parse_relative_time("last 3 years")

    def get_suggested_queries(self) -> list:
        """Return list of example queries for the UI."""
        return [
            "Show me sewage spill patterns in Baldwin County over the last 3 years",
            "Which facilities have the most repeat violations?",
            "Are spills correlated with heavy rainfall events?",
            "What are the violation trends in the past year?",
            "Show an overview of environmental compliance in my area",
        ]
