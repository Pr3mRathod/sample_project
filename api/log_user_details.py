import os
import json
import socket
import platform
import psutil
import uuid
import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# MongoDB connection
try:
    MONGO_URI = os.getenv("MONGODB_URI")
    if not MONGO_URI:
        raise ValueError("MONGODB_URI environment variable is not set")
    mongo_client = MongoClient(MONGO_URI)
    db = mongo_client["user_data_db"]
    collection = db["user_details"]
except Exception as e:
    print(f"Error initializing MongoDB: {e}")

app = Flask(__name__, static_folder='../public')
CORS(app)

@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        print(f"Error serving index.html: {e}")
        return jsonify({"error": f"Could not serve index.html: {e}"}), 500

def get_ip_info():
    try:
        response = requests.get("https://ipinfo.io")
        response.raise_for_status()
        data = response.json()
        return {
            "public_ip": data.get("ip"),
            "city": data.get("city"),
            "region": data.get("region"),
            "country": data.get("country"),
            "location": data.get("loc"),
            "organization": data.get("org"),
            "postal": data.get("postal"),
            "timezone": data.get("timezone"),
        }
    except Exception as e:
        print(f"Error fetching IP info: {e}")
        return {"error": f"Could not fetch IP info: {e}"}

def get_private_ip():
    try:
        hostname = socket.gethostname()
        private_ip = socket.gethostbyname(hostname)
        return {"private_ip": private_ip, "hostname": hostname}
    except Exception as e:
        print(f"Error fetching private IP: {e}")
        return {"error": f"Could not fetch private IP: {e}"}

def get_mac_address():
    try:
        mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff)
                        for ele in range(0, 8 * 6, 8)][::-1])
        return {"mac_address": mac}
    except Exception as e:
        print(f"Error fetching MAC address: {e}")
        return {"error": f"Could not fetch MAC address: {e}"}

def get_system_info():
    try:
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "os_release": platform.release(),
            "architecture": platform.architecture()[0],
            "processor": platform.processor(),
            "machine": platform.machine(),
        }
    except Exception as e:
        print(f"Error fetching system info: {e}")
        return {"error": f"Could not fetch system info: {e}"}

def get_cpu_info():
    try:
        return {
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_freq": psutil.cpu_freq()._asdict() if psutil.cpu_freq() else None,
            "cpu_usage": psutil.cpu_percent(interval=1),
        }
    except Exception as e:
        print(f"Error fetching CPU info: {e}")
        return {"error": f"Could not fetch CPU info: {e}"}

def get_memory_info():
    try:
        memory = psutil.virtual_memory()
        return {
            "total_memory": memory.total,
            "available_memory": memory.available,
            "used_memory": memory.used,
            "memory_percentage": memory.percent,
        }
    except Exception as e:
        print(f"Error fetching memory info: {e}")
        return {"error": f"Could not fetch memory info: {e}"}

def get_disk_info():
    try:
        disk = psutil.disk_usage('/')
        return {
            "total_disk_space": disk.total,
            "used_disk_space": disk.used,
            "free_disk_space": disk.free,
            "disk_usage_percentage": disk.percent,
        }
    except Exception as e:
        print(f"Error fetching disk info: {e}")
        return {"error": f"Could not fetch disk info: {e}"}

def get_network_info():
    try:
        interfaces = psutil.net_if_addrs()
        net_info = {}
        for interface, addrs in interfaces.items():
            net_info[interface] = [{"address": addr.address, "family": str(addr.family)} for addr in addrs]
        return net_info
    except Exception as e:
        print(f"Error fetching network info: {e}")
        return {"error": f"Could not fetch network info: {e}"}

def get_browser_info(request_headers):
    try:
        return {"user_agent": request_headers.get("User-Agent")}
    except Exception as e:
        print(f"Error fetching user-agent: {e}")
        return {"error": f"Could not fetch user-agent: {e}"}

def collect_user_details(request):
    data = {}
    try:
        data.update(get_ip_info())
        data.update(get_private_ip())
        data.update(get_mac_address())
        data.update(get_system_info())
        data.update(get_cpu_info())
        data.update(get_memory_info())
        data.update(get_disk_info())
        data["network_info"] = get_network_info()
        data.update(get_browser_info(request.headers))
    except Exception as e:
        print(f"Error collecting user details: {e}")
    return data

@app.route('/api/log_user_details', methods=['POST'])
def log_user_details():
    try:
        print("Received request: ", request.json)  # Log request data
        user_details = collect_user_details(request)
        print("Collected user details: ", user_details)  # Log collected details
        
        # Attempt to insert into MongoDB
        insert_result = collection.insert_one(user_details)
        print("Insert result: ", insert_result.inserted_id)  # Log MongoDB insertion result
        
        return jsonify({"message": "User details collected and stored successfully"}), 200
    except PyMongoError as e:
        print(f"Database error: {e}")  # Log database error
        return jsonify({"error": f"Database error: {e}"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")  # Log unexpected error
        return jsonify({"error": f"An unexpected error occurred: {e}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
