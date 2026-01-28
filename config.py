"""Configuration settings for ClimateBud application."""

import os
from dotenv import load_dotenv

load_dotenv()


def get_secret(key: str) -> str:
    """Get secret from Streamlit secrets or environment variable."""
    # Try Streamlit secrets first (for cloud deployment)
    try:
        import streamlit as st
        if hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    # Fall back to environment variable
    return os.getenv(key)


# API Keys
OPENAI_API_KEY = get_secret("OPENAI_API_KEY")
NOAA_API_KEY = get_secret("NOAA_API_KEY")
CENSUS_API_KEY = get_secret("CENSUS_API_KEY")

# API Endpoints
EPA_ECHO_BASE_URL = "https://echo.epa.gov/api"
NOAA_BASE_URL = "https://www.ncdc.noaa.gov/cdo-web/api/v2"
CENSUS_BASE_URL = "https://api.census.gov/data"

# Cache settings
CACHE_DIR = ".cache"
CACHE_EXPIRY_HOURS = 24

# OpenAI settings
OPENAI_MODEL = "gpt-4"
OPENAI_TEMPERATURE = 0.3

# Default geographic settings
DEFAULT_STATE = "AL"
DEFAULT_COUNTY = "Baldwin"

# Visualization settings
MAP_DEFAULT_ZOOM = 10
MAP_DEFAULT_CENTER = [30.6549, -87.7473]  # Baldwin County, AL
PLOTLY_TEMPLATE = "plotly_white"

# Data limits
MAX_FACILITIES = 500
MAX_TIME_RANGE_DAYS = 1095  # 3 years
