from flask import Flask, request, jsonify
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, firestore
from geopy.distance import geodesic

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

app = Flask(__name__)

@app.route('/check-anomaly', methods=['POST'])
def check_anomaly():
    data = request.json  # Expecting {"userId": "UID123", "location_history": [{"lat":..., "lng":..., "timestamp":...}, ...]}
    location_history = data['location_history']
    alerts = []

    # ---------------- Rule 1: No movement for 10 minutes ----------------
    if len(location_history) >= 2:
        first_loc = location_history[0]
        last_loc = location_history[-1]
        dist = geodesic((first_loc['lat'], first_loc['lng']),
                        (last_loc['lat'], last_loc['lng'])).meters
        
        if dist < 10:  # threshold in meters
            # Assign severity based on distance
            if dist < 2:
                severity = "high"
            elif dist < 5:
                severity = "medium"
            else:
                severity = "low"

            alerts.append({
                'userId': data['userId'],
                'type': 'no_movement',
                'location': last_loc,
                'timestamp': datetime.now().isoformat(),
                'severity': severity
            })

    # ---------------- Rule 2: Prolonged inactivity (30 mins or more) ----------------
    if len(location_history) >= 2:
        first_time = datetime.fromisoformat(location_history[0]['timestamp'])
        last_time = datetime.fromisoformat(location_history[-1]['timestamp'])
        time_diff = (last_time - first_time).total_seconds() / 60  # in minutes

        if time_diff >= 30:
            alerts.append({
                'userId': data['userId'],
                'type': 'prolonged_inactivity',
                'location': location_history[-1],
                'timestamp': datetime.now().isoformat(),
                'severity': 'high'
            })

    # ---------------- Send alerts to Firebase ----------------
    for alert in alerts:
        db.collection('alerts').add(alert)

    return jsonify({'status': 'ok', 'alerts_generated': len(alerts)})

if __name__ == "__main__":
    app.run(debug=True)
