import json
from geopy.geocoders import Nominatim
from time import sleep
import sys

print("📍 Geocoding Company Addresses")

# Configuration
INPUT_FILE = '../data/company_data.json'
OUTPUT_FILE = '../data/atlas-of-public-stocks-2025.geojson'
GEOCODE_SERVICE = 'nominatim'
MAX_COMPANIES = None  # Set to a number (e.g., 100) to limit, or None for all

# Load company data
try:
    with open(INPUT_FILE, 'r') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"❌ Error: {INPUT_FILE} not found!")
    print("Please run 'python fetch_company_data.py' first")
    sys.exit(1)

all_companies = data.get('companies', [])
companies = all_companies[:MAX_COMPANIES] if MAX_COMPANIES else all_companies
print(f"Found {len(all_companies)} total companies")
if MAX_COMPANIES:
    print(f"Will geocode first {len(companies)} companies\n")
else:
    print(f"Will geocode all companies\n")

# Initialize geocoder
if GEOCODE_SERVICE == 'nominatim':
    geolocator = Nominatim(user_agent="stock_atlas")
    print("Using Nominatim (OpenStreetMap) geocoding service")

features = []
geocoded_count = 0
failed_count = 0
skipped_count = 0

for i, company in enumerate(companies):
    symbol = company['ticker']
    name = company['company_name'][:40]
    if GEOCODE_SERVICE == 'nominatim':
        print(f"Address data: {company['address_data']}")
        address = company['address_data']['street1']
        if company['address_data']['city']:
            address += ', ' + company['address_data']['city']
        if company['address_data']['state']:
            address += ', ' + company['address_data']['state']
        if company['address_data']['zipcode']:
            address += ', ' + company['address_data']['zipcode']
        if company['address_data']['country']:
            address += ', ' + company['address_data']['country']
        if address.startswith(', '):
            address = address[2:]
        print(f"Address: {address}")
    else:
        address = company['address']
    
    print(f"\n{i+1}/{len(companies)}: {symbol} - {name}")
    
    # Skip if already geocoded
    if company.get('geocoded') and company.get('coordinates'):
        print("Already geocoded, skipping")
        coords = company['coordinates']
        skipped_count += 1
    elif not address.strip():
        print("No address available")
        coords = [0, 0]
        failed_count += 1
    else:
        coords = [0, 0]
        try:
            print(f"  Geocoding: {address[:70]}")
            loc = geolocator.geocode(address, timeout=10)
            if loc:
                coords = [loc.longitude, loc.latitude]
                company['coordinates'] = coords
                company['geocoded'] = True
                geocoded_count += 1
                print(f"✅ Success: [{coords[0]:.6f}, {coords[1]:.6f}]")
            else:
                print(f"⚠️  Failed to geocode")
                failed_count += 1
        except Exception as e:
            print(f"❌ Error: {str(e)[:70]}")
            failed_count += 1
    
    # Create GeoJSON feature
    address_data = company.get('address_data', {})
    features.append({
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": coords
        },
        "properties": {
            "Company Name": company['company_name'],
            "Ticker": company['ticker'],
            "Description": company['description'],
            "Sector": company['sector'],
            "Industry-Group": company['industry_group'],
            "Industry": company['industry'],
            "Address": company['address'],
            "Address-Data": {
                "Street1": address_data.get('street1', ''),
                "Street2": address_data.get('street2', ''),
                "City": address_data.get('city', ''),
                "State": address_data.get('state', ''),
                "Country": address_data.get('country', ''),
                "Zipcode": address_data.get('zipcode', ''),
            },
            "URL": company['website'],
        }
    })
    
    # Save progress back to company_data.json after each geocode
    data['metadata']['geocoded_count'] = geocoded_count
    data['metadata']['failed_count'] = failed_count
    with open(INPUT_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    # Delay to respect rate limits (Nominatim requires 1 request/second)
    if not company.get('geocoded'):
        sleep(1.1)

# Save final GeoJSON
print(f"\n💾 Saving to {OUTPUT_FILE}...")
with open(OUTPUT_FILE, 'w') as f:
    json.dump({
        "type": "FeatureCollection",
        "features": features
    }, f, indent=2)

print("\n" + "="*60)
print("✅ Geocoding Complete!")
print("="*60)
print(f"Total companies:     {len(companies)}")
print(f"Successfully geocoded: {geocoded_count}")
print(f"Skipped (already done): {skipped_count}")
print(f"Failed:              {failed_count}")
print(f"\nOutput saved to: {OUTPUT_FILE}")
print(f"\nTo retry failed geocodes, run this script again.")
print(f"Progress is saved to {INPUT_FILE}")

