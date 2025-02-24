from flask import Flask,send_from_directory,request,jsonify
import os
from openai import OpenAI
from flask_cors import CORS
from flask_pymongo import PyMongo
import bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, verify_jwt_in_request
from functools import wraps
from flask_jwt_extended import verify_jwt_in_request, JWTManager, exceptions
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import json
from static import staticfilepath
basedir=os.path.abspath(os.path.dirname(__file__))

print(basedir)
# Load config file
def load_config():
    with open(os.path.join(staticfilepath, "config.json")) as config_file:
        return json.load(config_file)

def save_config(data):
    with open(os.path.join(staticfilepath, "config.json"), "w") as config_file:
        json.dump(data, config_file, indent=4)

config = load_config()

aiclient = OpenAI(api_key=config["openai_api_key"])




app=Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/questionbanks_db"  # Change to your MongoDB URI
mongo = PyMongo(app)

app.config["ASSESSMENTS_MONGO_URI"] = "mongodb://localhost:27017/assessments_db"  # Different database
mongo_assessments = PyMongo(app, uri=app.config["ASSESSMENTS_MONGO_URI"])
CORS(app)


users_collection = mongo_assessments.db['users']

app.config['JWT_SECRET_KEY'] = 'onekeygreatkey'
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False


app.config["API_KEY"] = config["app_api_key"]

jwt = JWTManager(app)

@app.route('/register', methods=['POST'])
def register():
    
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    # Check if username already exists
    if users_collection.find_one({"username": username}):
        return jsonify({"msg": "Username already taken"}), 400

    # Hash the password before storing it
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    # Store the new user in MongoDB
    users_collection.insert_one({
        "username": username,
        "password": hashed_password
    })

    return jsonify({"msg": "User registered successfully"}), 201

@app.route('/login', methods=['POST'])
def login():
    username = request.json.get('username', None)
    password = request.json.get('password', None)

    # Retrieve the user from the database
    user = users_collection.find_one({"username": username})

    if not user or not bcrypt.checkpw(password.encode('utf-8'), user['password']):
        return jsonify({"msg": "Invalid username or password"}), 401

    # Create a new JWT token for the user
    access_token = create_access_token(identity=username)
    
    return jsonify(access_token=access_token), 200


@app.before_request
def check_jwt():
    print(request.path)

    if request.method == 'OPTIONS':
        return '', 204 
    # Allow certain routes to bypass JWT check (e.g., login and register)
    if request.path in ['/login', '/register']:
        return None  # Bypass JWT validation for these routes

      # Allow certain routes to be accessed using API Key instead of JWT
    if request.path.startswith('/assessments/') or request.path.startswith('/evaluate/') or request.path.startswith("/code-assessments") or request.path.startswith('/testdetails/'):  # Add your paths here
        try:
            authorization = request.headers['Authorization']
        except KeyError as e:
            api_key = request.headers['x-api-key']
       
            print(api_key)
            if api_key and api_key == app.config['API_KEY']:
                return None  # Valid API key, allow access
            else:
                return jsonify({"msg": "Missing or invalid API key"}), 401
    
    
    # For all other routes, require JWT
    try:
        verify_jwt_in_request()
    except exceptions.NoAuthorizationError:
        return jsonify({"msg": "Missing Authorization Header"}), 401
    except exceptions.InvalidHeaderError:
        return jsonify({"msg": "Invalid Authorization Header"}), 401
    except Exception as e:
        return jsonify({"msg": "Token validation error", "error": str(e)}), 401

# Endpoints to update keys in config.json
@app.route('/update_openai_key', methods=['POST'])
@jwt_required()
def update_openai_key():
    new_key = request.json.get("openai_api_key")
    if not new_key:
        return jsonify({"msg": "New OpenAI key is required"}), 400
    config["openai_api_key"] = new_key
    save_config(config)
    global aiclient
    aiclient = OpenAI(api_key=new_key)  # Update the client with the new key
    return jsonify({"msg": "OpenAI key updated successfully"}), 200

@app.route('/update_app_api_key', methods=['POST'])
@jwt_required()
def update_app_api_key():
    new_key = request.json.get("app_api_key")
    if not new_key:
        return jsonify({"msg": "New Application API key is required"}), 400
    config["app_api_key"] = new_key
    save_config(config)
    app.config["API_KEY"] = new_key  # Update Flask config
    return jsonify({"msg": "Application API key updated successfully"}), 200

@app.route('/update_password', methods=['PUT'])
@jwt_required()  # Protecting this route with JWT
def update_password():
    username = request.json.get('username')
    new_password = request.json.get('new_password')

    if not username or not new_password:
        return jsonify({"msg": "Username and new password are required"}), 400

    # Retrieve the user from the database
    user = users_collection.find_one({"username": username})
    if not user:
        return jsonify({"msg": "User not found"}), 404

    # Hash the new password before updating
    hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())

    # Update the password in MongoDB
    users_collection.update_one(
        {"username": username},
        {"$set": {"password": hashed_password}}
    )

    return jsonify({"msg": "Password updated successfully"}), 200

    
def update_expired_assessments():
    # Get the current date
    current_date = datetime.now()

    # Calculate the date two days ago
    expiry_threshold = current_date - timedelta(days=2)
    assessments_collection = mongo_assessments.db['assessment']
    # Query assessments where the createdDate is older than two days and status is not 'expired'
    assessments_to_update = assessments_collection.find({
        "createdDate": {"$lt": expiry_threshold},
        "status": {"$ne": "expired"}
    })

    # Iterate through the assessments and update their status to 'expired'
    for assessment in assessments_to_update:
        assessments_collection.update_one(
            {"_id": assessment["_id"]},
            {"$set": {"status": "expired"}}
        )
        print(f"Updated assessment with ID {assessment['_id']} to status 'expired'")

# Scheduler configuration
scheduler = BackgroundScheduler()

# Add a daily job to check for expired assessments
scheduler.add_job(func=update_expired_assessments, trigger="interval", minutes=180, id='update_assessments_job')

# Start the scheduler
scheduler.start()

