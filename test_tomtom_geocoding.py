import urllib.request
import urllib.parse
import urllib.error
import json
import sys

# TomTom Reverse Geocoding API URL
TOMTOM_REVERSE_GEOCODE_URL = "https://api.tomtom.com/search/2/reverseGeocode"

def test_tomtom_geocoding(api_key, lat, lon):
    print(f"\n--- Testing TomTom Reverse Geocoding (Lat: {lat}, Lon: {lon}) ---")
    
    # Construct URL: https://api.tomtom.com/search/2/reverseGeocode/{lat},{lon}.json
    base_url = f"{TOMTOM_REVERSE_GEOCODE_URL}/{lat},{lon}.json"
    
    params = {
        "key": api_key,
        "returnSpeedLimit": "true",  # This is the key parameter!
        "radius": 50, # Search within 50 meters
        "heading": 0 # Optional, but good if we knew direction. Leaving at 0 for now.
    }
    
    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    print(f"Request URL: {url.replace(api_key, 'HIDDEN_KEY')}")
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("Status: Success (200)")
            
            addresses = data.get("addresses", [])
            if addresses:
                print(f"Found {len(addresses)} address matches.")
                for i, addr in enumerate(addresses):
                    print(f"\n--- Result {i+1} ---")
                    
                    # Check for Speed Limit
                    # Note: Documentation says it's often in "address" or root object depending on version
                    # Let's inspect the whole object to find it.
                    
                    road_name = addr.get("address", {}).get("street", "Unknown Road")
                    print(f"Road: {road_name}")
                    
                    # Look for speed limit fields
                    # It might be a top-level key in the address object or nested
                    print("Full Result Object:")
                    print(json.dumps(addr, indent=2))
                    
            else:
                print("No addresses found.")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Hardcoded coordinates for Sunset Hwy test: 45.509139, -122.708
    # Using your key from context
    API_KEY = "9mUslvD61yuojwtQiMdjDPEyIL4sDqdh" 
    LAT = 45.509139
    LON = -122.708
    
    test_tomtom_geocoding(API_KEY, LAT, LON)
