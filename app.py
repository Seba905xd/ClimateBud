"""ClimateBud - Environmental Data Analysis Assistant.

A Streamlit application for analyzing environmental data through natural language queries.
"""

import streamlit as st
from datetime import datetime, timedelta
import pandas as pd

# Import local modules
from core.query_processor import QueryProcessor
from core.analysis_engine import AnalysisEngine
from core.insight_generator import InsightGenerator
from data.data_manager import DataManager
from visualization.maps import MapGenerator
from visualization.charts import ChartGenerator
from visualization.report_builder import ReportBuilder
import config

# Page configuration
st.set_page_config(
    page_title="ClimateBud - Environmental Analysis",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1a5f7a;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .insight-box {
        background-color: #f0f7fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1a5f7a;
        margin: 1rem 0;
    }
    .metric-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
    .concern-box {
        background-color: #fff5f5;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #e74c3c;
        margin: 0.5rem 0;
    }
    .recommendation-box {
        background-color: #f0fff4;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #27ae60;
        margin: 0.5rem 0;
    }
    .stButton>button {
        background-color: #1a5f7a;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #145a6e;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if "query_history" not in st.session_state:
        st.session_state.query_history = []
    if "current_results" not in st.session_state:
        st.session_state.current_results = None
    if "current_insights" not in st.session_state:
        st.session_state.current_insights = None
    if "current_data" not in st.session_state:
        st.session_state.current_data = {}


@st.cache_resource
def get_components():
    """Initialize and cache application components."""
    return {
        "query_processor": QueryProcessor(),
        "analysis_engine": AnalysisEngine(),
        "insight_generator": InsightGenerator(),
        "data_manager": DataManager(),
        "map_generator": MapGenerator(),
        "chart_generator": ChartGenerator(),
        "report_builder": ReportBuilder(),
    }


def render_sidebar():
    """Render the sidebar with query history and settings."""
    with st.sidebar:
        st.markdown("### Settings")

        # Location settings
        state = st.selectbox(
            "Default State",
            ["AL", "CA", "FL", "TX", "NY"],
            index=0,
            help="Default state for queries",
        )

        county = st.text_input(
            "Default County",
            value="Baldwin",
            help="Default county for queries",
        )

        st.markdown("---")

        # Query history
        st.markdown("### Query History")
        if st.session_state.query_history:
            for i, query in enumerate(reversed(st.session_state.query_history[-5:])):
                if st.button(f"📝 {query[:40]}...", key=f"history_{i}"):
                    st.session_state.rerun_query = query
        else:
            st.info("No queries yet")

        st.markdown("---")

        # Export options
        st.markdown("### Export Data")
        if st.session_state.current_data:
            components = get_components()

            # CSV export
            if "violations" in st.session_state.current_data:
                csv_data = components["report_builder"].build_csv_export(
                    st.session_state.current_data["violations"]
                )
                st.download_button(
                    label="Download CSV",
                    data=csv_data,
                    file_name="environmental_data.csv",
                    mime="text/csv",
                )

            # PDF export
            if st.session_state.current_results and st.session_state.current_insights:
                pdf_data = components["report_builder"].build_pdf_report(
                    st.session_state.current_results,
                    st.session_state.current_insights,
                    {"state": state, "county": county},
                )
                st.download_button(
                    label="Download PDF Report",
                    data=pdf_data,
                    file_name="environmental_report.pdf",
                    mime="application/pdf",
                )

        return {"state": state, "county": county}


def render_example_queries():
    """Render example query buttons."""
    st.markdown("### Quick Start - Example Queries")

    col1, col2 = st.columns(2)

    example_queries = [
        ("🗺️ Spill Patterns", "Show me sewage spill patterns in Baldwin County over the last 3 years"),
        ("🔄 Repeat Violators", "Which facilities have the most repeat violations?"),
        ("🌧️ Weather Correlation", "Are spills correlated with heavy rainfall events?"),
        ("📈 Violation Trends", "What are the violation trends in the past year?"),
    ]

    selected_query = None
    for i, (label, query) in enumerate(example_queries):
        col = col1 if i % 2 == 0 else col2
        with col:
            if st.button(label, key=f"example_{i}", use_container_width=True):
                selected_query = query

    return selected_query


def process_query(query: str, settings: dict):
    """Process a user query and display results."""
    try:
        components = get_components()

        with st.spinner("Understanding your query..."):
            # Parse the query
            parsed = components["query_processor"].process_query(query)

            # Update location from settings if not in query
            if not parsed["location"].get("state"):
                parsed["location"]["state"] = settings["state"]
            if not parsed["location"].get("county"):
                parsed["location"]["county"] = settings["county"]

        # Show parsed query info
        with st.expander("Query Details", expanded=False):
            st.json({
                "type": parsed["query_type"],
                "location": parsed["location"],
                "time_range": parsed["time_range"],
                "visualization": parsed["visualization_type"],
            })

        # Fetch and analyze data
        with st.spinner("Fetching environmental data..."):
            data = fetch_data_for_query(parsed, components)
            st.session_state.current_data = data

        with st.spinner("Analyzing patterns..."):
            results = analyze_data(parsed, data, components)
            st.session_state.current_results = results

        with st.spinner("Generating insights..."):
            insights = components["insight_generator"].generate_insights(
                results,
                parsed["query_type"],
                parsed["location"],
            )
            st.session_state.current_insights = insights

        # Display results
        display_results(parsed, data, results, insights, components)

        # Add to history
        if query not in st.session_state.query_history:
            st.session_state.query_history.append(query)

    except Exception as e:
        st.error(f"An error occurred while processing your query: {str(e)}")
        st.info("Try one of the example queries, or check that your query is about environmental data analysis.")
        import traceback
        with st.expander("Error Details", expanded=False):
            st.code(traceback.format_exc())


def fetch_data_for_query(parsed: dict, components: dict) -> dict:
    """Fetch data based on parsed query."""
    dm = components["data_manager"]
    location = parsed["location"]
    time_range = parsed["time_range"]

    start_date = datetime.strptime(time_range["start_date"], "%Y-%m-%d")
    end_date = datetime.strptime(time_range["end_date"], "%Y-%m-%d")

    data = {}

    query_type = parsed["query_type"]

    if query_type in ["spill_analysis", "violation_trends", "general_overview"]:
        data["violations"] = dm.epa.get_violations(
            state=location["state"],
            county=location["county"],
            start_date=start_date,
            end_date=end_date,
        )
        data["facilities"] = dm.epa.get_facilities(
            state=location["state"],
            county=location["county"],
        )

    if query_type == "repeat_violators":
        data["violations"] = dm.epa.get_violations(
            state=location["state"],
            county=location["county"],
            start_date=start_date,
            end_date=end_date,
        )

    if query_type == "weather_correlation":
        data["violations"] = dm.epa.get_violations(
            state=location["state"],
            county=location["county"],
            start_date=start_date,
            end_date=end_date,
        )
        data["precipitation"] = dm.noaa.get_precipitation(
            start_date=start_date,
            end_date=end_date,
        )

    # Always get some basic data
    if "violations" not in data:
        data["violations"] = dm.epa.get_violations(
            state=location["state"],
            county=location["county"],
        )

    return data


def analyze_data(parsed: dict, data: dict, components: dict) -> dict:
    """Analyze data based on query type."""
    engine = components["analysis_engine"]
    query_type = parsed["query_type"]

    if query_type == "spill_analysis":
        return engine.analyze_spill_patterns(
            data.get("violations", pd.DataFrame()),
            data.get("precipitation"),
        )

    elif query_type == "repeat_violators":
        return engine.analyze_repeat_violators(
            data.get("violations", pd.DataFrame()),
        )

    elif query_type == "weather_correlation":
        return engine.analyze_weather_correlation(
            data.get("violations", pd.DataFrame()),
            data.get("precipitation", pd.DataFrame()),
        )

    elif query_type == "violation_trends":
        return engine.analyze_spill_patterns(
            data.get("violations", pd.DataFrame()),
        )

    else:
        # General overview
        return engine.analyze_spill_patterns(
            data.get("violations", pd.DataFrame()),
        )


def display_results(parsed: dict, data: dict, results: dict, insights: dict, components: dict):
    """Display analysis results with visualizations."""
    query_type = parsed["query_type"]
    maps = components["map_generator"]
    charts = components["chart_generator"]

    # Summary metrics
    st.markdown("---")
    st.markdown("## Analysis Results")

    display_metrics(results)

    # Insights section
    st.markdown("### Key Insights")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.markdown(f'<div class="insight-box">{insights.get("summary", "")}</div>', unsafe_allow_html=True)

        # Key findings
        findings = insights.get("key_findings", [])
        if findings:
            st.markdown("**Key Findings:**")
            for finding in findings:
                st.markdown(f"• {finding}")

    with col2:
        # Concerns
        concerns = insights.get("concerns", [])
        if concerns:
            st.markdown("**Areas of Concern:**")
            for concern in concerns:
                st.markdown(f'<div class="concern-box">{concern}</div>', unsafe_allow_html=True)

    # Recommendations
    recommendations = insights.get("recommendations", [])
    if recommendations:
        st.markdown("### Recommendations")
        for i, rec in enumerate(recommendations, 1):
            st.markdown(f'<div class="recommendation-box">{i}. {rec}</div>', unsafe_allow_html=True)

    # Visualizations
    st.markdown("---")
    st.markdown("## Visualizations")

    display_visualizations(query_type, data, results, maps, charts)


def display_metrics(results: dict):
    """Display summary metrics."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total = results.get("total_incidents", 0)
        st.metric("Total Incidents", total)

    with col2:
        if "by_facility" in results:
            facilities = results["by_facility"].get("total_facilities", 0)
            st.metric("Facilities", facilities)
        elif "total_facilities" in results:
            st.metric("Facilities", results["total_facilities"])

    with col3:
        if "by_facility" in results:
            repeat = results["by_facility"].get("repeat_violator_count", 0)
            st.metric("Repeat Violators", repeat)
        elif "repeat_violators" in results:
            st.metric("Repeat Violators", results["repeat_violators"])

    with col4:
        if "temporal" in results:
            trend = results["temporal"].get("trend", "stable").title()
            st.metric("Trend", trend)
        elif "chronic_violators" in results:
            st.metric("Chronic Violators", results["chronic_violators"])


def display_visualizations(query_type: str, data: dict, results: dict, maps, charts):
    """Display visualizations based on query type."""
    violations = data.get("violations", pd.DataFrame())
    precipitation = data.get("precipitation", pd.DataFrame())

    tab1, tab2, tab3 = st.tabs(["📊 Charts", "🗺️ Map", "📋 Data"])

    with tab1:
        display_charts(query_type, violations, precipitation, results, charts)

    with tab2:
        display_map(violations, results, maps)

    with tab3:
        display_data_table(violations)


def display_charts(query_type: str, violations: pd.DataFrame, precipitation: pd.DataFrame, results: dict, charts):
    """Display charts based on query type."""
    col1, col2 = st.columns(2)

    with col1:
        if query_type == "repeat_violators" and "top_violators" in results:
            violators_df = pd.DataFrame(results["top_violators"])
            if not violators_df.empty:
                fig = charts.create_top_violators_chart(violators_df)
                st.plotly_chart(fig, use_container_width=True)
        elif not violations.empty:
            fig = charts.create_violation_trend(violations)
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        if query_type == "weather_correlation" and not precipitation.empty:
            # Merge data for correlation chart
            merged = prepare_correlation_data(violations, precipitation)
            if not merged.empty:
                fig = charts.create_weather_correlation_scatter(merged)
                st.plotly_chart(fig, use_container_width=True)
        elif not violations.empty and "severity" in violations.columns:
            fig = charts.create_severity_pie(violations)
            st.plotly_chart(fig, use_container_width=True)

    # Additional charts
    if not violations.empty:
        col3, col4 = st.columns(2)

        with col3:
            if "violation_type" in violations.columns:
                fig = charts.create_violation_type_chart(violations)
                st.plotly_chart(fig, use_container_width=True)

        with col4:
            fig = charts.create_monthly_heatmap(violations)
            st.plotly_chart(fig, use_container_width=True)


def display_map(violations: pd.DataFrame, results: dict, maps):
    """Display map visualization."""
    if violations.empty:
        st.info("No geographic data available for mapping.")
        return

    # Check for valid coordinates
    valid_coords = violations.dropna(subset=["latitude", "longitude"])
    if valid_coords.empty:
        st.info("No location data available for mapping.")
        return

    # Create map
    m = maps.create_violation_map(violations, show_heatmap=True)

    # Display map
    try:
        from streamlit_folium import folium_static
        folium_static(m, width=None, height=500)
    except ImportError:
        st.warning("Install streamlit-folium to view interactive maps: pip install streamlit-folium")
        st.map(valid_coords[["latitude", "longitude"]].rename(columns={"latitude": "lat", "longitude": "lon"}))


def display_data_table(violations: pd.DataFrame):
    """Display data table."""
    if violations.empty:
        st.info("No data available.")
        return

    st.markdown("### Violation Records")

    # Select columns to display
    display_cols = [col for col in [
        "facility_name", "violation_date", "violation_type",
        "severity", "parameter", "latitude", "longitude"
    ] if col in violations.columns]

    if display_cols:
        st.dataframe(
            violations[display_cols].head(100),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Showing first 100 of {len(violations)} records")


def prepare_correlation_data(violations: pd.DataFrame, precipitation: pd.DataFrame) -> pd.DataFrame:
    """Prepare merged data for correlation analysis."""
    if violations.empty or precipitation.empty:
        return pd.DataFrame()

    violations = violations.copy()
    violations["date"] = pd.to_datetime(violations["violation_date"])

    daily_violations = violations.groupby(
        violations["date"].dt.date
    ).size().reset_index(name="violation_count")
    daily_violations["date"] = pd.to_datetime(daily_violations["date"])

    precipitation = precipitation.copy()
    precipitation["date"] = pd.to_datetime(precipitation["date"])

    merged = pd.merge(
        precipitation[["date", "precipitation_inches"]],
        daily_violations,
        on="date",
        how="left",
    )
    merged["violation_count"] = merged["violation_count"].fillna(0)

    return merged


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    st.markdown('<p class="main-header">🌍 ClimateBud</p>', unsafe_allow_html=True)
    st.markdown(
        '<p class="sub-header">Environmental Data Analysis Assistant - Ask questions about environmental data in plain English</p>',
        unsafe_allow_html=True,
    )

    # Sidebar
    settings = render_sidebar()

    # Check for API key
    if not config.OPENAI_API_KEY:
        st.warning(
            "OpenAI API key not configured. The app will use fallback query parsing. "
            "Set OPENAI_API_KEY in your .env file for full functionality."
        )

    # Example queries
    example_query = render_example_queries()

    # Query input
    st.markdown("---")
    st.markdown("### Ask a Question")

    # Check if we should rerun a query from history
    default_query = ""
    if hasattr(st.session_state, "rerun_query"):
        default_query = st.session_state.rerun_query
        del st.session_state.rerun_query

    query = st.text_input(
        "Enter your question about environmental data:",
        value=default_query,
        placeholder="e.g., Show me sewage spill patterns in Baldwin County...",
        key="query_input",
    )

    col1, col2 = st.columns([1, 5])
    with col1:
        analyze_button = st.button("Analyze", type="primary", use_container_width=True)

    # Process query
    if analyze_button and query:
        process_query(query, settings)
    elif example_query:
        process_query(example_query, settings)
    elif st.session_state.current_results:
        # Display cached results
        components = get_components()
        display_results(
            {"query_type": "general_overview", "location": settings},
            st.session_state.current_data,
            st.session_state.current_results,
            st.session_state.current_insights,
            components,
        )

    # Footer
    st.markdown("---")
    st.markdown(
        """
        <div style="text-align: center; color: #666; font-size: 0.9em;">
            ClimateBud - Environmental Data Analysis Assistant<br>
            Data sources: EPA ECHO, NOAA, US Census Bureau
        </div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
