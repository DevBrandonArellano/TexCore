
import requests
import sys

BASE_URL = "http://localhost:8000/api"
LOGIN_URL = f"{BASE_URL}/token/"
SEDES_URL = f"{BASE_URL}/sedes/"

USERNAME = "Adminitrador"
PASSWORD = "password123"

def test_create_sede():
    session = requests.Session()
    
    # 1. Login
    print(f"Logging in as {USERNAME}...")
    try:
        response = session.post(LOGIN_URL, json={"username": USERNAME, "password": PASSWORD})
    except requests.exceptions.ConnectionError:
        print("Failed to connect to backend. Is it running?")
        sys.exit(1)
        
    if response.status_code != 200:
        print(f"Login failed: {response.status_code} {response.text}")
        sys.exit(1)
    
    print("Login successful. Cookies:", session.cookies.get_dict())
    
    # 2. Try to create Sede
    new_sede = {
        "nombre": "Sede Test Automated",
        "direccion": "Calle 123",
        "telefono": "5551234"
    }
    
    print("Attempting to create Sede...")
    # Note: We need to set X-CSRFToken if SessionAuth was active, but we removed it.
    # We still rely on the 'access_token' cookie which 'session' handles automatically.
    
    response = session.post(SEDES_URL, json=new_sede)
    
    print(f"Create Sede Status: {response.status_code}")
    print(f"Create Sede Response: {response.text}")

    if response.status_code == 201:
        print("SUCCESS: Sede created.")
    elif response.status_code == 403:
        print("FAILURE: 403 Forbidden.")
    else:
        print(f"FAILURE: Unexpected status.")

if __name__ == "__main__":
    test_create_sede()
