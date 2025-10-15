from dotenv import load_dotenv
load_dotenv()

import json
import sys
from time import sleep
import os

print("🌍 Google Geocoding API - Retry Failed Addresses")
print("="*60)

# Configuration
COMPANY_DATA_FILE = '../data/company_data.json'
ATLAS_FILE = '../data/atlas-of-public-stocks-2026.geojson'
MAX_RETRIES = None  # Set to a number to limit retries, or None for all
SAVE_INTERVAL = 10  # Save progress every N geocodes

# Get API key from environment variable or set it directly
GOOGLE_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')

# Check if API key is set
if not GOOGLE_API_KEY:
    print("❌ ERROR: Google API key not found!")
    print("\n📝 You can set it in one of two ways:")
    print("\n1. Environment variable (recommended):")
    print("   export GOOGLE_MAPS_API_KEY='your-api-key-here'")
    print("   python geocode_with_google.py")
    print("\n2. Or edit this script and set:")
    print("   GOOGLE_API_KEY = 'your-api-key-here'")
    print("\n🔑 Get your API key at: https://console.cloud.google.com/apis/credentials")
    sys.exit(1)

# Import Google geocoding
try:
    from geopy.geocoders import GoogleV3
    geolocator = GoogleV3(api_key=GOOGLE_API_KEY)
    print("✅ Google Geocoding API initialized")
except ImportError:
    print("❌ ERROR: geopy library not found!")
    print("   Install it with: pip install geopy")
    sys.exit(1)

# Load company data
print(f"\n📂 Loading company data from {COMPANY_DATA_FILE}...")
try:
    with open(COMPANY_DATA_FILE, 'r') as f:
        company_data = json.load(f)
except FileNotFoundError:
    print(f"❌ Error: {COMPANY_DATA_FILE} not found!")
    sys.exit(1)

companies = company_data.get('companies', [])
print(f"   Loaded {len(companies)} companies")

# Find companies with failed geocoding
failed_companies = []
for company in companies:
    coords = company.get('coordinates')
    geocoded = company.get('geocoded', False)
    
    # Check if coordinates are null, [0,0], or not geocoded
    if not geocoded or coords is None or coords == [0, 0]:
        failed_companies.append(company)

print(f"   Found {len(failed_companies)} companies with failed/missing geocoding")

if len(failed_companies) == 0:
    print("✅ All companies already have valid coordinates!")
    sys.exit(0)

# Limit if MAX_RETRIES is set
companies_to_retry = failed_companies[:MAX_RETRIES] if MAX_RETRIES else failed_companies
print(f"   Will retry {len(companies_to_retry)} companies\n")

# Load atlas GeoJSON
print(f"📂 Loading atlas from {ATLAS_FILE}...")
try:
    with open(ATLAS_FILE, 'r') as f:
        atlas_data = json.load(f)
    atlas_features = atlas_data.get('features', [])
    print(f"   Loaded {len(atlas_features)} features from atlas\n")
except FileNotFoundError:
    print(f"⚠️  Atlas file not found. Will create new one.")
    atlas_data = {"type": "FeatureCollection", "features": []}
    atlas_features = []

# Create a mapping from ticker to atlas feature index
ticker_to_atlas_index = {}
for idx, feature in enumerate(atlas_features):
    ticker = feature['properties'].get('Ticker')
    if ticker:
        ticker_to_atlas_index[ticker] = idx

# Helper function to save progress
def save_progress():
    print(f"\n💾 Saving progress...")
    # Update metadata
    company_data['metadata']['geocoded_count'] = sum(1 for c in companies if c.get('geocoded'))
    company_data['metadata']['failed_count'] = sum(1 for c in companies if not c.get('geocoded'))
    
    # Save company data
    with open(COMPANY_DATA_FILE, 'w') as f:
        json.dump(company_data, f, indent=2)
    print(f"   ✅ Saved company data")
    
    # Save atlas
    with open(ATLAS_FILE, 'w') as f:
        json.dump(atlas_data, f, indent=2)
    print(f"   ✅ Saved atlas\n")

# Geocode failed companies
success_count = 0
still_failed_count = 0

for i, company in enumerate(companies_to_retry):
    ticker = company['ticker']
    company_name = company['company_name'][:40]
    address = company['address']
    
    print(f"{i+1}/{len(companies_to_retry)}: {ticker} - {company_name}")
    print(f"  Address: {address[:70]}")
    
    if not address or address.strip() == '':
        print(f"  ⏭️  No address available, skipping")
        still_failed_count += 1
        continue
    
    try:
        # Try geocoding with Google
        location = geolocator.geocode(address, timeout=10)
        
        if location:
            coords = [location.longitude, location.latitude]
            company['coordinates'] = coords
            company['geocoded'] = True
            success_count += 1
            
            print(f"  ✅ Success: [{coords[0]:.6f}, {coords[1]:.6f}]")
            
            # Update atlas if this company exists in it
            if ticker in ticker_to_atlas_index:
                idx = ticker_to_atlas_index[ticker]
                atlas_features[idx]['geometry']['coordinates'] = coords
                print(f"  📝 Updated atlas entry")
            else:
                # Add new feature to atlas
                address_data = company.get('address_data', {})
                new_feature = {
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": coords
                    },
                    "properties": {
                        "Company Name": company['company_name'],
                        "Ticker": ticker,
                        "Description": company.get('description', ''),
                        "Sector": company.get('sector', ''),
                        "Industry": company.get('industry', ''),
                        "Sub-Industry": company.get('industry_group', ''),
                        "Address": address,
                        "URL": company.get('website', ''),
                        "City": address_data.get('city', ''),
                        "State": address_data.get('state', ''),
                        "Country": address_data.get('country', ''),
                        "Zipcode": address_data.get('zipcode', ''),
                    }
                }
                atlas_features.append(new_feature)
                ticker_to_atlas_index[ticker] = len(atlas_features) - 1
                print(f"  📝 Added to atlas")
        else:
            print(f"  ⚠️  Failed to geocode")
            still_failed_count += 1
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user!")
        print("Saving progress before exiting...")
        save_progress()
        sys.exit(0)
    
    except Exception as e:
        print(f"  ❌ Error: {str(e)[:70]}")
        still_failed_count += 1
    
    # Save progress periodically
    if (success_count > 0 and success_count % SAVE_INTERVAL == 0):
        save_progress()
    
    # Delay to respect Google's rate limits (50 requests per second max)
    # sleep(1.0)
    sleep(0.05)

# Final save
save_progress()

# Summary
print("\n" + "="*60)
print("✅ Google Geocoding Complete!")
print("="*60)
print(f"Successfully geocoded: {success_count}")
print(f"Still failed:          {still_failed_count}")
print(f"Total attempted:       {len(companies_to_retry)}")
print(f"\nAtlas now has:        {len(atlas_features)} companies")
print(f"\n💡 Tip: Refresh your map to see the updated locations!")

