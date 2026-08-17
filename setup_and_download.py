import os
import sys
import json
import urllib.request
import urllib.parse

# 1. Define paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SUB_DIRS = [
    "GIS",
    "traffic",
    "parking",
    "pedestrian",
    "public_transit",
    "business",
    "weather",
    "population",
    "land_use",
    "historical_policy"
]

def setup_directories():
    print("Setting up directory structure...")
    for sub in SUB_DIRS:
        path = os.path.join(DATA_DIR, sub)
        os.makedirs(path, exist_ok=True)
        print(f"Created: {path}")

def install_dependencies():
    print("Installing python-geojson, requests, and pandas if not present...")
    import subprocess
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests", "pandas", "geojson"])
        print("Required Python packages installed successfully.")
    except Exception as e:
        print(f"Error installing packages: {e}. Attempting to run with standard libraries.")

def download_taipei_parking():
    print("\n--- Downloading Taipei Parking Data ---")
    # Taipei Open Data Parking static and dynamic links
    static_url = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_alldesc.json"
    dynamic_url = "https://tcgbusfs.blob.core.windows.net/blobtcmsv/TCMSV_allavailable.json"
    
    parking_dir = os.path.join(DATA_DIR, "parking")
    
    # Download static parking descriptions
    static_path = os.path.join(parking_dir, "taipei_parking_static.json")
    print(f"Downloading static parking data from {static_url}...")
    try:
        urllib.request.urlretrieve(static_url, static_path)
        print(f"Saved static parking data to {static_path}")
    except Exception as e:
        print(f"Failed to download static parking data: {e}")
        
    # Download dynamic parking availability
    dynamic_path = os.path.join(parking_dir, "taipei_parking_dynamic.json")
    print(f"Downloading dynamic parking data from {dynamic_url}...")
    try:
        urllib.request.urlretrieve(dynamic_url, dynamic_path)
        print(f"Saved dynamic parking data to {dynamic_path}")
    except Exception as e:
        print(f"Failed to download dynamic parking data: {e}")

def query_overpass(query_string):
    import requests
    # Use Taiwan's NCHC Overpass mirror if the main one rate-limits or blocks
    overpass_urls = [
        "https://overpass.nchc.org.tw/api/interpreter",
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass-api.de/api/interpreter"
    ]
    
    headers = {
        'User-Agent': 'TaipeiXinyiSimulatorDataDownloader/2.0 (contact: contact@xinyi-simulator.local)',
        'Accept': 'application/json, text/plain, */*'
    }
    
    for url in overpass_urls:
        print(f"Querying Overpass API via {url}...")
        try:
            response = requests.post(url, data={'data': query_string}, headers=headers, timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Overpass API ({url}) returned status {response.status_code}")
        except Exception as e:
            print(f"Request to {url} failed: {e}")
    return None

def download_osm_xinyi_impact_data():
    print("\n--- Downloading Xinyi impact-area OpenStreetMap Data via Overpass API ---")
    # Buffer around the influence area bounded by Zhongxiao E. Rd. Sec. 5,
    # Keelung Rd. Sec. 1, Songde Rd., and Xinyi Rd. Sec. 5.
    # This bbox is a download envelope, not the policy boundary. See SIMULATION_SCOPE.md.
    bbox = "25.031,121.553,25.044,121.580"
    
    gis_dir = os.path.join(DATA_DIR, "GIS")
    transit_dir = os.path.join(DATA_DIR, "public_transit")
    
    # 1. Download Road Network
    print("Fetching Xinyi impact-area road network...")
    road_query = f"""
    [out:json][timeout:90];
    (
      way["highway"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    roads_data = query_overpass(road_query)
    if roads_data:
        roads_path = os.path.join(gis_dir, "xinyi_impact_road_network.json")
        with open(roads_path, "w", encoding="utf-8") as f:
            json.dump(roads_data, f, ensure_ascii=False, indent=2)
        print(f"Saved road network to {roads_path} ({len(roads_data.get('elements', []))} elements)")
        
        # Convert to a basic GeoJSON for convenience
        try:
            nodes = {el["id"]: el for el in roads_data.get("elements", []) if el["type"] == "node"}
            ways = [el for el in roads_data.get("elements", []) if el["type"] == "way"]
            
            geojson = {
                "type": "FeatureCollection",
                "features": []
            }
            for w in ways:
                coords = []
                valid = True
                for nd_id in w.get("nodes", []):
                    if nd_id in nodes:
                        coords.append([nodes[nd_id]["lon"], nodes[nd_id]["lat"]])
                    else:
                        valid = False
                if valid and len(coords) > 1:
                    geojson["features"].append({
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": coords
                        },
                        "properties": w.get("tags", {})
                    })
            
            geojson_path = os.path.join(gis_dir, "xinyi_impact_road_network.geojson")
            with open(geojson_path, "w", encoding="utf-8") as f:
                json.dump(geojson, f, ensure_ascii=False, indent=2)
            print(f"Generated GeoJSON road network to {geojson_path}")
        except Exception as e:
            print(f"Failed to generate GeoJSON road network: {e}")

    # 2. Download POIs
    print("Fetching POIs (amenities, shops, food)...")
    poi_query = f"""
    [out:json][timeout:90];
    (
      node["amenity"]({bbox});
      node["shop"]({bbox});
      node["tourism"]({bbox});
      way["amenity"]({bbox});
      way["shop"]({bbox});
      way["tourism"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    poi_data = query_overpass(poi_query)
    if poi_data:
        poi_path = os.path.join(gis_dir, "xinyi_impact_pois.json")
        with open(poi_path, "w", encoding="utf-8") as f:
            json.dump(poi_data, f, ensure_ascii=False, indent=2)
        print(f"Saved POIs to {poi_path} ({len(poi_data.get('elements', []))} elements)")

    # 3. Download Transit Nodes (MRT & Bus stops)
    print("Fetching Xinyi impact-area public transit nodes (MRT & Bus stops)...")
    transit_query = f"""
    [out:json][timeout:90];
    (
      node["highway"="bus_stop"]({bbox});
      node["railway"="station"]({bbox});
      node["railway"="subway_entrance"]({bbox});
    );
    out body;
    >;
    out skel qt;
    """
    transit_data = query_overpass(transit_query)
    if transit_data:
        transit_path = os.path.join(transit_dir, "xinyi_impact_transit_nodes.json")
        with open(transit_path, "w", encoding="utf-8") as f:
            json.dump(transit_data, f, ensure_ascii=False, indent=2)
        print(f"Saved transit nodes to {transit_path} ({len(transit_data.get('elements', []))} elements)")

def main():
    setup_directories()
    download_taipei_parking()
    download_osm_xinyi_impact_data()
    print("\nAll tasks completed successfully!")

if __name__ == "__main__":
    main()
