"""
Prueba de carga concurrente TexCore — simula 100 usuarios reales repartidos
entre los 11 roles RBAC reales del sistema (Django Groups): admin_sistemas,
admin_sede, bodeguero, despacho, ejecutivo, empaquetado, jefe_area,
jefe_planta, operario, tintorero, vendedor. NO se inventan roles nuevos —
cada clase de usuario simulado corresponde 1:1 a un grupo real, y solo
ejecuta las acciones HTTP que ese rol tiene permitido hacer en el sistema
real (ver evidencia de código citada en cada clase).

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
vez por cada uno de los 11 usuarios demo (uno por rol, respetando el
límite) al arrancar la prueba, y cada usuario virtual de ese rol reutiliza
esa sesión ya autenticada — igual que varias pestañas de navegador de la
misma persona, no logins nuevos por cada usuario virtual.

IMPORTANTE — mutación de datos: los roles despacho, empaquetado, operario y
vendedor mutan datos reales (stock, lotes, pedidos, historial de despacho).
Correr esta prueba EXCLUSIVAMENTE contra el stack Docker de pruebas
sembrado con `python manage.py stress_test_data` / `stress_ventas_data`,
NUNCA contra producción.
"""
import random
import time

from locust import HttpUser, events, task, between


# Un usuario demo por rol — exactamente los 11 grupos RBAC reales, creados
# por `stress_test_data` (gestion/management/commands/stress_test_data.py,
# función ensure_user) y `stress_ventas_data`. NO agregar roles/usuarios
# nuevos aquí: si el sistema alguna vez tiene más de 11 grupos, actualizar
# esta lista para que siga siendo 1:1 con los grupos reales de Django.
ROLE_USERS = {
    "admin_sistemas": "user_admin_sistemas",
    "admin_sede": "user_admin_sede",
    "bodeguero": "user_bodeguero",
    "despacho": "user_despacho",
    "ejecutivo": "user_ejecutivo",
    "empaquetado": "user_empaquetado",
    "jefe_area": "user_jefe_area",
    "jefe_planta": "user_jefe_planta",
    "operario": "user_operario",
    "tintorero": "user_tintorero",
    "vendedor": "user_vendedor",
}
DEMO_PASSWORD = "password123"

# Umbral de negocio para el escaneo de lotes durante el despacho (rol
# `despacho`, ver DespachoUser más abajo).
UMBRAL_ESCANEO_SEGUNDOS = 1.0

# Una cookie JWT ya autenticada por rol — poblada una sola vez en
# test_start (ver abajo) y reutilizada por todos los HttpUser de ese rol.
_role_cookies: dict[str, dict] = {}


@events.test_start.add_listener
def _preauth_role_users(environment, **kwargs):
    import requests

    base_url = environment.host
    for role, username in ROLE_USERS.items():
        resp = requests.post(
            f"{base_url}/api/token/",
            json={"username": username, "password": DEMO_PASSWORD},
            verify=False,
        )
        if resp.status_code == 200:
            _role_cookies[role] = dict(resp.cookies)
        else:
            print(f"[preauth] {username} ({role}) -> {resp.status_code} {resp.text[:200]}")
        # Respeta login_zone (rate=5r/m, burst=3, nodelay — nginx/nginx.conf:13,39):
        # con nodelay, nginx sirve las primeras ~4 peticiones sin demora pero
        # el balde solo se recarga a 1 token cada 12s; con 11 logins secuenciales,
        # un espaciado de 3s (válido para 4 usuarios) agota el balde y el resto
        # recibe 429. 13s es seguro para cualquier cantidad de logins.
        time.sleep(13)


def _extraer_lista(payload):
    """DRF puede paginar (`{"results": [...]}`) o no (`[...]`) según el
    ViewSet — normaliza ambos casos para los pools de datos."""
    if isinstance(payload, dict):
        return payload.get("results", [])
    if isinstance(payload, list):
        return payload
    return []


_PREAUTH_TIMEOUT_SEGUNDOS = 200  # > 11 roles * 13s de espaciado del login_zone


class _UsuarioRolBase(HttpUser):
    """Base compartida: cada subclase fija `role` a una de las claves de
    ROLE_USERS y hereda la sesión ya autenticada de ese rol.

    Locust genera (spawnea) usuarios casi de inmediato al arrancar la
    corrida, mientras que _preauth_role_users autentica los 11 roles en
    serie respetando el rate-limit de login (~2.5 min en total) — así que
    on_start() de los primeros usuarios se ejecuta ANTES de que exista la
    cookie de su rol. Por eso se espera activamente (con timeout) en vez
    de fallar de inmediato.
    """
    abstract = True
    role: str = ""

    def on_start(self):
        esperado = 0.0
        while self.role not in _role_cookies and esperado < _PREAUTH_TIMEOUT_SEGUNDOS:
            time.sleep(2)
            esperado += 2

        cookies = _role_cookies.get(self.role)
        if not cookies:
            raise RuntimeError(
                f"No hay sesión pre-autenticada para el rol '{self.role}' "
                f"({ROLE_USERS.get(self.role)}) tras esperar "
                f"{_PREAUTH_TIMEOUT_SEGUNDOS}s — revisa el log de "
                "'[preauth]' (usuario inexistente/credenciales incorrectas: "
                "corre 'python manage.py stress_test_data' primero)."
            )
        for name, value in cookies.items():
            self.client.cookies.set(name, value)


# ---------------------------------------------------------------------------
# 1. admin_sistemas — acceso amplio a catálogo/config (gestion/permissions.py
#    IsSystemAdmin; frontend/src/components/admin-sistemas/Manage*.tsx)
# ---------------------------------------------------------------------------
class AdminSistemasUser(_UsuarioRolBase):
    role = "admin_sistemas"
    weight = 9
    wait_time = between(1, 4)

    @task
    def navegar_catalogo(self):
        endpoint = random.choice([
            "/api/productos/", "/api/users/", "/api/sedes/",
            "/api/areas/", "/api/bodegas/", "/api/proveedores/",
        ])
        self.client.get(endpoint, name=endpoint)

    @task
    def ver_audit_logs(self):
        self.client.get("/api/inventory/audit-logs/", name="/api/inventory/audit-logs/")


# ---------------------------------------------------------------------------
# 2. admin_sede — igual que admin_sistemas pero acotado a su sede
#    (inventory/views.py:1002-1013, IsDespachoReader/Writer)
# ---------------------------------------------------------------------------
class AdminSedeUser(_UsuarioRolBase):
    role = "admin_sede"
    weight = 9
    wait_time = between(1, 4)

    @task
    def ver_audit_logs(self):
        self.client.get("/api/inventory/audit-logs/", name="/api/inventory/audit-logs/")

    @task
    def ver_stock_y_despachos(self):
        endpoint = random.choice([
            "/api/inventory/stock/", "/api/users/", "/api/inventory/historial-despachos/",
        ])
        self.client.get(endpoint, name=endpoint)


# ---------------------------------------------------------------------------
# 3. bodeguero — recepción de materia prima y consulta de stock de sus
#    bodegas asignadas (gestion/permissions.py IsBodegueroOrAdmin;
#    frontend/src/components/bodeguero/BodegueroDashboard.tsx:168-182)
# ---------------------------------------------------------------------------
class BodegueroUser(_UsuarioRolBase):
    role = "bodeguero"
    weight = 9
    wait_time = between(1, 4)

    @task
    def navegar_bodega(self):
        endpoint = random.choice([
            "/api/materia-prima/", "/api/productos/", "/api/bodegas/",
            "/api/lotes-produccion/", "/api/proveedores/",
        ])
        self.client.get(endpoint, name=endpoint)

    @task
    def ver_alertas_y_stock(self):
        endpoint = random.choice(["/api/inventory/alertas-stock/", "/api/inventory/stock/"])
        self.client.get(endpoint, name=endpoint)


# ---------------------------------------------------------------------------
# 4. despacho — único rol (junto a admins) con IsDespachoWriter: escanea
#    lotes y despacha, transfiere stock entre bodegas, revierte despachos.
#    (inventory/permissions.py:16-28; DespachoDashboard.tsx:160,192;
#    TransferenciaStockAPIView; HistorialDespachos.tsx:151)
#
#    El umbral de negocio (<1s por escaneo) se valida aquí con
#    catch_response=True: cada llamada de escaneo se marca como fallo
#    explícito si supera UMBRAL_ESCANEO_SEGUNDOS, además de registrarse
#    bajo un `name` propio ("... (en despacho)") para poder ver su
#    percentil por separado del resto de tareas en el CSV/UI de Locust.
# ---------------------------------------------------------------------------
class DespachoUser(_UsuarioRolBase):
    role = "despacho"
    weight = 9
    wait_time = between(2, 6)

    def on_start(self):
        super().on_start()
        self._pedidos_pendientes: list[int] = []
        self._lotes_con_stock: list[str] = []
        self._bodegas: list[int] = []
        self._stock_disponible: list[dict] = []
        self._refrescar_pools()

    def _refrescar_pools(self):
        resp = self.client.get("/api/pedidos-venta/", name="/api/pedidos-venta/ (pool despacho)")
        if resp.status_code == 200:
            self._pedidos_pendientes = [
                p["id"] for p in _extraer_lista(resp.json()) if p.get("estado") == "pendiente"
            ]

        resp = self.client.get("/api/inventory/stock/", name="/api/inventory/stock/ (pool despacho)")
        if resp.status_code == 200:
            items = _extraer_lista(resp.json())
            self._lotes_con_stock = [
                s["lote_codigo"] for s in items
                if s.get("lote_codigo") and float(s.get("cantidad") or 0) > 0
            ]
            self._stock_disponible = [s for s in items if float(s.get("cantidad") or 0) > 0]

        resp = self.client.get("/api/bodegas/", name="/api/bodegas/ (pool despacho)")
        if resp.status_code == 200:
            self._bodegas = [b["id"] for b in _extraer_lista(resp.json())]

    @task(50)
    def flujo_despacho(self):
        """Flujo real: N escaneos (uno por lote, igual que
        DespachoDashboard.tsx handleScan) + 1 POST a process-despacho."""
        if not self._pedidos_pendientes or not self._lotes_con_stock:
            self._refrescar_pools()
        if not self._pedidos_pendientes or not self._lotes_con_stock:
            return  # pool agotado — no-op en vez de fallar el run

        pedido_id = random.choice(self._pedidos_pendientes)
        n_lotes = min(len(self._lotes_con_stock), random.randint(2, 4))
        lotes_escaneados = random.sample(self._lotes_con_stock, n_lotes)

        for codigo_lote in lotes_escaneados:
            with self.client.post(
                "/api/scanning/validate",
                json={"code": codigo_lote},
                name="/api/scanning/validate (en despacho)",
                catch_response=True,
            ) as response:
                elapsed = response.elapsed.total_seconds() if response.elapsed else None
                if response.status_code >= 500:
                    response.failure(f"HTTP {response.status_code}")
                elif elapsed is not None and elapsed > UMBRAL_ESCANEO_SEGUNDOS:
                    response.failure(
                        f"Escaneo tardó {elapsed:.3f}s — supera el umbral de "
                        f"{UMBRAL_ESCANEO_SEGUNDOS}s"
                    )
                else:
                    response.success()

        self.client.post(
            "/api/inventory/process-despacho/",
            json={
                "pedidos": [pedido_id],
                "lotes": lotes_escaneados,
                "observaciones": "Despacho generado por stress test 100 usuarios",
                "confirmar_incompleto": True,
            },
            name="/api/inventory/process-despacho/",
        )

        self._pedidos_pendientes = [p for p in self._pedidos_pendientes if p != pedido_id]
        self._lotes_con_stock = [c for c in self._lotes_con_stock if c not in lotes_escaneados]

    @task(30)
    def transferir_stock(self):
        if len(self._bodegas) < 2 or not self._stock_disponible:
            self._refrescar_pools()
        if len(self._bodegas) < 2 or not self._stock_disponible:
            return

        item = random.choice(self._stock_disponible)
        bodega_origen = item["bodega_id"]
        destinos_posibles = [b for b in self._bodegas if b != bodega_origen]
        if not destinos_posibles:
            return
        cantidad_disponible = float(item["cantidad"])
        cantidad_a_mover = round(min(cantidad_disponible, random.uniform(1, 10)), 2)
        if cantidad_a_mover <= 0:
            return

        self.client.post(
            "/api/inventory/transferencias/",
            json={
                "producto_id": item["producto_id"],
                "bodega_origen_id": bodega_origen,
                "bodega_destino_id": random.choice(destinos_posibles),
                "cantidad": cantidad_a_mover,
                "lote_id": item.get("lote_id"),
                "observaciones": "Transferencia generada por stress test 100 usuarios",
            },
            name="/api/inventory/transferencias/",
        )
        item["cantidad"] = cantidad_disponible - cantidad_a_mover

    @task(20)
    def revertir_despacho(self):
        resp = self.client.get(
            "/api/inventory/historial-despachos/",
            name="/api/inventory/historial-despachos/ (pool reversion)",
        )
        if resp.status_code != 200:
            return
        # revertir/ elimina el HistorialDespacho al procesar la reversión
        # (ver HistorialDespachoViewSet.revertir en inventory/views.py) —
        # no existe un flag 'revertido': cualquier registro listado
        # todavía existe y es candidato a revertirse.
        candidatos = [h["id"] for h in _extraer_lista(resp.json())]
        if not candidatos:
            return

        historial_id = random.choice(candidatos)
        self.client.post(
            f"/api/inventory/historial-despachos/{historial_id}/revertir/",
            json={"justificacion": "Reversión generada por stress test 100 usuarios"},
            name="/api/inventory/historial-despachos/{id}/revertir/",
        )


# ---------------------------------------------------------------------------
# 5. ejecutivo — solo lectura: KPIs, reportes, alertas (IsDespachoReader;
#    EjecutivosDashboard.tsx:268,291-297,453)
# ---------------------------------------------------------------------------
class EjecutivoUser(_UsuarioRolBase):
    role = "ejecutivo"
    weight = 9
    wait_time = between(1, 4)

    @task(60)
    def ver_kpis_y_resumen(self):
        endpoint = random.choice([
            "/api/kpi-ejecutivo/", "/api/produccion/resumen/", "/api/produccion/tendencia/",
            "/api/inventory/alertas-stock/", "/api/inventory/stock/",
            "/api/clientes/", "/api/sedes/",
        ])
        self.client.get(endpoint, name=endpoint)

    @task(20)
    def ver_pedidos(self):
        self.client.get("/api/pedidos-venta/?limit=200", name="/api/pedidos-venta/ (ejecutivo)")

    @task(20)
    def exportar_reporte(self):
        ruta = random.choice([
            "gerencial/ventas", "gerencial/top-clientes", "gerencial/deudores",
            "produccion/ordenes", "produccion/lotes", "produccion/tendencia",
        ])
        self.client.get(
            f"/api/reporting/{ruta}", params={"format": "xlsx"},
            name=f"/api/reporting/{ruta} (export)",
        )


# ---------------------------------------------------------------------------
# 6. empaquetado — registra lotes de órdenes en proceso y consulta
#    máquinas/lotes (EmpaquetadoDashboard.tsx:166-168,204,237;
#    gestion/views/production_views.py:531)
# ---------------------------------------------------------------------------
class EmpaquetadoUser(_UsuarioRolBase):
    role = "empaquetado"
    weight = 9
    wait_time = between(2, 5)

    @task
    def navegar_produccion(self):
        endpoint = random.choice([
            "/api/ordenes-produccion/?estado=en_proceso", "/api/maquinas/",
            "/api/lotes-produccion/?ordering=-id&limit=200",
        ])
        self.client.get(endpoint, name=endpoint.split("?")[0])


# ---------------------------------------------------------------------------
# 7. jefe_area — supervisión de área: KPIs, máquinas, órdenes
#    (gestion/permissions.py IsJefeAreaOrAdmin; JefeAreaDashboard.tsx:201-206)
# ---------------------------------------------------------------------------
class JefeAreaUser(_UsuarioRolBase):
    role = "jefe_area"
    weight = 9
    wait_time = between(1, 4)

    @task
    def navegar_area(self):
        endpoint = random.choice([
            "/api/kpi-area/", "/api/maquinas/", "/api/ordenes-produccion/",
            "/api/users/", "/api/productos/", "/api/lotes-produccion/",
        ])
        self.client.get(endpoint, name=endpoint)


# ---------------------------------------------------------------------------
# 8. jefe_planta — visión de planta completa, crea/gestiona órdenes de
#    producción (JefePlantaDashboard.tsx:33-40,79,97,116)
# ---------------------------------------------------------------------------
class JefePlantaUser(_UsuarioRolBase):
    role = "jefe_planta"
    weight = 9
    wait_time = between(1, 4)

    @task
    def navegar_planta(self):
        endpoint = random.choice([
            "/api/ordenes-produccion/", "/api/productos/", "/api/formula-colors/",
            "/api/sedes/", "/api/maquinas/", "/api/areas/", "/api/bodegas/", "/api/users/",
        ])
        self.client.get(endpoint, name=endpoint)


# ---------------------------------------------------------------------------
# 9. operario — ejecuta órdenes en máquina y registra lotes producidos
#    (OperarioDashboard.tsx:59,75,149,189,213; RegistrarLoteProduccionView)
# ---------------------------------------------------------------------------
class OperarioUser(_UsuarioRolBase):
    role = "operario"
    weight = 9
    wait_time = between(2, 5)

    def on_start(self):
        super().on_start()
        self._ordenes_en_proceso: list[dict] = []
        self._refrescar_pool()

    def _refrescar_pool(self):
        resp = self.client.get(
            "/api/ordenes-produccion/?estado=en_proceso",
            name="/api/ordenes-produccion/ (pool operario)",
        )
        if resp.status_code == 200:
            self._ordenes_en_proceso = _extraer_lista(resp.json())

    @task(70)
    def navegar_ordenes_y_lotes(self):
        endpoint = random.choice(["/api/ordenes-produccion/", "/api/lotes-produccion/"])
        self.client.get(endpoint, name=endpoint)

    @task(30)
    def registrar_lote(self):
        if not self._ordenes_en_proceso:
            self._refrescar_pool()
        if not self._ordenes_en_proceso:
            return  # pool agotado — no-op

        orden = random.choice(self._ordenes_en_proceso)
        ahora = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.client.post(
            f"/api/ordenes-produccion/{orden['id']}/registrar-lote/",
            json={
                "codigo_lote": f"LOT-STR-{orden['id']}-{random.randint(1000, 9999)}",
                "peso_neto_producido": str(round(random.uniform(10, 80), 2)),
                "turno": random.choice(["Mañana", "Tarde", "Noche"]),
                "hora_inicio": ahora,
                "hora_final": ahora,
            },
            name="/api/ordenes-produccion/{id}/registrar-lote/",
        )


# ---------------------------------------------------------------------------
# 10. tintorero — consulta y gestiona fórmulas de color y químicos
#     (gestion/permissions.py IsTintoreroOrAdmin; TintoreroDashboard.tsx:46-47)
# ---------------------------------------------------------------------------
class TintoreroUser(_UsuarioRolBase):
    role = "tintorero"
    weight = 9
    wait_time = between(1, 4)

    @task
    def navegar_formulas(self):
        endpoint = random.choice(["/api/formula-colors/", "/api/chemicals/"])
        self.client.get(endpoint, name=endpoint)


# ---------------------------------------------------------------------------
# 11. vendedor — gestiona sus propios clientes y pedidos de venta
#     (gestion/views/sales_views.py: filtra por vendedor_asignado;
#     VendedorDashboard.tsx:447-449,625)
# ---------------------------------------------------------------------------
class VendedorUser(_UsuarioRolBase):
    role = "vendedor"
    weight = 9
    wait_time = between(2, 5)

    def on_start(self):
        super().on_start()
        self._clientes: list[int] = []
        self._productos: list[dict] = []
        self._refrescar_pools()

    def _refrescar_pools(self):
        resp = self.client.get("/api/clientes/", name="/api/clientes/ (pool vendedor)")
        if resp.status_code == 200:
            self._clientes = [c["id"] for c in _extraer_lista(resp.json())]

        resp = self.client.get("/api/productos/", name="/api/productos/ (pool vendedor)")
        if resp.status_code == 200:
            self._productos = [p for p in _extraer_lista(resp.json()) if p.get("id")]

    @task(70)
    def navegar_clientes_y_pedidos(self):
        endpoint = random.choice(["/api/clientes/", "/api/pedidos-venta/?limit=100", "/api/productos/"])
        self.client.get(endpoint, name=endpoint.split("?")[0])

    @task(30)
    def crear_pedido(self):
        if not self._clientes or not self._productos:
            self._refrescar_pools()
        if not self._clientes or not self._productos:
            return  # pool agotado — no-op

        producto = random.choice(self._productos)
        self.client.post(
            "/api/pedidos-venta/",
            json={
                "cliente": random.choice(self._clientes),
                "estado": "pendiente",
                "esta_pagado": False,
                "guia_remision": f"GR-STR-{random.randint(100000, 999999)}",
                "detalles": [{
                    "producto": producto["id"],
                    "cantidad": random.randint(1, 5),
                    "peso": round(random.uniform(5, 50), 2),
                    "precio_unitario": round(random.uniform(2, 20), 2),
                    "incluye_iva": True,
                }],
            },
            name="/api/pedidos-venta/ (crear)",
        )
