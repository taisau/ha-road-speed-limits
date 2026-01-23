import urllib.request
import urllib.parse
import urllib.error
import json
import sys

# HERE Reverse Geocoding API URL
HERE_REVGEO_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"

def test_here_timezone(api_key, lat, lon):
    print(f"\n--- Testing HERE Maps Timezone (Lat: {lat}, Lon: {lon}) ---")
    
    params = {
        "at": f"{lat},{lon}",
        "apiKey": api_key,
        "show": "tz",  # Timezone
        "showNavAttributes": "speedLimits", # Speed Limits
        "lang": "en-US"
    }
    
    url = f"{HERE_REVGEO_URL}?{urllib.parse.urlencode(params)}"
    print(f"Request URL: {url.replace(api_key, 'HIDDEN_KEY')}")
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("Status: Success (200)")
            
            items = data.get("items", [])
            if items:
                match = items[0]
                print(f"\n--- Result 1 ---")
                print(f"Title: {match.get('title')}")
                
                # Check for Timezone
                timezone = match.get("timeZone")
                if timezone:
                    print("Timezone Data Found:")
                    print(json.dumps(timezone, indent=2))
                
                # Check for Speed Limits
                nav = match.get("navigationAttributes", {})
                limits = nav.get("speedLimits", [])
                if limits:
                    print("Speed Limits Found:")
                    print(json.dumps(limits, indent=2))
                else:
                    print("No Speed Limits found.")
            else:
                print("No items found.")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        try:
            print(e.read().decode())
        except:
            pass
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    LAT, LON = 45.509139, -122.708
    HERE_KEY = "oLwzIij1iI5cX4wGQTS7889_CijiSC_x4tOzCbj4rYs"
    
    test_here_timezone(HERE_KEY, LAT, LON)
