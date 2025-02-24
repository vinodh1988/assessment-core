from flask import Flask, request, jsonify,send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import json
from config import app,mongo,mongo_assessments
import uuid
import random
import pandas as pd
import io
import pdfkit
import os
import hashlib
import datetime
from utils import loadcode,generate_topic
@app.route('/codequestion', methods=['POST'])
def question_get():
    data = request.get_json()
    topic = data['topic']
    result = loadcode(topic)
    return jsonify(result)

@app.route('/topics', methods=['POST'])
def get_topics():
    data = request.get_json()
    subject = data['subject']
    result = generate_topic(subject)
    return jsonify(result)
