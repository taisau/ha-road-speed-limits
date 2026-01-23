import urllib.request
import urllib.parse
import urllib.error
import json
import sys

# Production URLs
OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"
TOMTOM_REVGEO_URL = "https://api.tomtom.com/search/2/reverseGeocode"
HERE_REVGEO_URL = "https://revgeocode.search.hereapi.com/v1/revgeocode"

def test_osm(lat, lon):
    print(f"\n--- Testing OpenStreetMap (Lat: {lat}, Lon: {lon}) ---")
    query = f'[out:json];way(around:50,{lat},{lon})["maxspeed"];out body;'
    data = urllib.parse.urlencode({"data": query}).encode()
    try:
        req = urllib.request.Request(OSM_OVERPASS_URL, data=data)
        with urllib.request.urlopen(req, timeout=10) as response:
            res = json.loads(response.read().decode())
            elements = res.get("elements", [])
            if elements:
                match = elements[0]
                tags = match.get("tags", {})
                raw_limit = tags.get('maxspeed', '')
                
                # Sanitization Logic
                clean_limit = raw_limit.replace("mph", "").replace("km/h", "").replace("kmh", "").strip()
                try:
                    sanitized_limit = int(round(float(clean_limit)))
                except:
                    sanitized_limit = raw_limit

                print(f"Road Name: {tags.get('name', 'Unknown')}")
                print(f"Raw Limit: {raw_limit}")
                print(f"Sanitized Limit: {sanitized_limit}")
                print(f"Timezone: {tags.get('timezone', 'Not found in tags')}")
            else:
                print("No maxspeed found in OSM.")
    except Exception as e:
        print(f"Error: {e}")

def test_here(api_key, lat, lon):
    print(f"\n--- Testing HERE Maps Search API v7 (Lat: {lat}, Lon: {lon}) ---")
    params = {"at": f"{lat},{lon}", "apiKey": api_key, "showNavAttributes": "speedLimits", "lang": "en-US"}
    url = f"{HERE_REVGEO_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            res = json.loads(response.read().decode())
            items = res.get("items", [])
            if items:
                match = items[0]
                addr = match.get("address", {})
                nav = match.get("navigationAttributes", {})
                limits = nav.get("speedLimits", [])
                
                raw_speed = limits[0].get("maxSpeed") if limits else "None"
                
                # Sanitization Logic
                try:
                    sanitized_limit = int(round(float(raw_speed)))
                except:
                    sanitized_limit = raw_speed

                print(f"Road Name: {addr.get('street', match.get('title'))}")
                print(f"Raw Limit: {raw_speed}")
                print(f"Sanitized Limit: {sanitized_limit}")
                print(f"Timezone: {match.get('timezone', 'Not found in match')}")
            else:
                print("No HERE address found.")
    except Exception as e:
        print(f"Error: {e}")

def test_tomtom(api_key, lat, lon):
    print(f"\n--- Testing TomTom Search API v2 (Lat: {lat}, Lon: {lon}) ---")
    url = f"{TOMTOM_REVGEO_URL}/{lat},{lon}.json"
    params = {"key": api_key, "returnSpeedLimit": "true", "radius": 50}
    try:
        with urllib.request.urlopen(f"{url}?{urllib.parse.urlencode(params)}", timeout=10) as response:
            res = json.loads(response.read().decode())
            addresses = res.get("addresses", [])
            if addresses:
                match = addresses[0]
                addr = match.get("address", {})
                raw_limit = addr.get('speedLimit', '')
                
                # Sanitization Logic
                clean_limit = raw_limit.upper().replace("MPH", "").replace("KM/H", "").replace("KMH", "").strip()
                try:
                    sanitized_limit = int(round(float(clean_limit)))
                except:
                    sanitized_limit = raw_limit

                road = addr.get("street") or ", ".join(addr.get("routeNumbers", []))
                print(f"Road Name: {road}")
                print(f"Raw Limit: {raw_limit}")
                print(f"Sanitized Limit: {sanitized_limit}")
                print(f"Timezone: {match.get('address', {}).get('timeZone', 'Not found in address')}")
            else:
                print("No TomTom address found.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    LAT, LON = 45.509139, -122.708
    HERE_KEY = "oLwzIij1iI5cX4wGQTS7889_CijiSC_x4tOzCbj4rYs"
    TOMTOM_KEY = "9mUslvD61yuojwtQiMdjDPEyIL4sDqdh"
    
    print("=== Road Speed Limits Final Production Test ===")
    test_osm(LAT, LON)
    test_here(HERE_KEY, LAT, LON)
    test_tomtom(TOMTOM_KEY, LAT, LON)
