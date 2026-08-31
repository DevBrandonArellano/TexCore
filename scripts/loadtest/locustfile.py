"""
Prueba de carga concurrente TexCore — simula ~100 usuarios reales.

Uso:
    locust -f scripts/loadtest/locustfile.py --host=http://localhost

Ver scripts/loadtest/README.md para la secuencia completa (sembrar datos,
verificar RCSI, correr baseline, aplicar fixes, re-correr).

Autenticación: usa el flujo real (POST /api/token/, cookies httponly JWT),
igual que el navegador — no se salta el proxy ni la negociación de contenido
de DRF, para que la medición refleje el costo real de un request.

Nota sobre el login: nginx protege /api/token/ con rate-limiting real
(login_zone: 5 intentos/min, burst 3, POR IP — ver nginx/nginx.conf). En
producción eso es correcto porque 100 usuarios reales vienen de 100 IPs
distintas; en esta prueba, todos los usuarios virtuales de Locust salen de
la MISMA IP (la máquina donde corre Locust). Para no medir el rate-limiter
de login en vez del rendimiento de la app, este script autentica una sola
vez por cada usuario demo (respetando el límite) al arrancar la prueba, y
cada usuario virtual reutiliza una de esas sesiones ya autenticadas — igual
que 100 pestañas de navegador de 4 personas reales, no 100 logins nuevos.
"""
import itertools
import random
import time

from locust import HttpUser, events, task, between


# Usuarios demo creados por seed_production_masters / stress_test_data /
# stress_ventas_data. Ajustar si los usernames reales difieren en el entorno
# objetivo.
DEMO_USERS = [
    ("user_ejecutivo", "password123"),
    ("user_jefe_planta", "password123"),
    ("user_bodeguero", "password123"),
    ("user_vendedor", "password123"),
]

HOY = "2026-08-31"
INICIO_MES = "2026-08-01"

# Cookies JWT ya autenticadas, una por usuario demo — pobladas una sola vez
# en test_start (ver abajo) y compartidas (round-robin) entre todos los
# HttpUser simulados.
_SESSION_COOKIES: list[dict] = []
_cookie_cycle = None


@events.test_start.add_listener
def _preauth_demo_users(environment, **kwargs):
    global _cookie_cycle
    import requests

    base_url = environment.host
    for username, password in DEMO_USERS:
        resp = requests.post(
            f"{base_url}/api/token/",
            json={"username": username, "password": password},
            verify=False,
        )
        if resp.status_code == 200:
            _SESSION_COOKIES.append(dict(resp.cookies))
        else:
            print(f"[preauth] {username} -> {resp.status_code} {resp.text[:200]}")
        # Respeta login_zone (5/min, burst 3, nodelay) — espaciar evita 429.
        time.sleep(3)
    _cookie_cycle = itertools.cycle(_SESSION_COOKIES) if _SESSION_COOKIES else None


class UsuarioTexCore(HttpUser):
    # Tiempo de "pensar" entre acciones de un usuario real (no ráfaga pura)
    wait_time = between(1, 4)

    def on_start(self):
        if _cookie_cycle is None:
            raise RuntimeError(
                "No hay sesiones pre-autenticadas — revisa el log de "
                "'[preauth]' al inicio de la corrida (probablemente 401/429)."
            )
        for name, value in next(_cookie_cycle).items():
            self.client.cookies.set(name, value)

    # --- ~60% navegación normal de dashboard/listados ---
    @task(60)
    def navegar_dashboard(self):
        endpoint = random.choice([
            "/api/productos/",
            "/api/clientes/",
            "/api/pedidos-venta/",
            "/api/ordenes-produccion/",
            "/api/inventory/stock/",
            "/api/inventory/movimientos/",
            "/api/kpi-ejecutivo/",
            "/api/kpi-area/",
            "/api/produccion/resumen/",
        ])
        self.client.get(endpoint, name=endpoint)

    # --- ~30% lectura de reportes gerenciales/producción (agregación) ---
    @task(30)
    def leer_reporte_gerencial(self):
        ruta = random.choice([
            "gerencial/ventas",
            "gerencial/top-clientes",
            "gerencial/deudores",
            "produccion/ordenes",
            "produccion/lotes",
            "produccion/tendencia",
        ])
        params = {"format": "xlsx"}
        if "deudores" not in ruta:
            params.update({"fecha_inicio": INICIO_MES, "fecha_fin": HOY})
        self.client.get(
            f"/api/reporting/{ruta}",
            params=params,
            name=f"/api/reporting/{ruta} (export)",
        )

    # --- ~10% exports pesados (kardex/stock, más costosos de generar) ---
    @task(10)
    def export_pesado(self):
        self.client.get(
            "/api/reporting/export/kardex",
            params={"bodega_id": 10002, "format": "xlsx"},
            name="/api/reporting/export/kardex (export)",
        )
