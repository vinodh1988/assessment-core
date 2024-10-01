from flask import Flask, request, jsonify,send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import json
from config import app,mongo,mongo_assessments
import uuid
import random
import pandas as pd
import io

@app.route('/questionsupload', methods=['POST'])
def question_upload():
    # Get JSON data from request
    data = request.get_json()

    # Extract questionbankname and questions array
    question_bank_name = data.get('questionBankName')
    questions = data.get('questions')

    if not question_bank_name or not questions:
        return jsonify({"error": "Both 'questionbankname' and 'questions' are required"}), 400

    # Insert questions into a new collection based on the questionbankname
    try:
        collection = mongo.db[question_bank_name]
        # Insert all questions into the MongoDB collection
        inserted_ids = collection.insert_many(questions).inserted_ids

        return jsonify({
            "message": f"Questions successfully inserted into {question_bank_name}",
            "inserted_ids": [str(id) for id in inserted_ids]  # Convert ObjectIds to strings
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/questionbanks', methods=['GET'])
def get_questionbanks():
    try:
        # Get a list of all collections (question banks) in the database
        collections = mongo.db.list_collection_names()

        questionbanks_info = []
        # For each collection, get the number of documents
        for collection_name in collections:
            collection = mongo.db[collection_name]
            noq = collection.count_documents({})  # Get the number of documents in the collection
            questionbanks_info.append({
                'questionbankname': collection_name,
                'noq': noq
            })

        return jsonify(questionbanks_info), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/assessments', methods=['POST'])
def add_assessment():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Generate a unique assessment code
        assessment_code = str(uuid.uuid4())

        # Add the assessment code to the data
        data['assessmentcode'] = assessment_code

        # Insert the data into the 'assessment' collection
        collection = mongo_assessments.db.assessment
        result = collection.insert_one(data)

        return jsonify({
            "message": "Assessment successfully added",
            "assessmentcode": assessment_code,
            # Return the MongoDB ObjectId
        }), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/assessments/<code>', methods=['GET'])
def get_assessment_questions(code):
    try:
        # Access the assessment collection
        assessment_collection = mongo_assessments.db.assessment
        
        # Retrieve the assessment details
        assessment = assessment_collection.find_one({"assessmentcode": code})

        if not assessment:
            return jsonify({"error": "Assessment not found"}), 404
        
        # Get the number of questions from the assessment
        num_questions = assessment.get('numberOfQuestions', 0)
        questionbank_name = assessment.get('questionbankname')

        print(num_questions,questionbank_name)

        if not questionbank_name:
            return jsonify({"error": "Question bank name is missing in the assessment"}), 400

        # Access the question bank collection
        question_collection = mongo.db[questionbank_name]
        
        # Fetch all questions from the question bank
        all_questions = list(question_collection.find({}, {"_id": 0, "answer": 0}))  # Exclude the answer field

        if len(all_questions) < num_questions:
            return jsonify({"error": "Not enough questions in the question bank"}), 400
        
        # Randomly select the required number of questions
        selected_questions = random.sample(all_questions, num_questions)
        
        return jsonify(selected_questions), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/testdetails/<assessmentcode>', methods=['GET'])
def get_assessment_details(assessmentcode):
    try:
        # Access the assessment collection
        assessment_collection = mongo_assessments.db.assessment
        
        # Retrieve the assessment details based on the assessmentcode
        assessment = assessment_collection.find_one({"assessmentcode": assessmentcode})

        if not assessment:
            return jsonify({"error": "Assessment not found"}), 404

        # Return the assessment details
        # Exclude the '_id' field from the response
        assessment.pop('_id', None)

        return jsonify(assessment), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/assessments/status', methods=['POST'])
def update_or_create_status():
    try:
        print("running it")
        # Get JSON data from request
        data = request.get_json()
        print(data)

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['name', 'email', 'assessmentcode', 'questionnos', 'answers', 'duration','currentDuration']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Extract fields from data
        name = data['name']
        email = data['email']
        assessmentcode = data['assessmentcode']
        questionnos = data['questionnos']
        answers = data['answers']
        duration = data ['duration']
        currentDuration = data['currentDuration']
        phone=data['phone']
        status = data["testStatus"]

        # Access the assessment_status collection
        status_collection = mongo_assessments.db.assessment_status
        
        # Check if a record with the same email and assessmentcode exists
        existing_record = status_collection.find_one({"email": email, "assessmentcode": assessmentcode})

        if existing_record:
            # Update the existing record
            status_collection.update_one(
                {"_id": existing_record['_id']},
                {
                    "$set": {
                        "name": name,
                        "questionnos": questionnos,
                        "answers": answers,
                        "currentDuration": currentDuration,
                        "duration": duration,
                        "phone":phone,
                        "testStatus": status
                    }
                }
            )
            return jsonify({"message": "Record updated successfully"}), 200
        else:
            # Create a new record
            new_record = {
                "name": name,
                "email": email,
                "assessmentcode": assessmentcode,
                "questionnos": questionnos,
                "answers": answers,
                "duration": duration,
                "currentDuration": currentDuration,
                "phone":phone,
                "testStatus": False
            }
            result = status_collection.insert_one(new_record)
            return jsonify({
                "message": "Record created successfully",
                "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
            }), 201

    except Exception as e:
        print(e)
        print("print")
        return jsonify({"error": str(e)}), 500

@app.route('/assessments/status', methods=['GET'])
def get_assessment_status():
    try:
        # Extract query parameters
        email = request.args.get('email')
        assessmentcode = request.args.get('assessmentcode')

        if not email or not assessmentcode:
            return jsonify({"error": "Missing required query parameters: email and assessmentcode"}), 400

        # Access the assessment_status collection
        status_collection = mongo_assessments.db.assessment_status
        
        # Retrieve the record based on email and assessmentcode
        record = status_collection.find_one({"email": email, "assessmentcode": assessmentcode})

        if not record:
            return jsonify({"error": "Record not found"}), 404

        # Exclude the '_id' field from the response
        record.pop('_id', None)

        return jsonify(record), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/assessments/evaluate', methods=['POST'])
def evaluate_assessment():
    try:
        # Get JSON data from the request
        data = request.get_json()

        if not data or "assessmentcode" not in data or "email" not in data:
            return jsonify({"error": "Missing 'assessmentcode' or 'email'"}), 400

        assessmentcode = data['assessmentcode']
        email = data['email']

        # Fetch the assessment status record using assessmentcode and email
        status_collection = mongo_assessments.db.assessment_status
        status_record = status_collection.find_one({"assessmentcode": assessmentcode, "email": email})

        if not status_record:
            return jsonify({"error": "No matching assessment status record found"}), 404

        # Fetch the assessment details to get the questionbankname
        assessment_collection = mongo_assessments.db.assessment
        assessment_details = assessment_collection.find_one({"assessmentcode": assessmentcode})

        if not assessment_details:
            return jsonify({"error": "No matching assessment details found"}), 404

        questionbankname = assessment_details["questionbankname"]

        # Access the question bank collection
        question_collection = mongo.db[questionbankname]

        # Initialize evaluation metrics
        total_questions = len(status_record["questionnos"])
        answered_correct = 0

        # Evaluate each question
        for idx, user_question in enumerate(status_record["questionnos"]):
            # Fetch the original question using questionno
            original_question = question_collection.find_one({"questionno": user_question["questionno"]})
            if not original_question:
                continue  # Skip if the original question is not found

            # Compare answers
            user_answer = status_record["answers"][idx]
            correct_answer = original_question["answer"]

            if user_question["type"] == "single":
                # Single-type question, check if answers match (case-insensitive)
                if user_answer and correct_answer and user_answer[0].strip().lower() == correct_answer[0].strip().lower():
                    answered_correct += 1

            elif user_question["type"] == "multi":
                # Multi-type question, evaluate based on length and correctness
                correct_answer_set = set([ans.strip().lower() for ans in correct_answer])
                user_answer_set = set([ans.strip().lower() for ans in user_answer])

                if len(user_answer_set) > len(correct_answer_set):
                    continue  # Exceeding answers, no marks awarded
                else:
                    # Calculate correct matches as the intersection of both sets
                    correct_matches = len(user_answer_set.intersection(correct_answer_set))
                    percentage_correct = (correct_matches / len(correct_answer_set)) * 100
                    if percentage_correct == 100:
                        answered_correct += 1

        # Calculate the percentage score
        percentage_score = (answered_correct / total_questions) * 100 if total_questions > 0 else 0

        # Prepare the result record
        result_record = {
            "assessmentcode": assessmentcode,
            "email": status_record["email"],
            "name": status_record["name"],
            "phone": status_record.get("phone", "N/A"),  # Assuming phone might be missing
            "totalquestions": total_questions,
            "answeredCorrect": answered_correct,
            "percentage": round(percentage_score, 2)
        }

        # Insert the result into the result collection
        result_collection = mongo_assessments.db.result
        result_collection.insert_one(result_record)

        return jsonify({
            "message": "Evaluation completed successfully",
        }), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
    
@app.route('/assessments', methods=['GET'])
def get_all_assessments():
    try:
        # Access the assessment collection
        assessment_collection = mongo_assessments.db.assessment
        
        # Retrieve all documents in the collection
        assessments = list(assessment_collection.find({}, {"_id": 0}))  # Exclude the '_id' field

        if not assessments:
            return jsonify({"message": "No assessments found"}), 404

        return jsonify(assessments), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/assessments/evaluate', methods=['GET'])
def get_evaluation_results():
    try:
        # Retrieve the 'assessmentcode' from the query parameters
        assessmentcode = request.args.get('assessmentCode')

        if not assessmentcode:
            return jsonify({"error": "Missing 'assessmentcode' parameter"}), 400

        # Access the result collection
        result_collection = mongo_assessments.db.result
        
        # Fetch all documents with the specified assessmentcode
        results = list(result_collection.find({"assessmentcode": assessmentcode}, {"_id": 0}))  # Exclude the '_id' field

        if not results:
            return jsonify({"message": "No results found for the given assessmentcode"}), 404

        return jsonify(results), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/downloadExcel', methods=['POST'])
def download_excel():
    try:
        # Get JSON data from the request
        data = request.get_json()

        if not data or not isinstance(data, list) or len(data) == 0:
            return jsonify({"error": "Invalid or empty JSON data provided"}), 400

        # Convert the JSON data into a pandas DataFrame
        df = pd.DataFrame(data)

        # Create an in-memory Excel file using BytesIO
        excel_buffer = io.BytesIO()
        df.to_excel(excel_buffer, index=False, engine='openpyxl')
        excel_buffer.seek(0)  # Move the pointer to the beginning of the buffer

        # Send the file as a response for download
        return send_file(
            excel_buffer,
            as_attachment=True,
            download_name="assessment_data.xlsx",  # Use 'attachment_filename' for Flask < 2.0
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/lockedstatus', methods=['GET'])
def get_locked_assessments():
    try:
        # Retrieve the 'assessmentCode' from the query parameters
        assessment_code = request.args.get('assessmentCode')

        if not assessment_code:
            return jsonify({"error": "Missing 'assessmentCode' parameter"}), 400

        # Access the assessment_status collection
        status_collection = mongo_assessments.db.assessment_status
        
        # Query documents with the given assessmentCode and status 'locked'
        results = status_collection.find({"assessmentcode": assessment_code, "testStatus": "locked"},
                                         {"_id": 0, "name": 1, "email": 1, "currentDuration": 1, "assessmentcode":1})

        # Convert the cursor to a list of documents
        result_list = list(results)

        if len(result_list)==0:
            return jsonify([]), 200

        return jsonify(result_list), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/assessment/unlock', methods=['POST'])
def unlock_assessment():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        if not data or 'email' not in data or 'assessmentCode' not in data:
            return jsonify({"error": "Missing 'email' or 'assessmentCode' in the request body"}), 400

        email = data['email']
        assessment_code = data['assessmentCode']

        # Access the assessment_status collection
        status_collection = mongo_assessments.db.assessment_status
        
        # Find the record with matching email and assessmentCode
        result = status_collection.find_one({"email": email, "assessmentcode": assessment_code})

        if not result:
            return jsonify({"error": "No assessment found for the provided email and assessmentCode"}), 404

        # Update the status to 'unlocked'
        status_collection.update_one(
            {"email": email, "assessmentcode": assessment_code},
            {"$set": {"testStatus": False}}
        )

        return jsonify({"message": "Assessment unlocked successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

