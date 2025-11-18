"""
Test CSV submission endpoint directly
"""
import requests
import os

# Configuration
API_URL = "http://localhost:8000"
LOGIN_EMAIL = "lokichowdaryt@gmail.com"
LOGIN_PASSWORD = input("Enter your password: ")

def test_csv_upload():
    print("=" * 60)
    print("CSV UPLOAD ENDPOINT TEST")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Logging in...")
    login_response = requests.post(
        f"{API_URL}/login",
        json={"email": LOGIN_EMAIL, "password": LOGIN_PASSWORD}
    )
    
    if login_response.status_code != 200:
        print(f"❌ Login failed: {login_response.status_code}")
        print(login_response.json())
        return
    
    token = login_response.json().get("access_token")
    print(f"✅ Login successful! Token: {token[:20]}...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Step 2: List computations
    print("\n2. Listing your computations...")
    comp_response = requests.get(
        f"{API_URL}/secure-computations/computations",
        headers=headers
    )
    
    if comp_response.status_code != 200:
        print(f"❌ Failed to list computations: {comp_response.status_code}")
        return
    
    computations = comp_response.json()
    print(f"✅ Found {len(computations)} computations")
    
    if len(computations) == 0:
        print("\n⚠️ NO COMPUTATIONS FOUND!")
        print("You need to create a computation first before submitting CSV data.")
        print("\nSteps:")
        print("1. Go to Secure Computations page")
        print("2. Click 'New Computation'")
        print("3. Fill in details and create")
        print("4. Then come back to submit CSV")
        return
    
    # Show available computations (filter out completed ones)
    print("\n📋 Available Computations:")
    waiting_computations = [c for c in computations if c.get('status') != 'completed']
    
    if len(waiting_computations) == 0:
        print("⚠️ All computations are COMPLETED!")
        print("\nYou need to create a NEW computation to submit data.")
        print("\nCompleted computations found:")
        for idx, comp in enumerate(computations[:5], 1):
            comp_id = comp.get('computation_id', 'N/A')
            comp_name = comp.get('name') or comp.get('computation_name') or 'Unnamed'
            comp_type = comp.get('computation_type', 'N/A')
            comp_status = comp.get('status', 'N/A')
            print(f"  {idx}. {comp_name} (ID: {comp_id[:8]}..., Type: {comp_type}, Status: {comp_status})")
        
        print("\n✅ Create a new computation:")
        print("1. Go to: http://localhost:3000/secure-computations")
        print("2. Click 'New Computation'")
        print("3. Fill in details and create")
        print("4. Then run this script again")
        return
    
    # Show only waiting/active computations
    for idx, comp in enumerate(waiting_computations[:5], 1):
        comp_id = comp.get('computation_id', 'N/A')
        comp_name = comp.get('name') or comp.get('computation_name') or 'Unnamed'
        comp_type = comp.get('computation_type', 'N/A')
        comp_status = comp.get('status', 'N/A')
        print(f"{idx}. {comp_name} (ID: {comp_id[:8]}..., Type: {comp_type}, Status: {comp_status})")
    
    # Step 3: Select computation
    if len(waiting_computations) == 1:
        selected_comp = waiting_computations[0]
        comp_name = selected_comp.get('name') or selected_comp.get('computation_name') or 'Unnamed'
        print(f"\n✅ Auto-selected the only active computation: {comp_name}")
    else:
        try:
            choice = int(input(f"\nSelect computation (1-{min(5, len(waiting_computations))}): ")) - 1
            selected_comp = waiting_computations[choice]
        except:
            print("❌ Invalid selection")
            return
    
    computation_id = selected_comp['computation_id']
    comp_name = selected_comp.get('name') or selected_comp.get('computation_name') or 'Unnamed'
    print(f"✅ Selected: {comp_name} ({computation_id})")
    
    # Step 4: Prepare CSV file
    csv_file_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "sample_data",
        "correlation_analysis_numeric_only.csv"
    )
    
    if not os.path.exists(csv_file_path):
        print(f"❌ CSV file not found: {csv_file_path}")
        return
    
    print(f"\n3. Preparing to upload CSV...")
    print(f"   File: {csv_file_path}")
    print(f"   Size: {os.path.getsize(csv_file_path)} bytes")
    
    # Step 5: Submit CSV
    print("\n4. Submitting CSV...")
    
    with open(csv_file_path, 'rb') as f:
        files = {'file': ('correlation_analysis_numeric_only.csv', f, 'text/csv')}
        data = {
            'description': 'Test CSV upload',
            'has_header': 'true',
            'delimiter': ',',
        }
        
        submit_response = requests.post(
            f"{API_URL}/secure-computations/computations/{computation_id}/submit-csv",
            headers=headers,
            files=files,
            data=data
        )
    
    print(f"\n📊 Response Status: {submit_response.status_code}")
    
    if submit_response.status_code == 200:
        print("✅ CSV UPLOAD SUCCESSFUL!")
        print(submit_response.json())
    else:
        print(f"❌ CSV UPLOAD FAILED!")
        print(f"Status: {submit_response.status_code}")
        try:
            error_data = submit_response.json()
            print(f"Error: {error_data.get('detail', 'Unknown error')}")
            print(f"Full response: {error_data}")
        except:
            print(f"Response text: {submit_response.text}")

if __name__ == "__main__":
    test_csv_upload()
