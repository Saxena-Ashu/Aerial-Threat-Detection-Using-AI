from flask import Flask, render_template, request, jsonify
import random
import time
import math
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import io
import base64

app = Flask(__name__)

# Generate random location for threat data
def generate_random_location():
    return [random.uniform(-180, 180), random.uniform(-90, 90)]

# Get the place name for coordinates
def get_place_name(coordinates, geolocator):
    try:
        location = geolocator.reverse(coordinates, language='en', timeout=5)
        return location.address if location else "Unknown Location"
    except (GeocoderTimedOut, GeocoderServiceError):
        return "Location Service Timeout/Unavailable"

# Data for threat prediction
def data_for_threat_prediction(user_location):
    origin_location = generate_random_location()
    impact_location = [user_location[0] + random.uniform(-1, 1), user_location[1] + random.uniform(-1, 1)]
    threat_type = random.choice(["Missile", "Artillery"])
    timestamp = time.time()
    return {
        "origin_location": origin_location,
        "impact_location": impact_location,
        "threat_type": threat_type,
        "timestamp": timestamp
    }

# Calculate distance between two points
def calculate_distance(point1, point2):
    lon1, lat1 = map(math.radians, point1)
    lon2, lat2 = map(math.radians, point2)
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    radius_earth = 6371  # Earth's radius in kilometers
    return radius_earth * c

# Predict threat and safe routes based on user location
def predict_threat_and_safe_routes(user_location, threat_data):
    impact_location = threat_data["impact_location"]
    distance = calculate_distance(user_location, impact_location)
    
    # Threat Classification
    if distance <= 100:
        threat_level = "High Threat" 
    else:
        threat_level = "Low Threat"
    
    if threat_data["threat_type"] == "Missile":
        impact_radius = 200
    else:
        impact_radius = 50
        
    if distance > impact_radius:
        safe_zone = "Safe Route Nearby"
    else:
        safe_zone = "Immediate Danger Zone"
    
    return threat_level, impact_location, impact_radius, safe_zone

# View the map with the threat details
def view_map(user_location, origin_location, impact_location, impact_radius, threat_type, threat_level):
    fig, ax = plt.subplots(figsize=(10, 6), subplot_kw={'projection': ccrs.PlateCarree()})
    ax.add_feature(cfeature.LAND, facecolor='lightgray')
    ax.add_feature(cfeature.OCEAN, facecolor='lightblue')
    ax.add_feature(cfeature.BORDERS, edgecolor='gray')
    ax.add_feature(cfeature.COASTLINE, linewidth=1.0)
    ax.gridlines(draw_labels=True, color="gray", alpha=0.5, linestyle="--")
    buffer = 5 
    min_lon = min(user_location[0], origin_location[0], impact_location[0]) - buffer
    max_lon = max(user_location[0], origin_location[0], impact_location[0]) + buffer
    min_lat = min(user_location[1], origin_location[1], impact_location[1]) - buffer
    max_lat = max(user_location[1], origin_location[1], impact_location[1]) + buffer
    ax.set_extent([min_lon, max_lon, min_lat, max_lat])
    
    threat_color = 'red' if threat_level == "High Threat" else 'orange'
    ax.plot(user_location[0], user_location[1], 'bo', markersize=10, label="User Location")
    ax.text(user_location[0] + 0.2, user_location[1], "User", fontsize=9, color='blue')
    ax.plot(origin_location[0], origin_location[1], 'go', markersize=10, label="Threat Origin")
    ax.text(origin_location[0] + 0.2, origin_location[1], "Origin", fontsize=9, color='green')
    ax.plot(impact_location[0], impact_location[1], 'o', color=threat_color, markersize=10, label="Impact Location")
    ax.text(impact_location[0] + 0.2, impact_location[1], "Impact", fontsize=9, color=threat_color)
    ax.plot([origin_location[0], impact_location[0]], [origin_location[1], impact_location[1]],
            linestyle='--', linewidth=2, color=threat_color, label="Threat Path")
    
    impact_radius_degrees = impact_radius / 111
    impact_circle = plt.Circle((impact_location[0], impact_location[1]), radius=impact_radius_degrees,
                               transform=ccrs.PlateCarree(),
                               color=threat_color, alpha=0.3, edgecolor="black", linewidth=1.5,
                               label="Impact Radius")
    ax.add_patch(impact_circle)

    ax.set_title("Threat Detection Map", fontsize=14, fontweight='bold', color='darkred')
    ax.legend(loc='upper left', bbox_to_anchor=(1.05, 1), borderaxespad=0, fontsize=9, title="Legend")
    plt.tight_layout()

    # Save to a BytesIO buffer and encode to base64
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()

    return img_base64

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/interface')
def interface():
    return render_template('threat_detection_interface.html')

@app.route('/accurate', methods=['POST'])
def accurate():
    try:
        user_location = [
            float(request.form['longitude']),
            float(request.form['latitude'])
        ]
        geolocator = Nominatim(user_agent="threat-detection-system")
        user_place = get_place_name(user_location[::-1], geolocator)
        
        threat_data = data_for_threat_prediction(user_location)
        origin_location = threat_data["origin_location"]
        threat_level, impact_location, impact_radius, safe_zone = predict_threat_and_safe_routes(user_location, threat_data)

        map_image = view_map(user_location, origin_location, impact_location, impact_radius, threat_data["threat_type"], threat_level)
        
        return jsonify({'map_image': map_image, 'user_location': user_location, 'threat_level': threat_level, 'safe_zone': safe_zone})

    except Exception as e:
        return str(e), 500
if __name__ == '__main__':
    app.run(debug=True, port=5001)

