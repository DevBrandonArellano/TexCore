import requests
data = {
    "id": 1,
    "fecha_pedido": "2024-01-01T12:00:00Z",
    "detalles": []
}
r = requests.post('http://localhost:8001/pdf/nota-venta', json=data)
print(r.status_code)
print(r.text)
