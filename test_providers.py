import urllib.request
import urllib.parse
import urllib.error
import json
import ssl
import sys

# Constants from const.py
TOMTOM_API_URL = "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
HERE_API_URL = "https://data.traffic.hereapi.com/v7/flow"

def test_tomtom(api_key, lat, lon):
    print(f"\n--- Testing TomTom (Lat: {lat}, Lon: {lon}) ---")
    params = {
        "point": f"{lat},{lon}",
        "key": api_key,
        "unit": "MPH",
    }
    url = f"{TOMTOM_API_URL}?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("Status: Success (200)")
            # Parse like the provider
            try:
                flow_data = data.get("flowSegmentData", {})
                speed_limit = flow_data.get("speedLimit")
                road_name = flow_data.get("frc")
                print(f"Speed Limit: {speed_limit}")
                print(f"Road Class: {road_name}")
                print("Raw Data snippet:", str(data)[:200] + "...")
            except Exception as e:
                print(f"Parsing Error: {e}")
                print("Raw Data:", data)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"Error: {e}")

def test_here(api_key, lat, lon):
    print(f"\n--- Testing HERE Maps (Lat: {lat}, Lon: {lon}) ---")
    params = {
        "locationReferencing": "shape",
        "in": f"circle:{lat},{lon};r=50",
        "apiKey": api_key,
    }
    url = f"{HERE_API_URL}?{urllib.parse.urlencode(params)}"
    
    try:
        # Create SSL context to handle certificates if needed, usually default is fine
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(url, context=ctx, timeout=10) as response:
            data = json.loads(response.read().decode())
            print("Status: Success (200)")
            # Parse like the provider
            try:
                results = data.get("results", [])
                if results:
                    first = results[0]
                    flow = first.get("currentFlow", {})
                    limit = flow.get("speedLimit")
                    loc = first.get("location", {})
                    desc = loc.get("description")
                    print(f"Speed Limit: {limit} km/h")
                    print(f"Road: {desc}")
                else:
                    print("No results found in area.")
                print("Raw Data snippet:", str(data)[:200] + "...")
            except Exception as e:
                print(f"Parsing Error: {e}")
                print("Raw Data:", data)
    except urllib.error.HTTPError as e:
        print(f"HTTP Error: {e.code} - {e.reason}")
        print(e.read().decode())
    except Exception as e:
        print(f"Error: {e}")

def main():
    print("--- Road Speed Limits API Tester ---")
    print("This script tests the API connectivity and Keys directly using standard libraries.")
    
    # Get Location
    print("\nEnter test coordinates (default: 40.7580, -73.9855 [Times Square, NYC])")
    lat_str = input("Latitude: ").strip()
    lon_str = input("Longitude: ").strip()
    
    if not lat_str:
        lat = 40.7580
    else:
        lat = float(lat_str)
        
    if not lon_str:
        lon = -73.9855
    else:
        lon = float(lon_str)

    # Test HERE
    here_key = input("\nEnter HERE API Key (leave empty to skip): ").strip()
    if here_key:
        test_here(here_key, lat, lon)
    else:
        print("Skipped HERE.")

    # Test TomTom
    tomtom_key = input("\nEnter TomTom API Key (leave empty to skip): ").strip()
    if tomtom_key:
        test_tomtom(tomtom_key, lat, lon)
    else:
        print("Skipped TomTom.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nAborted.")