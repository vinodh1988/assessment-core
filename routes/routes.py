import os
from flask import Flask, request, render_template, redirect, flash,jsonify
from config import app
from utils import read_docx_in_parts,codegenerator,csv_to_json
import json
import re
from werkzeug.utils import secure_filename
from docx import Document
import fitz
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the upload folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def read_docx(filepath):
    """
    Read the entire DOCX file content in one go.
    """
    doc = Document(filepath)
    full_text = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            full_text.append(paragraph.text.strip())
    return "\n".join(full_text)



def csv_to_json(filepath, max_rows=None):
    """
    Mockup function to convert CSV to JSON.
    """
    return [{"name": "Sample", "value": 123}]

def read_pdf_page_wise(file_path):
    # Open the PDF file
    pdf_document = fitz.open(file_path)
    total_pages = pdf_document.page_count

    # Initialize a list to hold the text of each page
    pages_content = []

    # Iterate through each page
    for page_number in range(total_pages):
        page = pdf_document.load_page(page_number)
        text = page.get_text("text")  # Extract text from the page
        pages_content.append(text.strip())  # Append the page text to the list

    pdf_document.close()
    return pages_content

@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file is submitted
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']

    # If no file is selected
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    # Check if the file is allowed
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        if filename.endswith('.pdf'):
            # Read the entire DOCX content in one go
            full_text = read_pdf_page_wise(filepath)
            questions=[]
            for x in full_text:
                result = codegenerator(x)
                print(result)
                result = re.sub(r'```JSON', '', result, flags=re.IGNORECASE)
                result = re.sub(r'```', '', result, flags=re.IGNORECASE)
                result = json.loads(result)
                questions.extend(result["questionset"])

            # Add question numbers sequentially
            for idx, question in enumerate(questions, start=1):
                question['questionno'] = idx
                
            return jsonify(questions)

        # Process CSV file
        elif filename.endswith('.csv'):
            json_output = csv_to_json(filepath, None)  # Modify csv_to_json to return the JSON directly
            return jsonify(json_output)
    else:
        return ('Only .docx and .csv files are allowed')



"""
@app.route('/upload', methods=['POST'])
def upload_file():
    # Check if a file is submitted
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']

    # If no file is selected
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    # Check if the file is allowed
    if file and allowed_file(file.filename):
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        if filename.endswith('.docx'):
            parts = read_docx_in_parts(filepath, max_words_per_chunk=200)
            extratext = ""
            questions = []
            for x in parts:
                result = codegenerator(extratext + x)
                result = re.sub(r'```JSON', '', result, flags=re.IGNORECASE)
                result = re.sub(r'```', '', result, flags=re.IGNORECASE)
                result = json.loads(result)
                extratext = result["extratext"]
                questions.extend(result["questionset"])
            final=[]
            q=1
            for x in questions:
                x['questionno']=q
                q=q+1
                final.append(x)
                
            return jsonify(final)

        # Process csv file
        elif filename.endswith('.csv'):
            json_output = csv_to_json(filepath, None)  # Modify csv_to_json to return the JSON directly
            return jsonify(json_output)
    else:
        return ('Only .docx and .csv files are allowed')
    """
    
