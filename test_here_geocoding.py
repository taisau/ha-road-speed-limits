import urllib.request
import urllib.parse
import urllib.error
import json
import sys

# HERE Reverse Geocoding API URL (v1/revgeocode is part of the Search API v7 suite)
HERE_REVGEOCODE_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"

def test_here_geocoding(api_key, lat, lon):
    print(f"\n--- Testing HERE Reverse Geocoding (Lat: {lat}, Lon: {lon}) ---")
    
    params = {
        "at": f"{lat},{lon}",
        "apiKey": api_key,
        "showNavAttributes": "speedLimits,functionalClass,physical", 
        "lang": "en-US"
    }
    
    url = f"{HERE_REVGEOCODE_URL}?{urllib.parse.urlencode(params)}"
    print(f"Request URL: {url.replace(api_key, 'HIDDEN_KEY')}")
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("Status: Success (200)")
            
            items = data.get("items", [])
            if items:
                print(f"Found {len(items)} address matches.")
                for i, item in enumerate(items):
                    print(f"\n--- Result {i+1} ---")
                    
                    title = item.get("title")
                    print(f"Title: {title}")
                    
                    # Look for speed limit data
                    # It might be in 'access', 'navigation' or directly in the item
                    # Let's print the whole item to see where it lands (if at all)
                    print("Full Item Object:")
                    print(json.dumps(item, indent=2))
                    
            else:
                print("No address items found.")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        # Sometimes error body contains details about unauthorized parameters
        try:
            print(e.read().decode())
        except:
            pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Hardcoded coordinates for Sunset Hwy test: 45.509139, -122.708
    # Using your HERE key
    API_KEY = "oLwzIij1iI5cX4wGQTS7889_CijiSC_x4tOzCbj4rYs" 
    LAT = 45.509139
    LON = -122.708
    
    test_here_geocoding(API_KEY, LAT, LON)
