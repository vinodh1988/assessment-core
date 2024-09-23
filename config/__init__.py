from flask import Flask,send_from_directory
import os
from openai import OpenAI
from flask_cors import CORS
from flask_pymongo import PyMongo
aiclient=OpenAI(api_key="#####")




basedir=os.path.abspath(os.path.dirname(__file__))

app=Flask(__name__)
app.config["MONGO_URI"] = "mongodb://localhost:27017/questionbanks_db"  # Change to your MongoDB URI
mongo = PyMongo(app)

app.config["ASSESSMENTS_MONGO_URI"] = "mongodb://localhost:27017/assessments_db"  # Different database
mongo_assessments = PyMongo(app, uri=app.config["ASSESSMENTS_MONGO_URI"])
CORS(app)