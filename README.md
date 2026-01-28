# ClimateBud - Environmental Data Analysis Assistant

AI-made code for a competition

An AI-powered Streamlit application that enables non-technical users to analyze environmental data through natural language queries.

## Features

- **Natural Language Queries**: Ask questions about environmental data in plain English
- **Interactive Visualizations**: Maps, charts, and heatmaps powered by Plotly and Folium
- **AI-Generated Insights**: GPT-4 powered analysis and recommendations
- **Multiple Data Sources**: EPA ECHO, NOAA Weather, US Census Bureau
- **Export Reports**: PDF reports and CSV data exports

## Demo Queries

- "Show me sewage spill patterns in Baldwin County over the last 3 years"
- "Which facilities have the most repeat violations?"
- "Are spills correlated with heavy rainfall events?"

## Installation

```bash
# Clone the repository
git clone https://github.com/Seba905xd/ClimateBud.git
cd ClimateBud

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your API keys

# Run the app
streamlit run app.py
```

## API Keys Required

- **OpenAI API Key** (required for AI features): [Get one here](https://platform.openai.com/api-keys)
- **NOAA API Key** (free): [Get one here](https://www.ncdc.noaa.gov/cdo-web/token)
- **Census API Key** (optional): [Get one here](https://api.census.gov/data/key_signup.html)

## Deployment

This app is configured for deployment on [Streamlit Community Cloud](https://share.streamlit.io):

1. Push to GitHub
2. Connect your repo on share.streamlit.io
3. Add your API keys in the Secrets section

## Tech Stack

- **Frontend**: Streamlit
- **AI/LLM**: OpenAI GPT-4
- **Data Sources**: EPA ECHO API, NOAA API, Census Bureau API
- **Visualizations**: Plotly, Folium
- **Reports**: ReportLab (PDF)

## License

MIT
