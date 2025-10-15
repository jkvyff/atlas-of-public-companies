import financedatabase as fd
import yfinance as yf
import json
from time import sleep
import sys
import os

print("🌍 Fetching Company Data from FinanceDatabase")

# Configuration
NUM_COMPANIES = 30000  # Change this to get more companies
START_FROM = 0  # Start from this iteration (0 = start from beginning)
OUTPUT_FILE = '../data/company_data.json'
SAVE_INTERVAL = 100  # Save progress every N companies

# Load existing data if it exists (for resume capability)
existing_tickers = set()
companies = []
if os.path.exists(OUTPUT_FILE):
    print(f"📂 Found existing file: {OUTPUT_FILE}")
    try:
        with open(OUTPUT_FILE, 'r') as f:
            existing_data = json.load(f)
            companies = existing_data.get('companies', [])
            existing_tickers = {c['ticker'] for c in companies}
            print(f"   Loaded {len(companies)} existing companies")
            print(f"   Will resume from where we left off...\n")
    except Exception as e:
        print(f"   ⚠️  Error loading file: {e}")
        print(f"   Starting fresh...\n")

# Load equities
equities = fd.Equities()

# Filter to avoid duplicates - only primary listings
print("📊 Loading equities...")
data = equities.select(only_primary_listing=True)
print(f"Found {len(data)} companies in database")
if START_FROM > 0:
    print(f"Starting from iteration {START_FROM}")
print(f"Will fetch data for up to {NUM_COMPANIES} companies\n")

failed = []
skipped_count = 0
fetched_count = 0

# Helper function to save progress
def save_progress():
    print(f"\n💾 Saving progress to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump({
            "metadata": {
                "total_companies": len(companies),
                "geocoded_count": 0,
                "failed_count": 0
            },
            "companies": companies
        }, f, indent=2)
    print(f"✅ Saved {len(companies)} companies\n")

for i, (symbol, row) in enumerate(data.head(NUM_COMPANIES).iterrows()):
    # Skip to START_FROM iteration if specified
    if i < START_FROM:
        continue
        
    company_name = row.get('name', 'Unknown')
    if not isinstance(company_name, str):
        company_name = str(company_name) if company_name else 'Unknown'
    print(f"{i+1}/{NUM_COMPANIES}: {symbol} - {company_name[:40]}")
    
    # Skip if symbol is invalid (nan, None, or empty)
    if not symbol or not isinstance(symbol, str) or str(symbol).lower() == 'nan':
        print(f"Skipping - Invalid ticker symbol")
        skipped_count += 1
        continue
    
    # Skip if already fetched
    if symbol in existing_tickers:
        print(f"Already fetched, skipping")
        skipped_count += 1
        continue
    
    # Skip tickers with problematic characters that cause API issues
    if '/' in symbol or '\\' in symbol or '^' in symbol or '=' in symbol:
        print(f"Skipping - Ticker contains special characters that may cause API issues")
        skipped_count += 1
        continue
    
    # Try to get detailed address and website from yfinance
    street_address1 = None
    street_address2 = None
    city = None
    state = None
    zipcode = None
    country = None
    website = None
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        street_address1 = info.get('address1')
        street_address2 = info.get('address2')
        city = info.get('city')
        state = info.get('state')
        zipcode = info.get('zip')
        country = info.get('country')
        website = info.get('website')
        print(f"  Street: {street_address1}")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user!")
        print("Saving progress before exiting...")
        save_progress()
        sys.exit(0)
    except Exception as e:
        print(f"yfinance error: {str(e)[:50]}")
        failed.append({"ticker": symbol, "error": str(e)[:100]})
    
    # Build full address with all available fields
    address_parts = [
        street_address1,  # From yfinance if available
        street_address2,
        city,
        state,
        zipcode,
        country

    ]
    # Filter out empty/nan values
    address = ', '.join([str(p) for p in address_parts if p and str(p) != 'nan'])
    
    # Helper function to safely get string value
    def safe_str(value, max_length=None):
        if value is None or (isinstance(value, float) and str(value) == 'nan'):
            return ''
        result = str(value)
        if max_length and len(result) > max_length:
            return result[:max_length]
        return result
    
    # Check if company has required location data (city, country)
    city_val = safe_str(city)
    state_val = safe_str(state)
    country_val = safe_str(country)
    zipcode_val = safe_str(zipcode)
    
    if not (city_val and country_val):
        print(f"Skipping - Missing required location data (city: {bool(city_val)}, country: {bool(country_val)})")
        sleep(0.01)
        continue
    
    company_data = {
        "ticker": symbol,
        "company_name": safe_str(row.get('name')),
        "description": safe_str(row.get('summary')),
        "sector": safe_str(row.get('sector')),
        "industry_group": safe_str(row.get('industry_group')),
        "industry": safe_str(row.get('industry')),
        "address": address,
        "address_data": {
            "street1": safe_str(street_address1),
            "street2": safe_str(street_address2),
            "city": city_val,
            "state": state_val,
            "country": country_val,
            "zipcode": zipcode_val,
        },
        "website": safe_str(website),  # From yfinance instead of FinanceDatabase
        "isin": safe_str(row.get('isin')),
        "figi": safe_str(row.get('figi')),
        "exchange": safe_str(row.get('exchange')),
        "geocoded": False,  # Will be set to True when geocoded
        "coordinates": None  # Will be filled by geocoding script
    }
    
    companies.append(company_data)
    existing_tickers.add(symbol)
    fetched_count += 1
    print(f"✅ Data collected")
    
    # Save progress periodically
    if fetched_count % SAVE_INTERVAL == 0:
        save_progress()
    
    # Small delay to be nice to APIs
    sleep(1.1)

# Final save
save_progress()

print("\n" + "="*60)
print("✅ Data Collection Complete!")
print("="*60)
print(f"Total companies in file: {len(companies)}")
print(f"Newly fetched:          {fetched_count}")
print(f"Skipped (already had):  {skipped_count}")
if failed:
    print(f"Failed to fetch:        {len(failed)}")
print(f"\nNext step: Run 'python geocode_addresses.py' to geocode addresses")

