import csv
import json

def csv_to_json(csv_file_path, json_file_path):
    questions_list = []
    
    # Open the CSV file
    with open(csv_file_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Iterate over each row in the CSV
        for row in reader:
            question = row['question']
            options = [row['option1'], row['option2'], row['option3'], row['option4']]
            
            # Retrieve the letter answer from the CSV directly
            answer_letter = row['answer'].strip().lower()  # Get the letter answer (e.g., 'a')
            
            # Append the question object to the list
            questions_list.append({
                "question": question,
                "options": options,  # Just the raw text options
                "answer": answer_letter,  # The letter answer ('a', 'b', 'c', etc.)
                "type": "single"
            })
    
    # Write the list of questions to a JSON file
   
    return  questions_list


