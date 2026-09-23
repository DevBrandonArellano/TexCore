"""
Tests del middleware de autenticación JWT del printing_service.
Convención ISTQB CTFL v4.0:
test_[objeto]_dado_[contexto]_cuando_[acción]_entonces_[resultado]

Antes de este fix, cualquier actor con acceso a la red interna de Docker
podía generar PDFs/ZPL con datos arbitrarios (notas de venta, etiquetas)
sin ninguna credencial — este archivo prueba que ya no es posible.
"""
from unittest.mock import patch

import jwt as pyjwt

_ETIQUETA_PAYLOAD = {
    "producto_desc": "Hilo Acrílico 20/1",
    "lote_codigo": "LOT-0001",
    "peso_neto": 25.0,
    "qr_data": "LOT-0001",
}

_NOTA_VENTA_PAYLOAD = {
    "id": 1,
    "fecha_pedido": "2026-09-22",
    "detalles": [],
}


class TestZplEndpointAuth:

    def test_zpl_dado_sin_authorization_header_cuando_post_entonces_401(self, app_client):
        response = app_client.post("/zpl/etiqueta", json=_ETIQUETA_PAYLOAD)
        assert response.status_code == 401
        assert "Bearer" in response.json()["detail"]

    def test_zpl_dado_header_sin_bearer_cuando_post_entonces_401(self, app_client):
        response = app_client.post(
            "/zpl/etiqueta", json=_ETIQUETA_PAYLOAD, headers={"Authorization": "Token abc"}
        )
        assert response.status_code == 401

    def test_zpl_dado_token_con_bearer_valido_cuando_post_entonces_no_401(self, app_client, auth_headers):
        response = app_client.post("/zpl/etiqueta", json=_ETIQUETA_PAYLOAD, headers=auth_headers)
        assert response.status_code != 401


class TestPdfEndpointAuth:

    def test_pdf_dado_sin_authorization_header_cuando_post_entonces_401(self, app_client):
        response = app_client.post("/pdf/nota-venta", json=_NOTA_VENTA_PAYLOAD)
        assert response.status_code == 401

    def test_pdf_dado_token_con_bearer_valido_cuando_post_entonces_no_401(self, app_client, auth_headers):
        response = app_client.post("/pdf/nota-venta", json=_NOTA_VENTA_PAYLOAD, headers=auth_headers)
        assert response.status_code != 401


class TestHealthEndpointSinAuth:

    def test_health_dado_sin_authorization_header_cuando_get_entonces_no_requiere_auth(self, app_client):
        response = app_client.get("/health")
        assert response.status_code != 401


class TestTokenInvalido:

    def test_zpl_dado_token_expirado_cuando_post_entonces_401(self, app_client):
        with patch("src.main.jwt.decode", side_effect=pyjwt.ExpiredSignatureError()):
            response = app_client.post(
                "/zpl/etiqueta", json=_ETIQUETA_PAYLOAD, headers={"Authorization": "Bearer expired"}
            )
        assert response.status_code == 401
        assert "expirado" in response.json()["detail"].lower()

    def test_zpl_dado_tipo_token_incorrecto_cuando_post_entonces_401(self, app_client):
        payload_refresh = {"iss": "texcore", "sub": "svc", "type": "service_refresh"}
        with patch("src.main.jwt.decode", return_value=payload_refresh):
            response = app_client.post(
                "/zpl/etiqueta", json=_ETIQUETA_PAYLOAD, headers={"Authorization": "Bearer x"}
            )
        assert response.status_code == 401
        assert "service_access" in response.json()["detail"]

    def test_zpl_dado_emisor_no_reconocido_cuando_post_entonces_401(self, app_client):
        payload_bad_iss = {"iss": "otro-sistema", "sub": "svc", "type": "service_access"}
        with patch("src.main.jwt.decode", return_value=payload_bad_iss):
            response = app_client.post(
                "/zpl/etiqueta", json=_ETIQUETA_PAYLOAD, headers={"Authorization": "Bearer x"}
            )
        assert response.status_code == 401
