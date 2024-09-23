from openai import OpenAI
from config import aiclient


def codegenerator(text):
    messages=[]
  
    messages.append({"role":"system",
                     "content":"The user will pass full text from a document which contains few MCQ's with options"})
    
   
    messages.append({
                      "role":"system",
                      "content":"For each question create a json object with  question [value is full question text , only question text no need for questionno], options [Array of answers ,only answers strictly no need for specifying A,B,C or 1,2,3], type (possible values are single or multi  based on if the question has multiple answers) and finally answer which has answer in array, also  must contains only alphabets as answers"
    })

    messages.append(
                      {"role": "system",
                       "content":"finally produce a json object with one property questionset with array of objects of questions as value"}
    )
 
          
    
    messages.append({"role": "user", 
                     "content": text})
    

    chat_response= aiclient.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=messages,
    
    )
    return chat_response.choices[0].message.content

