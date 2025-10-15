# Atlas Generation Scripts

This folder contains scripts to generate a GeoJSON file of public companies with their locations.

## Two-Step Process

### Step 1: Fetch Company Data
```bash
python fetch_company_data.py
```

This script:
- Fetches company information from FinanceDatabase
- Gets detailed addresses from yfinance
- Saves raw data to `company_data.json`
- Does NOT geocode addresses yet

**Configuration:**
- Edit `NUM_COMPANIES` in the script to change how many companies to fetch
- Default is 10 for testing

### Step 2: Geocode Addresses
```bash
python geocode_addresses.py
```

This script:
- Reads `company_data.json`
- Geocodes each address to get coordinates
- Saves progress after each company (can be interrupted!)
- Outputs final GeoJSON to `atlas-of-public-stocks-2026.geojson`
- Can be run multiple times to retry failed geocodes

**Features:**
- Progress is saved automatically
- Skips already geocoded addresses
- Can be interrupted and resumed
- Detailed logging of successes/failures

### Step 3 (Optional): Retry Failed Geocodes with Google
```bash
python geocode_with_google.py
```

This script:
- Finds companies with failed/missing geocoding (null or [0,0] coordinates)
- Uses Google Maps Geocoding API to retry them
- Updates BOTH `company_data.json` AND the atlas GeoJSON file
- Saves progress automatically

**Requirements:**
- Google Cloud Platform account
- Geocoding API enabled
- API key (see setup below)
- `pip install geopy` (if not already installed)

**Setup API Key (recommended - use environment variable):**
```bash
# Set environment variable (Mac/Linux)
export GOOGLE_MAPS_API_KEY='your-api-key-here'

# Or for current session only
GOOGLE_MAPS_API_KEY='your-api-key-here' python geocode_with_google.py

# Windows (PowerShell)
$env:GOOGLE_MAPS_API_KEY='your-api-key-here'
```

**Configuration:**
- Set `MAX_RETRIES` to limit how many to attempt
- Google allows 50 requests/second, charges after free tier

## Workflow Example

```bash
# 1. Fetch company data (fast)
python fetch_company_data.py

# 2. Geocode addresses with free Nominatim (slower, 1 req/sec limit)
python geocode_addresses.py

# 3. Retry failed geocodes with Google API (optional, more accurate)
python geocode_with_google.py

# The atlas file is automatically saved to ../data/ directory
```

## Output Files

- `company_data.json` - Intermediate file with raw company data and geocoding status
- `atlas-of-public-stocks-2026.geojson` - Final GeoJSON file for the map

## Geocoding Services

### Nominatim (OpenStreetMap) - Free
- Used by: `geocode_addresses.py`
- Rate limit: 1 request/second
- No API key needed
- Good for most addresses

### Google Maps Geocoding API - Paid (with free tier)
- Used by: `geocode_with_google.py`
- Rate limit: 50 requests/second
- Requires API key
- More accurate, especially for international addresses
- Free tier: $200/month credit (~40,000 requests)
- Pricing: $5 per 1000 requests after free tier

**Recommended workflow:** Use Nominatim first (free), then use Google to retry only the failed ones.

