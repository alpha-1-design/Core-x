import os
import threading
import time
import random
import uuid
from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

class DataStore:
    def __init__(self):
        self.connections = {}
        self.alerts = []
        self.data_points = {}
        self._init_demo_connections()
        self._start_simulation()

    def _init_demo_connections(self):
        demo_connections = [
            {"id": "us-west", "name": "SF Gateway", "type": "API Server", "lat": 37.7749, "lng": -122.4194, "url": "https://api.sanfrancisco.example"},
            {"id": "us-east", "name": "NYC Data Center", "type": "Data Center", "lat": 40.7128, "lng": -74.0060, "url": "https://datacenter.nyc.example"},
            {"id": "eu-london", "name": "London Cloud", "type": "Cloud Node", "lat": 51.5074, "lng": -0.1278, "url": "https://cloud.london.example"},
            {"id": "eu-frankfurt", "name": "Sensor Array Alpha", "type": "Sensor Array", "lat": 50.1109, "lng": 8.6821, "url": "https://sensors.frankfurt.example"},
            {"id": "asia-tokyo", "name": "Tokyo Satellite", "type": "Satellite Link", "lat": 35.6762, "lng": 139.6503, "url": "https://sat.tokyo.example"},
            {"id": "asia-singapore", "name": "Maritime Sensor", "type": "Maritime Sensor", "lat": 1.3521, "lng": 103.8198, "url": "https://maritime.sg.example"},
            {"id": "aus-sydney", "name": "Weather Station NSW", "type": "Weather Station", "lat": -33.8688, "lng": 151.2093, "url": "https://weather.sydney.example"},
            {"id": "africa-cape", "name": "Research Hub", "type": "Research Station", "lat": -33.9249, "lng": 18.4241, "url": "https://research.cape.example"},
        ]
        for conn in demo_connections:
            conn["status"] = "online"
            conn["lastPing"] = time.time()
            conn["metrics"] = {
                "cpu": random.randint(20, 80),
                "memory": random.randint(30, 70),
                "latency": random.randint(10, 150),
                "throughput": random.randint(100, 1000)
            }
            self.connections[conn["id"]] = conn
            self.data_points[conn["id"]] = []

    def _start_simulation(self):
        def simulate():
            while True:
                time.sleep(2)
                for conn_id, conn in self.connections.items():
                    conn["metrics"] = {
                        "cpu": max(0, min(100, conn["metrics"]["cpu"] + random.randint(-10, 10))),
                        "memory": max(0, min(100, conn["metrics"]["memory"] + random.randint(-5, 5))),
                        "latency": max(5, conn["metrics"]["latency"] + random.randint(-20, 20)),
                        "throughput": max(50, conn["metrics"]["throughput"] + random.randint(-100, 100))
                    }
                    conn["lastPing"] = time.time()
                    
                    if random.random() < 0.02:
                        old_status = conn["status"]
                        conn["status"] = random.choice(["online", "warning", "offline"])
                        if conn["status"] != old_status:
                            self.alerts.append({
                                "id": str(uuid.uuid4()),
                                "connectionId": conn_id,
                                "connectionName": conn["name"],
                                "type": conn["status"],
                                "message": f"{conn['name']} is now {conn['status']}",
                                "timestamp": time.time()
                            })
                            if len(self.alerts) > 50:
                                self.alerts = self.alerts[-50:]
                    
                    self.data_points[conn_id].append({
                        "timestamp": time.time(),
                        "cpu": conn["metrics"]["cpu"],
                        "memory": conn["metrics"]["memory"]
                    })
                    if len(self.data_points[conn_id]) > 60:
                        self.data_points[conn_id] = self.data_points[conn_id][-60:]

        thread = threading.Thread(target=simulate, daemon=True)
        thread.start()

    def get_connections(self):
        return list(self.connections.values())

    def get_connection(self, id):
        return self.connections.get(id)

    def add_connection(self, data):
        conn_id = str(uuid.uuid4())[:8]
        data["id"] = conn_id
        data["status"] = "online"
        data["lastPing"] = time.time()
        data["metrics"] = {"cpu": 0, "memory": 0, "latency": 0, "throughput": 0}
        self.connections[conn_id] = data
        self.data_points[conn_id] = []
        return data

    def update_connection(self, id, data):
        if id in self.connections:
            self.connections[id].update(data)
            return self.connections[id]
        return None

    def delete_connection(self, id):
        if id in self.connections:
            del self.connections[id]
            if id in self.data_points:
                del self.data_points[id]
            return True
        return False

    def ping_connection(self, id):
        conn = self.connections.get(id)
        if conn:
            conn["lastPing"] = time.time()
            conn["status"] = "online"
            return {"success": True, "latency": random.randint(10, 100)}
        return {"success": False, "error": "Connection not found"}

    def command_connection(self, id, cmd):
        conn = self.connections.get(id)
        if conn:
            return {"success": True, "output": f"Command '{cmd}' executed on {conn['name']}", "timestamp": time.time()}
        return {"success": False, "error": "Connection not found"}

    def get_metrics(self):
        return {id: conn["metrics"] for id, conn in self.connections.items()}

    def get_alerts(self):
        return self.alerts[-20:]

    def clear_alert(self, alert_id):
        self.alerts = [a for a in self.alerts if a["id"] != alert_id]
        return True


store = DataStore()


@app.route('/api/connections', methods=['GET'])
def get_connections():
    return jsonify(store.get_connections())


@app.route('/api/connections', methods=['POST'])
def add_connection():
    data = request.json
    return jsonify(store.add_connection(data)), 201


@app.route('/api/connections/<id>', methods=['PUT'])
def update_connection(id):
    data = request.json
    result = store.update_connection(id, data)
    if result:
        return jsonify(result)
    return jsonify({"error": "Not found"}), 404


@app.route('/api/connections/<id>', methods=['DELETE'])
def delete_connection(id):
    if store.delete_connection(id):
        return jsonify({"success": True})
    return jsonify({"error": "Not found"}), 404


@app.route('/api/connections/<id>/ping', methods=['POST'])
def ping_connection(id):
    return jsonify(store.ping_connection(id))


@app.route('/api/connections/<id>/command', methods=['POST'])
def command_connection(id):
    cmd = request.json.get("command", "")
    return jsonify(store.command_connection(id, cmd))


@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    return jsonify(store.get_metrics())


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    return jsonify(store.get_alerts())


@app.route('/api/alerts/<alert_id>', methods=['DELETE'])
def clear_alert(alert_id):
    store.clear_alert(alert_id)
    return jsonify({"success": True})


@app.route('/api/data/<id>', methods=['GET'])
def get_connection_data(id):
    points = store.data_points.get(id, [])
    return jsonify(points)


@app.route('/')
def index():
    with open('index.html', 'r') as f:
        return f.read(), 200, {'Content-Type': 'text/html'}


@app.route('/app.js')
def app_js():
    with open('app.js', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}


@app.route('/services.js')
def services_js():
    with open('services.js', 'r') as f:
        return f.read(), 200, {'Content-Type': 'application/javascript'}


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)