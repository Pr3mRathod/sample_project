import os
import json
import platform
import psutil
import uuid
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from flask import Flask, request, send_from_directory, Response
from flask_cors import CORS

# Load environment variables
from dotenv import load_dotenv

load_dotenv()

# MongoDB setup
try:
    MONGO_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017")  # Default URI fallback
    mongo_client = MongoClient(MONGO_URI)
    mongo_client.server_info()  # Test connection
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    raise

# Initialize Flask app
app = Flask(__name__, static_folder='../public')
CORS(app)

# MongoDB collection
db = mongo_client["user_logs"]
collection = db["logs"]

@app.route('/')
def index():
    try:
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        return Response(
            json.dumps({"error": f"Could not serve index.html: {e}"}),
            status=500,
            mimetype='application/json'
        )

def collect_user_details(request):
    data = {}
    try:
        # Required fields validation
        required_fields = [
            "timestamp", "browser_language", "screen_width",
            "screen_height", "timezone", "battery_level", "ip",
            "latitude", "longitude"
        ]
        for field in required_fields:
            if field not in request.json:
                raise ValueError(f"Missing required field: {field}")

        # Collect user details sent from frontend
        data = {field: request.json.get(field) for field in required_fields}
        data["user_agent"] = request.headers.get("User-Agent")

        # Collect system information
        data["system_info"] = get_system_info()
        data["cpu_info"] = get_cpu_info()
        data["memory_info"] = get_memory_info()
        data["disk_info"] = get_disk_info()

        # Generate a unique session ID
        data["session_id"] = str(uuid.uuid4())
    except ValueError as ve:
        print(f"Validation error: {ve}")
        data["error"] = str(ve)
    except Exception as e:
        print(f"Error collecting user details: {e}")
        data["error"] = f"Unexpected error: {e}"
    return data

@app.route('/api/log_user_details', methods=['POST'])
def log_user_details():
    try:
        if not request.is_json:
            raise ValueError("Request content type must be JSON")

        user_details = collect_user_details(request)

        if "error" in user_details:
            raise ValueError(user_details["error"])

        result = collection.insert_one(user_details)
        return Response(
            json.dumps({"message": "Data sent successfully!", "id": str(result.inserted_id)}),
            status=200,
            mimetype='application/json'
        )
    except ValueError as ve:
        print(f"Validation error: {ve}")
        return Response(
            json.dumps({"error": f"Validation error: {ve}"}),
            status=400,
            mimetype='application/json'
        )
    except PyMongoError as pe:
        print(f"MongoDB error: {pe}")
        return Response(
            json.dumps({"error": f"Database error: {pe}"}),
            status=500,
            mimetype='application/json'
        )
    except Exception as e:
        print(f"Unexpected error: {e}")
        return Response(
            json.dumps({"error": f"Unexpected error: {e}"}),
            status=500,
            mimetype='application/json'
        )

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
        freq = psutil.cpu_freq()
        return {
            "cpu_count": psutil.cpu_count(logical=True),
            "cpu_freq": freq._asdict() if freq else None,
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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
