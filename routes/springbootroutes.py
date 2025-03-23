from flask import Flask, request, jsonify
import os
import shutil
import zipfile
import time
from subprocess import Popen, PIPE
import requests
import threading
from utils import  replace_java_folder,build_project,terminate_application,run_application,run_employee_tests,run_product_tests,run__itenerary_tests
from config import app
UPLOAD_FOLDER = "/home/azureuser/spring-code-uploads"
MAX_FILE_SIZE = 50 * 1024  # 50KB
LOCK = threading.Lock()  # Global lock for synchronization

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Validate file size
def validate_file_size(file):
    file.seek(0, os.SEEK_END)
    file_size = file.tell()
    file.seek(0)  # Reset the pointer to the beginning of the file
    if file_size > MAX_FILE_SIZE:
        return False
    return True


@app.route('/spring-assessments/spring-upload', methods=['POST'])
def upload_and_process():
    # Clear the contents of /home/azureuser/h2db folder
    h2db_folder = "/home/azureuser/h2db"
    for filename in os.listdir(h2db_folder):
        file_path = os.path.join(h2db_folder, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            return jsonify({"error": f"Failed to delete {file_path}. Reason: {str(e)}"}), 500
    name = request.form.get('name')
    phone = request.form.get('phone')
    #assessment = request.form.get('assessmentcode')
    questionname = request.form.get('questionname')

    if not name:
        return jsonify({"error": "Property name is required"}), 400
    file = request.files.get('file')
    if not file:
        return jsonify({"error": "No file uploaded"}), 400

    if not validate_file_size(file):
        return jsonify({"error": "File size exceeds 50KB"}), 400

    # Save the uploaded file
    current_time = time.strftime("%Y%m%d%H%M%S")
    zip_folder = os.path.join(UPLOAD_FOLDER, f"{name}_{phone}")
    os.makedirs(zip_folder, exist_ok=True)
    file_path = os.path.join(zip_folder, file.filename)
    file.save(file_path)
    
    # Acquire the global lock to ensure only one request processes at a time
    with LOCK:
        try:
            # Workflow execution
            project_path = "/home/azureuser/demo-1"
            zip_path = UPLOAD_FOLDER
            replace_java_folder(file_path, zip_path, project_path)
            build_project(project_path)
            app_process = run_application(project_path)
            if questionname == 'EmployeeAPI':
                test_results = run_employee_tests()
            elif questionname == 'ProductAPI':
                test_results = run_product_tests()
            elif questionname == 'IteneraryAPI':
                test_results = run__itenerary_tests()
            else:
                return jsonify({"error": "Invalid question name"}), 400
           
            terminate_application(app_process)
        # Filter test results to keep only specific properties
            filtered_results = []
            for result in test_results:
                filtered_result = {
                "testCase": result.get("testCase"),
                "endpoint": result.get("endpoint"),
                "status": result.get("status")
                 }
                filtered_results.append(filtered_result)
            test_results = filtered_results
            # Return test results as JSON
            return jsonify({"status": "success", "results": test_results})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)}), 500

