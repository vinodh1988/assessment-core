from flask import Flask, request, jsonify,send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
import json
from config import app,mongo,mongo_assessments
from base import basedir
import uuid
import random
import pandas as pd
import io
import pdfkit
import os
import hashlib
import datetime

from static import staticfilepath  # Importing the base path of the static resources
import requests

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
        # For each collection, filter out those that contain the word "derived" in their name
        for collection_name in collections:
            if "derived" not in collection_name:  # Exclude collections with "derived" in their name
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
        created_date = datetime.datetime.now().strftime('%Y-%m-%d')
        data['assessmentcode'] = assessment_code
        data['createdDate']=created_date
        data['status']='active'
        # Insert the data into the 'assessment' collection
        collection = mongo_assessments.db.assessment
        result = collection.insert_one(data)

        return jsonify({
            "message": "Assessment successfully added",
            "assessmentcode": assessment_code,
            "createdDate":created_date
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

        # Check if 'originalTotal' and 'requiredQuestion' exist
        original_total = assessment.get('originalTotal')
        required_question = assessment.get('requiredQuestion')

        if original_total and required_question:
            # Handle logic with originalTotal and requiredQuestion
            selected_questions = []
            start_index = 0

            # Loop through the originalTotal and requiredQuestion arrays
            for i, total_questions in enumerate(original_total):
                bank_name = assessment['questionbankname']  # Assuming the same bank contains all the questions
                required = required_question[i]
                question_collection = mongo.db[bank_name]

                # Fetch questions in the range for the current bank
                questions_in_range = list(question_collection.find().skip(start_index).limit(total_questions))
                
                # Randomly select the required number of questions from this range
                if len(questions_in_range) < required:
                    return jsonify({"error": f"Not enough questions in the range for bank {bank_name}"}), 400

                selected_questions.extend(random.sample(questions_in_range, required))
                
                # Update the start_index to skip past the current range for the next iteration
                start_index += total_questions

            # Return selected questions, excluding the 'answer' field

            random.shuffle(selected_questions)
            for question in selected_questions:
                question.pop('answer', None)
                question.pop('_id', None)
            print("##### inside jikki")
            print(selected_questions)
            return jsonify(selected_questions), 200

        # If originalTotal and requiredQuestion do not exist, use the original logic
        else:
            # Get the number of questions from the assessment
            num_questions = assessment.get('numberOfQuestions', 0)
            questionbank_name = assessment.get('questionbankname')

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

@app.route('/questionslist', methods=['GET'])
def get_questions_list():
    try:
        # Retrieve the 'questionBankName' from the query parameters
        question_bank_name = request.args.get('questionBankName')

        if not question_bank_name:
            return jsonify({"error": "Missing 'questionBankName' parameter"}), 400

        # Access the question bank collection based on the questionBankName
        question_collection = mongo.db[question_bank_name]
        
        # Retrieve all the questions from the question bank
        questions = list(question_collection.find({}, {"_id": 0}))  # Exclude the '_id' field

        if not questions:
            return jsonify({"message": "No questions found for the given questionBankName"}), 404

        return jsonify(questions), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/question', methods=['PUT'])
def update_or_add_question():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        if not data or 'questionBankName' not in data or 'question' not in data:
            return jsonify({"error": "Missing 'questionBankName' or 'question' in the request body"}), 400

        question_bank_name = data['questionBankName']
        question_data = data['question']

        if 'questionno' not in question_data:
            return jsonify({"error": "Each question must have a 'questionno'"}), 400

        questionno = question_data['questionno']

        # Access the question bank collection based on the questionBankName
        question_collection = mongo.db[question_bank_name]

        # Check if the question with the given questionno exists
        existing_question = question_collection.find_one({"questionno": questionno})

        if existing_question:
            # If the question exists, update it
            question_collection.update_one(
                {"questionno": questionno},
                {"$set": question_data}
            )
            return jsonify({"message": "Question updated successfully"}), 200
        else:
            # If the question does not exist, insert it
            question_collection.insert_one(question_data)
            return jsonify({"message": "Question added successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/questions', methods=['POST'])
def get_answers_by_question_numbers():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        if not data or 'questionBankName' not in data or 'questionnos' not in data:
            return jsonify({"error": "Missing 'questionBankName' or 'questionnos' in the request body"}), 400

        question_bank_name = data['questionBankName']
        questionnos = data['questionnos']

        # Ensure questionnos are integers (since MongoDB has questionno as integers)
        try:
            questionnos = [int(qno) for qno in questionnos]
        except ValueError:
            return jsonify({"error": "'questionnos' must be an array of integers"}), 400

        # Access the question bank collection based on the questionBankName
        question_collection = mongo.db[question_bank_name]

        # Fetch all questions that match the provided question numbers
        questions = list(question_collection.find({"questionno": {"$in": questionnos}}, {"_id": 0, "questionno": 1, "answer": 1}))

        if not questions:
            return jsonify({"message": "No questions found for the provided questionnos"}), 404

        # Debugging output to check what was fetched
        print(f"Fetched questions: {questions}")

        # Create a map from questionno to answer, but only if the question contains the 'questionno' field
        question_map = {question['questionno']: question['answer'] for question in questions if 'questionno' in question}

        # Ensure the answers are ordered based on the input array order
        ordered_answers = [question_map.get(qno, None) for qno in questionnos]

        return jsonify(ordered_answers), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/generate-pdf', methods=['POST'])
def generate_pdf():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        if not data or 'html' not in data:
            return jsonify({"error": "Missing 'html' in the request body"}), 400

        html_content = data['html']

        # Construct the full path to the CSS file
        css_file_path = os.path.join(staticfilepath, 'answerstyle.css')

        # Check if the CSS file exists
        if not os.path.exists(css_file_path):
            return jsonify({"error": "CSS file not found"}), 500

        # Generate PDF, always apply the CSS from static resources
        pdf = pdfkit.from_string(html_content, False, css=css_file_path)

        # Create an in-memory file stream
        pdf_file = io.BytesIO(pdf)
        pdf_file.seek(0)

        # Return the PDF as a downloadable file
        return send_file(pdf_file, as_attachment=True, download_name="generated.pdf", mimetype="application/pdf")

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
@app.route('/generate-batch-pdf', methods=['POST'])
def generate_batch_pdf():
    try:
        # Extract JSON data from the request
        data = request.get_json()

        if not data or 'html' not in data:
            return jsonify({"error": "Missing 'html' in the request body"}), 400

        html_content = data['html']

        # Construct the full path to the CSS file
        css_file_path = os.path.join(staticfilepath, 'batchstyle.css')

        # Check if the CSS file exists
        if not os.path.exists(css_file_path):
            return jsonify({"error": "CSS file not found"}), 500

        # Generate PDF, always apply the CSS from static resources
        pdf = pdfkit.from_string(html_content, False, css=css_file_path)

        # Create an in-memory file stream
        pdf_file = io.BytesIO(pdf)
        pdf_file.seek(0)

        # Return the PDF as a downloadable file
        return send_file(pdf_file, as_attachment=True, download_name="generated.pdf", mimetype="application/pdf")

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500
 
@app.route('/create-assessment-single-bank', methods=['POST'])
def create_assessment():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract required fields from input data
        assessment_name = data['assessmentName']
        duration = data['duration']
        original_questionbankname = data['questionbankname']
        number_of_questions = data['numberOfQuestions']

        # Fetch total number of questions from the original question bank
        original_collection = mongo.db[original_questionbankname]
        total_questions = original_collection.count_documents({})

        
        if total_questions < number_of_questions:
            return jsonify({"error": f"Not enough questions in {original_questionbankname}."}), 400

        # Case 1: If the requested number of questions is equal to total, use the original question bank
        if total_questions == number_of_questions:
            new_questionbankname = original_questionbankname
            random_questions = list(original_collection.find({}))  # Fetch all questions

        # Case 2: Otherwise, select random questions and create a new question bank
        else:
            random_questions = list(original_collection.aggregate([{"$sample": {"size": number_of_questions}}]))

            # Generate a new question bank name using the original name and current date
            #current_date = datetime.datetime.now().strftime('%Y_%m_%d')
            hash_value = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
            new_questionbankname = f"{original_questionbankname}_derived_{hash_value}"

            # Create a new collection for the selected questions and reset the questionno field
            new_collection = mongo.db[new_questionbankname]
            for idx, question in enumerate(random_questions, start=1):
                # Reset the questionno field to start from 1 and increment
                question['questionno'] = idx
                # Insert the updated question into the new collection
                new_collection.insert_one(question)

        # Generate a unique assessment code
        assessment_code = str(uuid.uuid4())

        # Get the current date for createdDate
        created_date = datetime.datetime.now().strftime('%Y-%m-%d')

        # Create the new assessment
        new_assessment = {
            "assessmentName": assessment_name,
            "duration": duration,
            "questionbankname": new_questionbankname,  # Use the original or new question bank name
            "numberOfQuestions": number_of_questions,
            "assessmentcode": assessment_code,
            "status":"active",
            "createdDate": created_date
        }

        # Insert the new assessment into the 'assessment' collection
        collection = mongo_assessments.db.assessment
        result = collection.insert_one(new_assessment)

        return jsonify({
            "message": "Assessment successfully created",
            "assessmentcode": assessment_code,
            "questionbankname": new_questionbankname,
            "createdDate": created_date
        }), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/create-assessment-multi-bank', methods=['POST'])
def create_combined_assessment():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract required fields from input data
        assessment_name = data['assessmentName']
        duration = data['duration']
        questionbanknames = data['questionbanknames']  # List of question bank names
        number_of_questions = data['numberOfQuestions']  # List of questions to pull from each bank

        # Validate that both lists have the same length
        if len(questionbanknames) != len(number_of_questions):
            return jsonify({"error": "Mismatch between question banks and number of questions."}), 400

        combined_questions = []

        # Combine names of the original banks for naming the new bank
        combined_bank_name_part = "_".join(questionbanknames)

        # Iterate through each question bank and fetch the requested number of questions
        for i, bank_name in enumerate(questionbanknames):
            num_questions = number_of_questions[i]
            original_collection = mongo.db[bank_name]

            # Check if the question bank has enough questions
            total_questions = original_collection.count_documents({})
            if total_questions < num_questions:
                print(total_questions,num_questions)
                return jsonify({"error": f"Not enough questions in {bank_name}."}), 400

            # Fetch the random questions from the original bank
            random_questions = list(original_collection.aggregate([{"$sample": {"size": num_questions}}]))
            combined_questions.extend(random_questions)

        # Generate a new question bank name using combined bank names, "derived", and a hash
        hash_value = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
        new_questionbankname = f"{combined_bank_name_part}_derived_{hash_value}"

        # Create a new collection for the combined questions and reset the questionno field
        new_collection = mongo.db[new_questionbankname]
        for idx, question in enumerate(combined_questions, start=1):
            # Reset the questionno field to start from 1 and increment
            question['questionno'] = idx
            # Insert the updated question into the new collection
            new_collection.insert_one(question)

        # Generate a unique assessment code
        assessment_code = str(uuid.uuid4())

        # Get the current date for createdDate
        created_date = datetime.datetime.now().strftime('%Y-%m-%d')

        # Create the new assessment
        new_assessment = {
            "assessmentName": assessment_name,
            "duration": duration,
            "questionbankname": new_questionbankname,  # Use the new combined question bank name
            "numberOfQuestions": sum(number_of_questions),  # Total number of questions
            "assessmentcode": assessment_code,
            "status":"active",
            "createdDate": created_date
        }

        # Insert the new assessment into the 'assessment' collection
        collection = mongo_assessments.db.assessment
        result = collection.insert_one(new_assessment)

        return jsonify({
            "message": "Assessment successfully created",
            "assessmentcode": assessment_code,
            "questionbankname": new_questionbankname,
            "createdDate": created_date
        }), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/create-full-combined-assessment', methods=['POST'])
def create_full_combined_assessment():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Extract required fields from input data
        assessment_name = data['assessmentName']
        duration = data['duration']
        questionbanknames = data['questionbanknames']  # List of question bank names
        number_of_questions = data['numberOfQuestions']  # List of questions to pull from each bank

        # Validate that both lists have the same length
        if len(questionbanknames) != len(number_of_questions):
            return jsonify({"error": "Mismatch between question banks and number of questions."}), 400

        combined_questions = []
        original_total = []

        # Combine names of the original banks for naming the new bank
        combined_bank_name_part = "_".join(questionbanknames)

        # Iterate through each question bank and fetch all questions
        for i, bank_name in enumerate(questionbanknames):
            original_collection = mongo.db[bank_name]

            # Fetch all questions from the original bank
            all_questions = list(original_collection.find({}))
            original_total.append(len(all_questions))  # Store total number of questions in each original bank

            # Add all questions to the combined questions list
            combined_questions.extend(all_questions)

        # Generate a new question bank name using combined bank names, "derived", and a hash
        hash_value = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:6]
        new_questionbankname = f"{combined_bank_name_part}_derived_{hash_value}"

        # Create a new collection for the combined questions and reset the questionno field
        new_collection = mongo.db[new_questionbankname]
        for idx, question in enumerate(combined_questions, start=1):
            # Reset the questionno field to start from 1 and increment
            question['questionno'] = idx
            # Insert the updated question into the new collection
            new_collection.insert_one(question)

        # Generate a unique assessment code
        assessment_code = str(uuid.uuid4())

        # Get the current date for createdDate
        created_date = datetime.datetime.now().strftime('%Y-%m-%d')

        # Create the new assessment with extra properties originalTotal and requiredQuestion
        new_assessment = {
            "assessmentName": assessment_name,
            "duration": duration,
            "questionbankname": new_questionbankname,  # Use the new combined question bank name
            "numberOfQuestions": sum(number_of_questions),  # Total number of questions for assessment
            "assessmentcode": assessment_code,
            "createdDate": created_date,
            "status":"active",
            "banktype": "derived",
            "originalTotal": original_total,  # Array of the total number of questions in each original collection
            "requiredQuestion": number_of_questions  # Same as the input numberOfQuestions array
        }

        # Insert the new assessment into the 'assessment' collection
        collection = mongo_assessments.db.assessment
        result = collection.insert_one(new_assessment)

        return jsonify({
            "message": "Assessment successfully created",
            "assessmentcode": assessment_code,
            "questionbankname": new_questionbankname,
            "createdDate": created_date
        }), 201

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route('/create-subject-matter', methods=['POST'])
def create_subject_matter():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Access the subjects collection
        subjects_collection = mongo_assessments.db.subjects

        # Insert the data into the subjects collection
        result = subjects_collection.insert_one(data)

        return jsonify({
            "message": "Subject matter successfully created",
            "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
        }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/subjects', methods=['GET'])
def get_subjects():
    try:
        # Access the subjects collection
        subjects_collection = mongo_assessments.db.subjects
            
         # Retrieve all documents from the subjects collection, excluding the '_id' field
        subjects = list(subjects_collection.find({}, {"_id": 0}))

        if not subjects:
            return jsonify({"message": "No subjects found"}), 404

        return jsonify(subjects), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/codequestions', methods=['POST'])
def create_code_question():
        try:
            # Get JSON data from request
            data = request.get_json()

            # Validate required fields
            required_fields = ['subject', 'topic', 'description', 'technology', 'outline', 'question', 'testcases']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            # Access the codequestions collection
            codequestions_collection = mongo_assessments.db.codequestions

            # Insert the data into the codequestions collection
            result = codequestions_collection.insert_one(data)

            return jsonify({
            "message": "Code question successfully created",
             "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
            }), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500
@app.route('/batchcategories', methods=['POST'])
def create_batch_category():
        try:
            # Get JSON data from request
            data = request.get_json()

            if not data or 'batchcategory' not in data:
                return jsonify({"error": "Missing 'batchcategory' in the request body"}), 400

            # Access the batchcategories collection
            batchcategories_collection = mongo_assessments.db.batchcategories

                    # Insert the data into the batchcategories collection
            result = batchcategories_collection.insert_one(data)

            return jsonify({
                        "message": "Batch category successfully created",
                        "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
                    }), 201

        except Exception as e:
                return jsonify({"error": str(e)}), 500


@app.route('/batchcategories', methods=['GET'])
def get_batch_categories():
    try:
        # Access the batchcategories collection
        batchcategories_collection = mongo_assessments.db.batchcategories
                        
        # Retrieve all documents from the batchcategories collection
        categories = list(batchcategories_collection.find({}, {"_id": 0, "batchcategory": 1}))

        # Extract the batchcategory field from each document
        batch_categories = [category['batchcategory'] for category in categories]

        if not batch_categories:
            return jsonify({"message": "No batch categories found"}), 404

        return jsonify(batch_categories), 200

    except Exception as e:
            return jsonify({"error": str(e)}), 500
    

@app.route('/batches', methods=['POST'])
def create_batch():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

            # Access the batches collection
        batches_collection = mongo_assessments.db.batches

            # Insert the data into the batches collection
        result = batches_collection.insert_one(data)

        return jsonify({
                "message": "Batch successfully created",
                "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
            }), 201

    except Exception as e:
            return jsonify({"error": str(e)}), 500

@app.route('/batches', methods=['GET'])
def get_batches():
                try:
                    # Access the batches collection
                    batches_collection = mongo_assessments.db.batches

                    # Retrieve all documents from the batches collection, excluding the '_id' field
                    batches = list(batches_collection.find({}, {"_id": 0}))

                    if not batches:
                        return jsonify({"message": "No batches found"}), 404

                    return jsonify(batches), 200

                except Exception as e:
                    return jsonify({"error": str(e)}), 500
                
@app.route('/codequestions/subjects-topics', methods=['GET'])
def get_codequestions_subjects_topics():
    try:
        # Access the codequestions collection
        codequestions_collection = mongo_assessments.db.codequestions

        # Retrieve only the 'subject' and 'topic' fields from the collection
        subjects_topics = list(codequestions_collection.find({}, {"_id": 0, "subject": 1, "topic": 1}))

        if not subjects_topics:
            return jsonify([]), 200

        return jsonify(subjects_topics), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/codequestions', methods=['GET'])
def get_code_questions_by_subject_and_topic():
        try:
            # Retrieve the 'subject' and 'topic' from the query parameters
            subject = request.args.get('subject')
            topic = request.args.get('topic')

            if not subject or not topic:
                return jsonify({"error": "Missing 'subject' or 'topic' parameter"}), 400

                # Access the codequestions collection
            codequestions_collection = mongo_assessments.db.codequestions

                # Query the collection for documents matching the subject and topic
            questions = list(codequestions_collection.find({"subject": subject, "topic": topic}, {"_id": 0}))

            if not questions:
                return jsonify({"message": "No code questions found for the given subject and topic"}), 404

            return jsonify(questions), 200

        except Exception as e:
                return jsonify({"error": str(e)}), 500
        
@app.route('/code-assessments', methods=['POST'])
def create_code_assessment():
        try:
            # Get JSON data from request
            data = request.get_json()

            if not data:
                return jsonify({"error": "No data provided"}), 400

                # Generate a unique assessment code
            assessment_code = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

                # Add the assessment code to the data
            data['assessmentcode'] = assessment_code

                # Access the code_assessments collection
            code_assessments_collection = mongo_assessments.db.code_assessments

                # Insert the data into the code_assessments collection
            result = code_assessments_collection.insert_one(data)

            return jsonify({
                    "message": "Code assessment successfully created",
                    "assessmentcode": assessment_code,
                    "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
                }), 201

        except Exception as e:
                return jsonify({"error": str(e)}), 500
        
@app.route('/code-assessments', methods=['GET'])
def get_all_code_assessments():
    try:
        # Access the code_assessments collection
        code_assessments_collection = mongo_assessments.db.code_assessments
        # Retrieve all documents from the code_assessments collection, excluding the '_id' field
        code_assessments = list(code_assessments_collection.find({}, {"_id": 0}))

        if not code_assessments:
            return jsonify({"message": "No code assessments found"}), 404

        return jsonify(code_assessments), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
        
@app.route('/code-assessments/<assessmentcode>', methods=['GET'])
def get_code_assessment(assessmentcode):
            try:
                # Access the code_assessments collection
                code_assessments_collection = mongo_assessments.db.code_assessments

                # Retrieve the code assessment based on the assessmentcode
                code_assessment = code_assessments_collection.find_one({"assessmentcode": assessmentcode}, {"_id": 0, "testcases": 0})

                if not code_assessment:
                    return jsonify({"error": "Code assessment not found"}), 404

                return jsonify(code_assessment), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500
@app.route('/code-assessments/check', methods=['POST'])
def check_code_assessment():
        try:
            # Get JSON data from request
            data = request.get_json()

            if not data or 'personName' not in data or 'code' not in data or 'assessmentcode' not in data:
                return jsonify({"error": "Missing 'personName', 'code', or 'assessmentcode' in the request body"}), 400

            person_name = data['personName']
            code = data['code']
            assessment_code = data['assessmentcode']

            # Access the code_assessments collection
            code_assessments_collection = mongo_assessments.db.code_assessments

            # Retrieve the code assessment based on the assessmentcode
            code_assessment = code_assessments_collection.find_one({"assessmentcode": assessment_code}, {"_id": 0, "testcases": 1})

            if not code_assessment:
                return jsonify({"error": "Code assessment not found"}), 404

            # Concatenate code and testcases separated by newline
            testcases = code_assessment.get('testcases', [])
            concatenated_code = code + '\n' + testcases
            print(concatenated_code)
            # Prepare the payload for the external API
            payload = {
                            "personName": person_name,
                            "code": concatenated_code
                        }

                        # Send the payload to the external API
            response = requests.post("http://localhost:8080/api/code", json=payload)
            result = response.json()

                        # Print the result
            print(result)

            return jsonify(result), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        

@app.route('/code-assessments/status', methods=['GET'])
def get_code_assessment_status():
            try:
                # Retrieve the 'assessmentcode' and 'email' from the query parameters
                assessmentcode = request.args.get('assessmentcode')
                email = request.args.get('email')

                if not assessmentcode or not email:
                    return jsonify({"error": "Missing 'assessmentcode' or 'email' parameter"}), 400

                # Access the code_assessments_status collection
                code_assessments_status_collection = mongo_assessments.db.code_assessments_status

                # Retrieve the assessment status based on the assessmentcode and email
                assessment_status = code_assessments_status_collection.find_one(
                    {"assessmentcode": assessmentcode, "email": email}, {"_id": 0}
                )

                if not assessment_status:
                    return jsonify({"error": "Assessment status not found"}), 404

                return jsonify(assessment_status), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500
@app.route('/code-assessments/status', methods=['POST'])
def update_or_create_code_assessment_status():
        try:
            # Get JSON data from request
            data = request.get_json()

            if not data:
                return jsonify({"error": "No data provided"}), 400

            # Validate required fields
            required_fields = ['email', 'assessmentcode', 'candidateName', 'phoneNumber', 'status', 'duration', 'result', 'code']
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            email = data['email']
            assessmentcode = data['assessmentcode']
            candidate_name = data['candidateName']
            phone_number = data['phoneNumber']
            status = data['status']
            duration = data['duration']
            result = data['result']
            code = data['code']

            # Access the code_assessments_status collection
            code_assessments_status_collection = mongo_assessments.db.code_assessments_status

            # Check if a record with the same email and assessmentcode exists
            existing_record = code_assessments_status_collection.find_one({"email": email, "assessmentcode": assessmentcode})

            if existing_record:
                # Update the existing record
                code_assessments_status_collection.update_one(
                    {"_id": existing_record['_id']},
                    {"$set": {
                        "candidateName": candidate_name,
                        "phoneNumber": phone_number,
                        "status": status,
                        "duration": duration,
                        "result": result,
                        "code": code
                    }}
                )
                return jsonify({"message": "Record updated successfully"}), 200
            else:
                # Create a new record
                new_record = {
                    "email": email,
                    "assessmentcode": assessmentcode,
                    "candidateName": candidate_name,
                    "phoneNumber": phone_number,
                    "status": status,
                    "duration": duration,
                    "result": result,
                    "code": code
                }
                result = code_assessments_status_collection.insert_one(new_record)
                return jsonify({
                    "message": "Record created successfully",
                    "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
                }), 201

        except Exception as e:
            return jsonify({"error": str(e)}), 500
        
@app.route('/completed-assessments', methods=['GET'])
def get_completed_assessments():
            try:
                # Retrieve the 'assessmentcode' from the query parameters
                assessmentcode = request.args.get('assessmentcode')

                if not assessmentcode:
                    return jsonify({"error": "Missing 'assessmentcode' parameter"}), 400

                # Access the code_assessments_status collection
                code_assessments_status_collection = mongo_assessments.db.code_assessments_status

                # Query documents with the given assessmentcode and status 'completed'
                completed_assessments = list(code_assessments_status_collection.find(
                    {"assessmentcode": assessmentcode, "status": "completed"},
                    {"_id": 0}
                ))

                if not completed_assessments:
                    return jsonify({"message": "No completed assessments found for the given assessmentcode"}), 404

                return jsonify(completed_assessments), 200

            except Exception as e:
                return jsonify({"error": str(e)}), 500
            

@app.route('/spring-boot-code-questions', methods=['POST'])
def upload_spring_boot_code_question():
        try:
            # Check if the request contains the 'name' and 'file' fields
            if 'name' not in request.form or 'file' not in request.files:
                return jsonify({"error": "Missing 'name' or 'file' in the request"}), 400

            name = request.form['name']
            file = request.files['file']

                    # Check if the file is a PDF
            if not file.filename.lower().endswith('.pdf'):
                return jsonify({"error": "File must have a .pdf extension"}), 400

                    # Check if the file size is less than 15 MB
            if len(file.read()) > 15 * 1024 * 1024:
                return jsonify({"error": "File size must be less than 15 MB"}), 400

                    # Reset the file pointer to the beginning
            file.seek(0)

                    # Create the uploads directory if it doesn't exist
            upload_folder = 'uploads/spring-questions'
            os.makedirs(upload_folder, exist_ok=True)

                    # Save the file to the uploads directory
            filename = file.filename
            file_path = os.path.join(upload_folder, filename)
            file.save(file_path)

                    # Access the spring_boot_questions collection
            spring_boot_questions_collection = mongo_assessments.db.spring_boot_questions

                    # Insert the name and filename into the collection
            result = spring_boot_questions_collection.insert_one({
                        "name": name,
                        "filename": filename
                    })

            return jsonify({
                        "message": "File uploaded and record created successfully",
                        "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
                    }), 201

        except Exception as e:
                    return jsonify({"error": str(e)}), 500
        
@app.route('/spring-assessments', methods=['POST'])
def create_spring_assessment():
            try:
                # Get JSON data from request
                data = request.get_json()

                if not data or 'name' not in data or 'batchname' not in data:
                    return jsonify({"error": "Missing 'name' or 'batchname' in the request body"}), 400

                name = data['name']
                batchname = data['batchname']

                # Generate a unique assessment code
                assessment_code = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

                # Get the current date for assessmentDate
                assessment_date = datetime.datetime.now().strftime('%Y-%m-%d')

                # Create the new assessment
                new_assessment = {
                    "assessmentcode": assessment_code,
                    "name": name,
                    "batchname": batchname,
                    "status": "active",
                    "assessmentdate": assessment_date
                }

                # Access the spring_boot_assessments collection
                spring_assessments_collection = mongo_assessments.db.spring_boot_assessments

                # Insert the new assessment into the collection
                result = spring_assessments_collection.insert_one(new_assessment)

                return jsonify({
                    "message": "Spring Boot assessment successfully created",
                    "assessmentcode": assessment_code,
                    "assessmentdate": assessment_date
                }), 201

            except Exception as e:
                return jsonify({"error": str(e)}), 500

@app.route('/spring-assessments/<assessmentcode>', methods=['GET'])
def get_spring_assessment(assessmentcode):
                try:
                    # Access the spring_boot_assessments collection
                    spring_assessments_collection = mongo_assessments.db.spring_boot_assessments

                    # Retrieve the spring assessment based on the assessmentcode
                    spring_assessment = spring_assessments_collection.find_one({"assessmentcode": assessmentcode}, {"_id": 0})

                    if not spring_assessment:
                        return jsonify({"error": "Spring assessment not found"}), 404

                    return jsonify(spring_assessment), 200

                except Exception as e:
                    return jsonify({"error": str(e)}), 500
                    
@app.route('/spring-assessment-details/<assessmentcode>', methods=['GET'])
def get_spring_assessment_details(assessmentcode):
    try:
        # Retrieve the 'email' from the query parameters
        email = request.args.get('email')

        if not email:
            return jsonify({"error": "Missing 'email' parameter"}), 400
    # Access the spring_boot_assessments collection
        spring_assessments_collection = mongo_assessments.db.spring_boot_assessments

       # Retrieve the spring assessment based on the assessmentcode
        spring_assessment = spring_assessments_collection.find_one({"assessmentcode": assessmentcode}, {"_id": 0})

        if not spring_assessment:
            return jsonify({"error": "Spring assessment not found"}), 404

        # Access the spring_boot_assessment_status collection
        spring_assessment_status_collection = mongo_assessments.db.spring_boot_assessment_status

        # Retrieve the assessment status based on the assessmentcode
        assessment_status = spring_assessment_status_collection.find_one({"assessmentcode": assessmentcode,"email": email}, {"_id": 0})

        print("Log_1",assessment_status)
        app.logger.info("Log_1",assessment_status)

        if assessment_status and 'questionname' in assessment_status:
            question_name = assessment_status['questionname']
            if assessment_status['status'] == 'completed':
                return jsonify({
                    "assessment": spring_assessment,
                    "questionname": "completed"
                }), 200
        else:
                                # Access the spring_boot_questions collection
            spring_questions_collection = mongo_assessments.db.spring_boot_questions

                                # Retrieve all questions
            questions = list(spring_questions_collection.find({}, {"_id": 0, "name": 1}))

            if not questions:
                return jsonify({"error": "No questions found"}), 404

                # Select a random question name
            question_name = random.choice(questions)['name']

            # Add the question name to the spring assessment object
        spring_assessment['questionname'] = question_name

        return jsonify(spring_assessment), 200

    except Exception as e:
            return jsonify({"error": str(e)}), 500
    

@app.route('/spring-boot-files/<fname>', methods=['GET'])
def get_spring_boot_file(fname):
    try:
        if fname == 'instructions':
            filename = 'Project-Instructions.pdf'
            file_path = basedir + '/uploads/spring-questions/' + filename
            if not os.path.exists(file_path):
                return jsonify({"error": "File not found on server"}), 404
            return send_file(file_path, as_attachment=True, download_name=filename, mimetype='application/pdf')
        
        # Access the spring_boot_questions collection
        spring_boot_questions_collection = mongo_assessments.db.spring_boot_questions

        # Find the document with the matching name
        document = spring_boot_questions_collection.find_one({"name": fname})

        if not document:
            return jsonify({"error": "File not found"}), 404

        # Get the filename from the document
        filename = document['filename']

        # Construct the file path
        file_path = basedir + '/uploads/spring-questions/' + filename

        if not os.path.exists(file_path):
            return jsonify({"error": "File not found on server"}), 404

        # Send the file for download
        return send_file(file_path, as_attachment=True, download_name=filename, mimetype='application/pdf')

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/spring-assessments/status', methods=['POST'])
def update_spring_assessment_status():
    try:
        # Get JSON data from request
        data = request.get_json()

        if not data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        required_fields = ['assessmentcode', 'batchname', 'questionname','name', 'email', 'phone', 'status', 'testresults', 'score']
        for field in required_fields:
            if field not in data:
                return jsonify({"error": f"Missing required field: {field}"}), 400

        assessmentcode = data['assessmentcode']
        batchname = data['batchname']
        name = data['name']
        email = data['email']
        phone = data['phone']
        status = data['status']
        testresults = data['testresults']
        score = data['score']
        questionname = data['questionname']

        # Access the spring_boot_assessment_status collection
        status_collection = mongo_assessments.db.spring_boot_assessment_status

        # Check if a record with the same email and assessmentcode exists
        existing_record = status_collection.find_one({"email": email, "assessmentcode": assessmentcode})

        if existing_record:
            # Update the existing record
            status_collection.update_one(
                {"_id": existing_record['_id']},
                {"$set": {
                    "batchname": batchname,
                    "name": name,
                    "phone": phone,
                    "questionname": questionname,
                    "status": status,
                    "testresults": testresults,
                    "score": score
                }}
            )
            return jsonify({"message": "Record updated successfully"}), 200
        else:
            # Create a new record
            new_record = {
                "assessmentcode": assessmentcode,
                "batchname": batchname,
                "name": name,
                "email": email,
                "phone": phone,
                "questionname": questionname,
                "status": status,
                "testresults": testresults,
                "score": score
            }
            result = status_collection.insert_one(new_record)
            return jsonify({
                "message": "Record created successfully",
                "inserted_id": str(result.inserted_id)  # Return the MongoDB ObjectId
            }), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/spring-assessments', methods=['GET'])
def get_all_spring_boot_assessments():
        try:
            # Access the spring_boot_assessments collection
            spring_assessments_collection = mongo_assessments.db.spring_boot_assessments

            # Retrieve all documents from the spring_boot_assessments collection, excluding the '_id' field
            assessments = list(spring_assessments_collection.find({}, {"_id": 0}))

            if not assessments:
                return jsonify({"message": "No spring boot assessments found"}), 404

            return jsonify(assessments), 200

        except Exception as e:
            return jsonify({"error": str(e)}), 500