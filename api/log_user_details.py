import os
import json
import socket
import platform
import psutil
import uuid
import requests
from pymongo import MongoClient
from pymongo.errors import PyMongoError
from flask import Flask, request, send_from_directory, Response
from flask_cors import CORS

# Load environment variables
from dotenv import load_dotenv

load_dotenv()  # Load the .env file from the root folder

# MongoDB setup
try:
    MONGO_URI = os.getenv("MONGODB_URI")
    if not MONGO_URI:
        raise ValueError("MONGODB_URI environment variable is not set")
    mongo_client = MongoClient(MONGO_URI)
    mongo_client.server_info()  # Test connection
    print("MongoDB connection successful")
except Exception as e:
    print(f"MongoDB connection failed: {e}")
    raise

# Initialize Flask app
app = Flask(__name__, static_folder='../public')  # Serve from the public folder
CORS(app)

# MongoDB collection
db = mongo_client["user_logs"]
collection = db["logs"]

@app.route('/')
def index():
    try:
        # Serve the index.html from the 'public' folder
        return send_from_directory(app.static_folder, 'index.html')
    except Exception as e:
        return Response(
            json.dumps({"error": f"Could not serve index.html: {e}"}),
            status=500,
            mimetype='application/json'
        )

# Collect user details function (excluding network info, as it is now fetched via frontend)
def collect_user_details(request):
    data = {}
    try:
        # Collect user details sent from frontend
        data["user_agent"] = request.headers.get("User-Agent")
        data["timestamp"] = request.json.get("timestamp")
        data["browser_language"] = request.json.get("browser_language")
        data["screen_width"] = request.json.get("screen_width")
        data["screen_height"] = request.json.get("screen_height")
        data["timezone"] = request.json.get("timezone")
        data["battery_level"] = request.json.get("battery_level")

        # Add additional system info
        data.update(get_system_info())
        data.update(get_cpu_info())
        data.update(get_memory_info())
        data.update(get_disk_info())

    except Exception as e:
        print(f"Error collecting user details: {e}")
    return data

@app.route('/api/log_user_details', methods=['POST'])
def log_user_details():
    try:
        print("Request received:", request.json)  # Log the incoming request
        user_details = collect_user_details(request)
        print("Collected user details:", user_details)  # Log collected details
        
        # Insert user details into MongoDB collection
        result = collection.insert_one(user_details)
        print("MongoDB insert result:", result.inserted_id)  # Log the result of the insert
        
        return Response(
            json.dumps({"message": "Alert Shown Successfully!"}),
            status=200,
            mimetype='application/json'
        )
    except PyMongoError as e:
        print(f"MongoDB error: {e}")  # Log MongoDB errors
        return Response(
            json.dumps({"error": f"Database error: {e}"}),
            status=500,
            mimetype='application/json'
        )
    except Exception as e:
        print(f"Unexpected error: {e}")  # Log unexpected errors
        return Response(
            json.dumps({"error": f"Unexpected error: {e}"}),
            status=500,
            mimetype='application/json'
        )

# Helper functions to collect various system and user details
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

# Run the app on port 5000
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
