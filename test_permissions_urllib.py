
import urllib.request
import urllib.parse
import json
import http.cookiejar
import sys

BASE_URL = "http://localhost:8000/api"
LOGIN_URL = f"{BASE_URL}/token/"
SEDES_URL = f"{BASE_URL}/sedes/"

USERNAME = "Adminitrador"
PASSWORD = "password123"

# Setup cookie jar
cj = http.cookiejar.CookieJar()
opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def make_request(url, data=None):
    if data:
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(url, data=json_data, headers={'Content-Type': 'application/json'})
    else:
        req = urllib.request.Request(url)
    
    try:
        response = opener.open(req)
        return response.status, response.read().decode('utf-8')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8')
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

def test_create_sede():
    # 1. Login
    print(f"Logging in as {USERNAME}...")
    status, body = make_request(LOGIN_URL, {"username": USERNAME, "password": PASSWORD})
    
    if status != 200:
        print(f"Login failed: {status} {body}")
        sys.exit(1)
    
    print("Login successful.")
    print("Cookies:")
    for cookie in cj:
        print(f"  {cookie.name}={cookie.value}")

    # 2. Try to create Sede
    new_sede = {
        "nombre": "Sede Test Automated Urllib",
        "direccion": "Calle 123",
        "telefono": "5551234"
    }
    
    print("Attempting to create Sede...")
    status, body = make_request(SEDES_URL, new_sede)
    
    print(f"Create Sede Status: {status}")
    print(f"Create Sede Response: {body}")

    if status == 201:
        print("SUCCESS: Sede created.")
    elif status == 403:
        print("FAILURE: 403 Forbidden.")
    else:
        print(f"FAILURE: Unexpected status {status}.")

if __name__ == "__main__":
    test_create_sede()
