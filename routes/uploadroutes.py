from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import zipfile
import pymongo
from pymongo import MongoClient
from config import app, mongo_assessments

def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions

@app.route('/project-uploads', methods=['POST'])
def project_uploads():
    if 'src' not in request.files or 'presentation' not in request.files or 'screenshots' not in request.files:
        return jsonify({'error': 'Missing file(s)'}), 400

    src = request.files['src']
    presentation = request.files['presentation']
    screenshots = request.files['screenshots']
    name = request.form.get('name')
    email = request.form.get('email')
    assignmentcode = request.form.get('assignmentcode')

    if not name or not email or not assignmentcode:
        return jsonify({'error': 'Missing form data'}), 400

    if not (allowed_file(src.filename, {'zip'}) and allowed_file(presentation.filename, {'pdf'}) and allowed_file(screenshots.filename, {'zip'})):
        return jsonify({'error': 'Invalid file type'}), 400

    if src.mimetype != 'application/zip' or presentation.mimetype != 'application/pdf' or screenshots.mimetype != 'application/zip':
        return jsonify({'error': 'Invalid file type'}), 400

    if len(src.read()) > 100 * 1024:
        return jsonify({'error': 'src file too large'}), 400
    src.seek(0)

    if len(presentation.read()) > 15 * 1024 * 1024:
        return jsonify({'error': 'presentation file too large'}), 400
    presentation.seek(0)

    if len(screenshots.read()) > 30 * 1024 * 1024:
        return jsonify({'error': 'screenshots file too large'}), 400
    screenshots.seek(0)

    assignment_folder_path = os.path.join('uploads', assignmentcode)
    if not os.path.exists(assignment_folder_path):
        return jsonify({'error': 'Assignment folder not found'}), 404

    user_folder_path = os.path.join(assignment_folder_path, name)
    os.makedirs(user_folder_path, exist_ok=True)

    src_filename = secure_filename("src.zip")
    presentation_filename = secure_filename("presentation.pdf")
    screenshots_filename = secure_filename("screenshots.zip")

    src.save(os.path.join(user_folder_path, src_filename))
    presentation.save(os.path.join(user_folder_path, presentation_filename))
    screenshots.save(os.path.join(user_folder_path, screenshots_filename))

    file_details = {
        'name': name,
        'email': email,
        'assignmentcode': assignmentcode,
        'src': src_filename,
        'presentation': presentation_filename,
        'screenshots': screenshots_filename,
        'folder_path': user_folder_path
    }
    collection = mongo_assessments['filedetails']
    collection.insert_one(file_details)

    return jsonify({'message': 'Files uploaded successfully'}), 200