import os
import shutil
import subprocess
import time
import zipfile
import requests
import threading
import requests
import json

# Step 1: Extract the `main/java` folder from the zip file and copy it to the project
def replace_java_folder(zip_file,zip_path, project_path):
    target_java_folder = os.path.join(project_path, "src", "main", "java")
    
    # Remove the existing 'src/main/java' folder if it exists
    if os.path.exists(target_java_folder):
        shutil.rmtree(target_java_folder)
        print(f"Removed existing folder: {target_java_folder}")

    # Extract the zip file
    with zipfile.ZipFile(zip_file, 'r') as zip_ref:
        zip_ref.extractall(zip_path)
        print(f"Extracted {zip_file} to {zip_path}")

    # Locate and copy the `main/java` folder from the extracted directory
    extracted_main_java = os.path.join(zip_path,"src", "main", "java")  # Adjust if structure differs
    shutil.copytree(extracted_main_java, target_java_folder)
    print(f"Copied {extracted_main_java} to {target_java_folder}")

    # Remove the temporary `main` directory after copying
    shutil.rmtree(os.path.join(zip_path, "src"))
    print(f"Cleaned up temporary extracted files.")

# Step 2: Build the Spring Boot project using Maven
def build_project(project_path):
    print("Building the Spring Boot project...")
    maven_executable = "E:\\apache-maven-3.9.9\\bin\\mvn.cmd"
    result = subprocess.run([maven_executable, "clean", "install"], cwd=project_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(result)
    if result.returncode == 0:
        print("Build succeeded!")
    else:
        print(f"Build failed:\n{result.stderr}")
        exit(1)

# Step 3: Run the Spring Boot application
def run_application(project_path):
    print("Running the Spring Boot application...")
    jar_file = os.path.join(project_path, "target", "code-uploaded-1.0.0.jar")  # Replace 'application.jar' with your actual JAR file name
    java_command = ["java", "-jar", jar_file]
     # Function to stream logs
    def stream_logs(process):
        try:
            for line in process.stdout:
                print(line, end="")  # Print logs to console in real-time
        except Exception as e:
            print(f"Error streaming logs: {e}")

    # Run the process
    process = subprocess.Popen(java_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    # Start a thread to stream logs without blocking the script
    log_thread = threading.Thread(target=stream_logs, args=(process,))
    log_thread.daemon = True  # Ensures the thread ends when the main program exits
    log_thread.start()
    time.sleep(10)
    print("Spring Boot application is running.")
    return process


# Base URL for the API


# Function to run all 10 test cases
def run_employee_tests():
    BASE_URL = "http://localhost:7878/api/employees"
    test_results = []

    # Test Case 1: Fetch all employees
    try:
        response = requests.get(BASE_URL)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch all employees",
            "endpoint": f"GET {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch all employees",
            "endpoint": f"GET {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })


    # Test Case 4: Add a new employee
    try:
        new_employee = {
             "id": 1,
            "name": "JOhny Hande",
            "department": "HR",
            "salary": 50000.0,
            "email": "jane.doe@example.com"
        }
        response = requests.post(BASE_URL, json=new_employee)
        status = "PASSED" if response.status_code == 201 else "FAILED"
        test_results.append({
            "testCase": "Add a new employee",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add a new employee",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 2: Fetch employee by ID
    try:
        employee_id = 1  # Replace with a valid ID
        response = requests.get(f"{BASE_URL}/{employee_id}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch employee by ID",
            "endpoint": f"GET {BASE_URL}/{employee_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch employee by ID",
            "endpoint": f"GET {BASE_URL}/{employee_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 3: Fetch non-existent ID
    try:
        non_existent_id = 9999
        response = requests.get(f"{BASE_URL}/{non_existent_id}")
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Fetch non-existent ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch non-existent ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })

   

    # Test Case 5: Add employee with duplicate email
    try:
        duplicate_employee = {
            "name": "John Doe",
            "department": "Engineering",
            "salary": 60000.0,
            "email": "jane.doe@example.com"  # Duplicate email
        }
        response = requests.post(BASE_URL, json=duplicate_employee)
        status = "PASSED" if response.status_code == 400 else "FAILED"
        test_results.append({
            "testCase": "Add employee with duplicate email",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add employee with duplicate email",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 6: Update employee details
    try:
        employee_id = 1  # Replace with a valid ID
        updated_employee = {
            "name": "John Updated",
            "department": "Finance",
            "salary": 70000.0,
            "email": "john.updated@example.com"
        }
        response = requests.put(f"{BASE_URL}/{employee_id}", json=updated_employee)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Update employee details",
            "endpoint": f"PUT {BASE_URL}/{employee_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Update employee details",
            "endpoint": f"PUT {BASE_URL}/{employee_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 7: Update non-existent employee
    try:
        non_existent_id = 9999
        updated_employee = {
            "name": "Ghost Employee",
            "department": "Mystery",
            "salary": 0.0,
            "email": "ghost@example.com"
        }
        response = requests.put(f"{BASE_URL}/{non_existent_id}", json=updated_employee)
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Update non-existent employee",
            "endpoint": f"PUT {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Update non-existent employee",
            "endpoint": f"PUT {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })
     # Test Case 10: Fetch employees by department
    try:
        department = "Finance"
        response = requests.get(f"{BASE_URL}/department/{department}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch employees by department",
            "endpoint": f"GET {BASE_URL}/department/{department}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch employees by department",
            "endpoint": f"GET {BASE_URL}/department/{department}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 8: Delete an employee
    try:
        employee_id = 1  # Replace with a valid ID
        response = requests.delete(f"{BASE_URL}/{employee_id}")
        status = "PASSED" if response.status_code == 204 else "FAILED"
        test_results.append({
            "testCase": "Delete an employee",
            "endpoint": f"DELETE {BASE_URL}/{employee_id}",
            "status": status,
            "response": response.text if status == "FAILED" else "No Content"
        })
    except Exception as e:
        test_results.append({
            "testCase": "Delete an employee",
            "endpoint": f"DELETE {BASE_URL}/{employee_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 9: Delete non-existent employee
    try:
        non_existent_id = 9999
        response = requests.delete(f"{BASE_URL}/{non_existent_id}")
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Delete non-existent employee",
            "endpoint": f"DELETE {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Delete non-existent employee",
            "endpoint": f"DELETE {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })

   
    return test_results


def run_product_tests():
    BASE_URL = "http://localhost:7878/api/products" 
    test_results = []

    # Test Case 1: Fetch all products
    try:
        response = requests.get(BASE_URL)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch all products",
            "endpoint": f"GET {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch all products",
            "endpoint": f"GET {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

      
    try:
        new_product = {
            "id":1,
            "name": "Product A",
            "price": 100.0,
            "category": "Electronics",
            "sku": "SKU001",
            "description": "A test product"
        }
        response = requests.post(BASE_URL, json=new_product)
        status = "PASSED" if response.status_code == 201 else "FAILED"
        test_results.append({
            "testCase": "Add a new product",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add a new product",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })
    # Test Case 2: Fetch product by ID
    try:
        product_id = 1  # Replace with a valid ID
        response = requests.get(f"{BASE_URL}/{product_id}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch product by ID",
            "endpoint": f"GET {BASE_URL}/{product_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch product by ID",
            "endpoint": f"GET {BASE_URL}/{product_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 3: Fetch non-existent product by ID
    try:
        non_existent_id = 9999
        response = requests.get(f"{BASE_URL}/{non_existent_id}")
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Fetch non-existent product by ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch non-existent product by ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 4: Add a new product
   

    # Test Case 5: Add product with invalid price
    try:
        invalid_product = {
            "id":2,
            "name": "Invalid Product",
            "price": -10.0,
            "category": "Electronics",
            "sku": "SKU002",
            "description": "Invalid product with negative price"
        }
        response = requests.post(BASE_URL, json=invalid_product)
        status = "PASSED" if response.status_code == 400 else "FAILED"
        test_results.append({
            "testCase": "Add product with invalid price",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add product with invalid price",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 6: Add product with duplicate SKU
    try:
        duplicate_product = {
            "id":3,
            "name": "Duplicate SKU Product",
            "price": 50.0,
            "category": "Home",
            "sku": "SKU001",  # Duplicate SKU
            "description": "Product with duplicate SKU"
        }
        response = requests.post(BASE_URL, json=duplicate_product)
        status = "PASSED" if response.status_code == 400 else "FAILED"
        test_results.append({
            "testCase": "Add product with duplicate SKU",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add product with duplicate SKU",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 7: Update an existing product
    try:
        product_id = 1  # Replace with a valid ID
        updated_product = {
            "name": "Updated Product A",
            "price": 150.0,
            "category": "Electronics",
            "sku": "SKU001",
            "description": "Updated description"
        }
        response = requests.put(f"{BASE_URL}/{product_id}", json=updated_product)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Update an existing product",
            "endpoint": f"PUT {BASE_URL}/{product_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Update an existing product",
            "endpoint": f"PUT {BASE_URL}/{product_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 8: Update non-existent product
    try:
        non_existent_id = 9999
        updated_product = {
            "name": "Non-existent Product",
            "price": 200.0,
            "category": "Office Supplies",
            "sku": "SKU999",
            "description": "This product does not exist"
        }
        response = requests.put(f"{BASE_URL}/{non_existent_id}", json=updated_product)
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Update non-existent product",
            "endpoint": f"PUT {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Update non-existent product",
            "endpoint": f"PUT {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })

      # Test Case 10: Fetch products by category
    try:
        category = "Electronics"
        response = requests.get(f"{BASE_URL}/category/{category}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch products by category",
            "endpoint": f"GET {BASE_URL}/category/{category}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch products by category",
            "endpoint": f"GET {BASE_URL}/category/{category}",
            "status": "FAILED",
            "error": str(e)
        })


    # Test Case 9: Delete a product
    try:
        product_id = 1  # Replace with a valid ID
        response = requests.delete(f"{BASE_URL}/{product_id}")
        status = "PASSED" if response.status_code == 204 else "FAILED"
        test_results.append({
            "testCase": "Delete a product",
            "endpoint": f"DELETE {BASE_URL}/{product_id}",
            "status": status,
            "response": response.text if status == "FAILED" else "No Content"
        })
    except Exception as e:
        test_results.append({
            "testCase": "Delete a product",
            "endpoint": f"DELETE {BASE_URL}/{product_id}",
            "status": "FAILED",
            "error": str(e)
        })

  
    return test_results



    print("Test cases executed. Results saved to 'test_results.json'.")
# Step 5: Terminate the Spring Boot application
def terminate_application(process):
    print("Terminating the Spring Boot application...")
    process.terminate()
    process.wait()
    print("Application terminated.")



 # Replace with your actual API base URL

def run__itenerary_tests():
    test_results = []
    BASE_URL = "http://localhost:7878/api/itineraries" 
    # Test Case 1: Fetch all itineraries
    try:
        response = requests.get(BASE_URL)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch all itineraries",
            "endpoint": f"GET {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch all itineraries",
            "endpoint": f"GET {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

     # Test Case 4: Add a new itinerary
    try:
        new_itinerary = {
            "id":1,
            "destination": "Paris",
            "budget": 50000.0,
            "travelMode": "Air",
            "notes": "Romantic getaway"
        }
        response = requests.post(BASE_URL, json=new_itinerary)
        status = "PASSED" if response.status_code == 201 else "FAILED"
        test_results.append({
            "testCase": "Add a new itinerary",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add a new itinerary",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })


    # Test Case 2: Fetch itinerary by ID
    try:
        itinerary_id = 1  # Replace with a valid ID
        response = requests.get(f"{BASE_URL}/{itinerary_id}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch itinerary by ID",
            "endpoint": f"GET {BASE_URL}/{itinerary_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch itinerary by ID",
            "endpoint": f"GET {BASE_URL}/{itinerary_id}",
            "status": "FAILED",
            "error": str(e)
        })


    # Test Case 3: Fetch non-existent itinerary by ID
    try:
        non_existent_id = 9999
        response = requests.get(f"{BASE_URL}/{non_existent_id}")
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Fetch non-existent itinerary by ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch non-existent itinerary by ID",
            "endpoint": f"GET {BASE_URL}/{non_existent_id}",
            "status": "FAILED",
            "error": str(e)
        })

   
    # Test Case 5: Add itinerary with budget out of range
    try:
        invalid_budget_itinerary = {
            "id":2,
            "destination": "Bali",
            "budget": 500.0,  # Out of range (less than 1,000)
            "travelMode": "Air",
            "notes": "Honeymoon trip"
        }
        response = requests.post(BASE_URL, json=invalid_budget_itinerary)
        status = "PASSED" if response.status_code == 400 else "FAILED"
        test_results.append({
            "testCase": "Add itinerary with budget out of range",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add itinerary with budget out of range",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 6: Add itinerary with invalid travel mode
    try:
        invalid_travel_mode_itinerary = {
            "id": 3,
            "destination": "Tokyo",
            "budget": 10000.0,
            "travelMode": "Space Shuttle",  # Invalid value
            "notes": "Futuristic adventure"
        }
        response = requests.post(BASE_URL, json=invalid_travel_mode_itinerary)
        status = "PASSED" if response.status_code == 400 else "FAILED"
        test_results.append({
            "testCase": "Add itinerary with invalid travel mode",
            "endpoint": f"POST {BASE_URL}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Add itinerary with invalid travel mode",
            "endpoint": f"POST {BASE_URL}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 7: Update an existing itinerary
    try:
        itinerary_id = 1  # Replace with a valid ID
        updated_itinerary = {
            "destination": "Paris Europe",
            "budget": 60000.0,
            "travelMode": "Air",
            "notes": "Updated romantic getaway"
        }
        response = requests.put(f"{BASE_URL}/{itinerary_id}", json=updated_itinerary)
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Update an existing itinerary",
            "endpoint": f"PUT {BASE_URL}/{itinerary_id}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Update an existing itinerary",
            "endpoint": f"PUT {BASE_URL}/{itinerary_id}",
            "status": "FAILED",
            "error": str(e)
        })

    # Test Case 9: Fetch itineraries by destination
    try:
        destination = "Paris Europe"
        response = requests.get(f"{BASE_URL}/destination/{destination}")
        status = "PASSED" if response.status_code == 200 else "FAILED"
        test_results.append({
            "testCase": "Fetch itineraries by destination",
            "endpoint": f"GET {BASE_URL}/destination/{destination}",
            "status": status,
            "response": response.json() if status == "PASSED" else response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch itineraries by destination",
            "endpoint": f"GET {BASE_URL}/destination/{destination}",
            "status": "FAILED",
            "error": str(e)
        })


    # Test Case 8: Delete an itinerary
    try:
        itinerary_id = 1  # Replace with a valid ID
        response = requests.delete(f"{BASE_URL}/{itinerary_id}")
        status = "PASSED" if response.status_code == 204 else "FAILED"
        test_results.append({
            "testCase": "Delete an itinerary",
            "endpoint": f"DELETE {BASE_URL}/{itinerary_id}",
            "status": status,
            "response": response.text if status == "FAILED" else "No Content"
        })
    except Exception as e:
        test_results.append({
            "testCase": "Delete an itinerary",
            "endpoint": f"DELETE {BASE_URL}/{itinerary_id}",
            "status": "FAILED",
            "error": str(e)
        })

    
    # Test Case 10: Fetch itineraries for non-existent destination
    try:
        non_existent_destination = "Atlantis"
        response = requests.get(f"{BASE_URL}/destination/{non_existent_destination}")
        status = "PASSED" if response.status_code == 404 else "FAILED"
        test_results.append({
            "testCase": "Fetch itineraries for non-existent destination",
            "endpoint": f"GET {BASE_URL}/destination/{non_existent_destination}",
            "status": status,
            "response": response.text
        })
    except Exception as e:
        test_results.append({
            "testCase": "Fetch itineraries for non-existent destination",
            "endpoint": f"GET {BASE_URL}/destination/{non_existent_destination}",
            "status": "FAILED",
            "error": str(e)
        })

    return test_results






  
  
