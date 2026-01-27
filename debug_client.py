import requests
import json

# Configuration
BASE_URL = 'http://localhost:8000/api'
LOGIN_URL = f'{BASE_URL}/token/'
CLIENTES_URL = f'{BASE_URL}/clientes/'
USERNAME = 'user_vendedor'
PASSWORD = 'password123'

payload = {
    "ruc_cedula": "1234567890",
    "nombre_razon_social": "Cliente Test Debug",
    "direccion_envio": "Av. Test 123",
    "nivel_precio": "normal",
    "tiene_beneficio": False,
    "saldo_pendiente": "0.00" 
}

# 1. Login to get token
try:
    session = requests.Session()
    login_resp = session.post(LOGIN_URL, json={'username': USERNAME, 'password': PASSWORD})
    
    if login_resp.status_code != 200:
        print(f"Error Login: {login_resp.status_code}")
        print(login_resp.text)
        exit(1)
        
    print("Login success")
    
    # 2. Try POST cliente
    resp = session.post(CLIENTES_URL, json=payload)
    print(f"Create Client Status: {resp.status_code}")
    print("Response Body:")
    print(json.dumps(resp.json(), indent=2))

except Exception as e:
    print(f"Exception: {e}")
