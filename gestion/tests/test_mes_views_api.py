"""
API del MES (gestion/views/mes_views.py): corridas, operaciones y planes MTS.

Completa lo que no cubrían test_produccion_continua.py y test_produccion_stock.py: filtros
de los listados, alcance por sede al iniciar una corrida, la regla de que el operario no
cambia el material, los rechazos por estado y las rutas de error.

Técnicas ISTQB aplicadas (CTFL v4.0):
- Partición de equivalencia (EP): filtro presente / ausente; rol que ve todas las sedes /
  rol de una sede; recurso de la sede / de otra sede; dirección atrás / adelante.
- Transición de estados (STT): corrida finalizada; plan borrador → aprobado → cerrado.
- Caja blanca (CB): ramas de excepción inesperada (500) de los servicios.
"""

from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import LoteProduccion
from gestion.tests.factories import (
    AreaFactory,
    BodegaFactory,
    CorridaProduccionFactory,
    CustomUserFactory,
    DetallePlanProduccionFactory,
    LineaProduccionFactory,
    MaquinaFactory,
    OperacionProduccionFactory,
    OrdenProduccionFactory,
    PedidoVentaFactory,
    PlanProduccionFactory,
    ProductoFactory,
    SedeFactory,
    StockBodegaFactory,
)

CORRIDAS = "/api/corridas-produccion/"
OPERACIONES = "/api/operaciones-produccion/"
PLANES = "/api/planes-produccion/"


def _ids(resp):
    datos = resp.data["results"] if isinstance(resp.data, dict) and "results" in resp.data else resp.data
    return {fila["id"] for fila in datos}


class _BaseMes(TestCase):
    def setUp(self):
        self.sede = SedeFactory()
        self.area = AreaFactory(sede=self.sede)
        self.maquina = MaquinaFactory(area=self.area)
        self.jefe = CustomUserFactory(sede=self.sede, groups=["jefe_planta"])
        self.client = APIClient()
        self.client.force_authenticate(user=self.jefe)


class CorridaListadoFiltrosTest(_BaseMes):
    def setUp(self):
        super().setUp()
        self.linea = LineaProduccionFactory(area=self.area)
        self.objetivo = CorridaProduccionFactory(
            sede=self.sede,
            area=self.area,
            linea=self.linea,
            maquina_principal=self.maquina,
            modalidad="STOCK",
            turno="Noche",
            fecha_jornada=date(2026, 10, 27),
            estado="pausada",
        )
        otra_area = AreaFactory(sede=self.sede)
        self.otra = CorridaProduccionFactory(sede=self.sede, area=otra_area, fecha_jornada=date(2026, 10, 1))

    def test_listado_dado_cada_filtro_cuando_consulta_entonces_solo_devuelve_la_corrida_que_coincide(self):
        filtros = {
            "estado": "pausada",
            "modalidad": "STOCK",
            "area": self.area.id,
            "maquina": self.maquina.id,
            "linea": self.linea.id,
            "turno": " noche ",
            "fecha": "2026-10-27",
        }
        for nombre, valor in filtros.items():
            with self.subTest(filtro=nombre):
                resp = self.client.get(CORRIDAS, {nombre: valor})
                self.assertEqual(resp.status_code, status.HTTP_200_OK)
                self.assertEqual(_ids(resp), {self.objetivo.id})

    def test_listado_dado_filtro_numerico_invalido_cuando_consulta_entonces_400(self):
        self.assertEqual(self.client.get(CORRIDAS, {"area": "abc"}).status_code, status.HTTP_400_BAD_REQUEST)


class IniciarCorridaAlcanceTest(_BaseMes):
    URL = f"{CORRIDAS}iniciar-corrida/"

    def test_iniciar_dado_admin_sin_sede_cuando_inicia_entonces_toma_la_sede_del_area(self):
        admin = CustomUserFactory(sede=None, groups=["admin_sistemas"])
        self.client.force_authenticate(user=admin)

        resp = self.client.post(self.URL, {"area_id": self.area.id}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["sede"], self.sede.id)

    def test_iniciar_dado_jefe_que_pide_otra_sede_cuando_inicia_entonces_403(self):
        resp = self.client.post(self.URL, {"area_id": self.area.id, "sede_id": SedeFactory().id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_iniciar_dado_vinculos_de_su_sede_cuando_inicia_entonces_los_guarda_con_el_codigo_pedido(self):
        linea = LineaProduccionFactory(area=self.area)
        plan = PlanProduccionFactory(sede=self.sede)
        detalle = DetallePlanProduccionFactory(plan=plan)
        pedido = PedidoVentaFactory(sede=self.sede)
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)

        resp = self.client.post(
            self.URL,
            {
                "area_id": self.area.id,
                "codigo": "CORR-PROPIA",
                "linea_id": linea.id,
                "maquina_principal_id": self.maquina.id,
                "orden_produccion_id": op.id,
                "plan_produccion_id": plan.id,
                "detalle_plan_id": detalle.id,
                "pedido_venta_id": pedido.id,
            },
            format="json",
        )

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["codigo"], "CORR-PROPIA")
        for campo, esperado in (
            ("linea", linea.id),
            ("maquina_principal", self.maquina.id),
            ("orden_produccion", op.id),
            ("plan_produccion", plan.id),
            ("detalle_plan", detalle.id),
            ("pedido_venta", pedido.id),
        ):
            with self.subTest(campo=campo):
                self.assertEqual(resp.data[campo], esperado)

    def test_iniciar_dado_op_con_plan_y_pedido_cuando_no_los_envia_entonces_los_hereda_de_la_op(self):
        plan = PlanProduccionFactory(sede=self.sede)
        detalle = DetallePlanProduccionFactory(plan=plan)
        pedido = PedidoVentaFactory(sede=self.sede)
        op = OrdenProduccionFactory(
            sede=self.sede, area=self.area, plan_produccion=plan, detalle_plan=detalle, pedido_venta=pedido
        )

        resp = self.client.post(self.URL, {"area_id": self.area.id, "orden_produccion_id": op.id}, format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(
            (resp.data["plan_produccion"], resp.data["detalle_plan"], resp.data["pedido_venta"]),
            (plan.id, detalle.id, pedido.id),
        )

    def test_iniciar_dado_maquina_de_otra_sede_cuando_inicia_entonces_404(self):
        ajena = MaquinaFactory(area=AreaFactory(sede=SedeFactory()))
        resp = self.client.post(self.URL, {"area_id": self.area.id, "maquina_principal_id": ajena.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)


class OperarioNoCambiaElMaterialTest(_BaseMes):
    """El operario solo registra avance sobre el material que fijó un supervisor."""

    def setUp(self):
        super().setUp()
        self.operario = CustomUserFactory(sede=self.sede, area=self.area, groups=["operario"])
        self.origen = BodegaFactory(sede=self.sede)
        self.destino = BodegaFactory(sede=self.sede)
        self.insumo = ProductoFactory(tipo="colorante", sede=self.sede)
        self.acabado = ProductoFactory(tipo="tela", sede=self.sede)
        self.lote = LoteProduccion.objects.create(
            producto=self.insumo,
            codigo_lote="LOT-INSUMO-MES",
            peso_neto_producido=Decimal("500.000"),
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )
        StockBodegaFactory(bodega=self.origen, producto=self.insumo, lote=self.lote, cantidad=Decimal("500.000"))
        self.corrida = CorridaProduccionFactory(sede=self.sede, area=self.area, maquina_principal=self.maquina)
        self.url = f"{CORRIDAS}{self.corrida.id}/registrar-operacion/"

    def _payload(self, salida_producto, codigo):
        return {
            "maquina_id": self.maquina.id,
            "consumos": [
                {
                    "producto_id": self.insumo.id,
                    "bodega_origen_id": self.origen.id,
                    "lote_origen_id": self.lote.id,
                    "cantidad_consumida": "100.000",
                }
            ],
            "salidas": [
                {
                    "producto_id": salida_producto.id,
                    "bodega_destino_id": self.destino.id,
                    "cantidad_neta": "100.000",
                    "codigo_lote": codigo,
                }
            ],
        }

    def test_registrar_dado_operario_sin_operacion_previa_cuando_registra_entonces_403(self):
        self.client.force_authenticate(user=self.operario)
        resp = self.client.post(self.url, self._payload(self.acabado, "LOT-OP-1"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("supervisor debe registrar la primera", resp.data["error"])

    def test_registrar_dado_operario_que_cambia_el_producto_cuando_registra_entonces_403(self):
        primera = self.client.post(self.url, self._payload(self.acabado, "LOT-SUP-1"), format="json")
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED, primera.data)
        self.client.force_authenticate(user=self.operario)

        resp = self.client.post(self.url, self._payload(ProductoFactory(sede=self.sede), "LOT-OP-2"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("no puede cambiar el producto", resp.data["error"])

    def test_registrar_dado_operario_con_el_mismo_material_cuando_registra_entonces_201(self):
        primera = self.client.post(self.url, self._payload(self.acabado, "LOT-SUP-2"), format="json")
        self.assertEqual(primera.status_code, status.HTTP_201_CREATED, primera.data)
        self.client.force_authenticate(user=self.operario)

        resp = self.client.post(self.url, self._payload(self.acabado, "LOT-OP-3"), format="json")

        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

    def test_registrar_dado_error_inesperado_del_motor_cuando_registra_entonces_500_generico(self):
        with patch(
            "gestion.views.mes_views.EjecucionProduccionService.registrar_operacion", side_effect=RuntimeError("x")
        ):
            resp = self.client.post(self.url, self._payload(self.acabado, "LOT-SUP-3"), format="json")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(resp.data["error"], "Error interno en el motor de ejecución.")


class CorridaEstadosYErroresTest(_BaseMes):
    def setUp(self):
        super().setUp()
        self.corrida = CorridaProduccionFactory(sede=self.sede, area=self.area, estado="finalizada")

    def test_finalizar_dado_corrida_ya_finalizada_cuando_finaliza_entonces_400(self):
        resp = self.client.post(f"{CORRIDAS}{self.corrida.id}/finalizar-corrida/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_pausar_dado_corrida_finalizada_cuando_pausa_entonces_400_sin_cambiar_estado(self):
        resp = self.client.post(f"{CORRIDAS}{self.corrida.id}/pausar/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.corrida.refresh_from_db()
        self.assertEqual(self.corrida.estado, "finalizada")

    def test_revertir_dado_error_inesperado_del_servicio_cuando_revierte_entonces_500_generico(self):
        operacion = OperacionProduccionFactory(corrida=self.corrida)
        with patch(
            "gestion.views.mes_views.EjecucionProduccionService.revertir_operacion", side_effect=RuntimeError("x")
        ):
            resp = self.client.post(
                f"{CORRIDAS}{self.corrida.id}/revertir-operacion/",
                {"operacion_id": operacion.id, "justificacion": "Pesaje mal cargado"},
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(resp.data["error"], "Error interno al procesar la reversión.")


class TrazabilidadLoteTest(_BaseMes):
    URL = f"{CORRIDAS}trazabilidad-lote/"

    def setUp(self):
        super().setUp()
        self.lote = LoteProduccion.objects.create(
            orden_produccion=OrdenProduccionFactory(sede=self.sede, area=self.area),
            codigo_lote="LOT-TRAZ-MES",
            peso_neto_producido=Decimal("10.000"),
            turno="Mañana",
            hora_inicio=timezone.now(),
            hora_final=timezone.now(),
        )

    def test_trazabilidad_dado_sin_codigo_ni_id_cuando_consulta_entonces_400(self):
        self.assertEqual(self.client.get(self.URL).status_code, status.HTTP_400_BAD_REQUEST)

    def test_trazabilidad_dado_lote_inexistente_cuando_consulta_entonces_404(self):
        self.assertEqual(self.client.get(self.URL, {"codigo": "NO-EXISTE"}).status_code, status.HTTP_404_NOT_FOUND)

    def test_trazabilidad_dado_direccion_adelante_cuando_consulta_entonces_usa_el_recorrido_hacia_adelante(self):
        with patch(
            "gestion.views.mes_views.GenealogiaService.obtener_trazabilidad_hacia_adelante", return_value={"nodos": []}
        ) as adelante:
            resp = self.client.get(self.URL, {"lote_id": self.lote.id, "direccion": "Adelante", "profundidad": 3})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        adelante.assert_called_once_with(lote_ref=self.lote.id, profundidad_maxima=3)

    def test_trazabilidad_dado_error_de_validacion_cuando_consulta_entonces_400_con_el_mensaje(self):
        from django.core.exceptions import ValidationError

        with patch(
            "gestion.views.mes_views.GenealogiaService.obtener_trazabilidad_hacia_atras",
            side_effect=ValidationError("Profundidad fuera de rango."),
        ):
            resp = self.client.get(self.URL, {"codigo": "LOT-TRAZ-MES"})
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(resp.data["error"], ["Profundidad fuera de rango."])

    def test_trazabilidad_dado_error_inesperado_cuando_consulta_entonces_500_generico(self):
        with patch(
            "gestion.views.mes_views.GenealogiaService.obtener_trazabilidad_hacia_atras", side_effect=RuntimeError("x")
        ):
            resp = self.client.get(self.URL, {"codigo": "LOT-TRAZ-MES"})
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class OperacionesListadoTest(_BaseMes):
    def test_listado_dado_filtro_por_corrida_y_estado_cuando_consulta_entonces_solo_esas_operaciones(self):
        corrida = CorridaProduccionFactory(sede=self.sede, area=self.area)
        objetivo = OperacionProduccionFactory(corrida=corrida, estado="revertida")
        OperacionProduccionFactory(corrida=corrida, estado="completada")
        # Mismo estado en otra corrida: solo el filtro por corrida la deja fuera.
        OperacionProduccionFactory(corrida=CorridaProduccionFactory(sede=self.sede, area=self.area), estado="revertida")

        resp = self.client.get(OPERACIONES, {"corrida": corrida.id, "estado": "revertida"})

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(_ids(resp), {objetivo.id})


class PlanesEstadosYAlcanceTest(_BaseMes):
    def test_listado_dado_filtro_por_sede_y_estado_cuando_consulta_entonces_solo_ese_plan(self):
        objetivo = PlanProduccionFactory(sede=self.sede, estado="aprobado")
        PlanProduccionFactory(sede=self.sede, estado="borrador")
        resp = self.client.get(PLANES, {"sede": self.sede.id, "estado": "aprobado"})
        self.assertEqual(_ids(resp), {objetivo.id})

    def test_aprobar_dado_plan_que_no_es_borrador_cuando_aprueba_entonces_400(self):
        plan = PlanProduccionFactory(sede=self.sede, estado="aprobado")
        self.assertEqual(self.client.post(f"{PLANES}{plan.id}/aprobar/").status_code, status.HTTP_400_BAD_REQUEST)

    def test_cerrar_dado_plan_aprobado_cuando_cierra_entonces_queda_cerrado(self):
        plan = PlanProduccionFactory(sede=self.sede, estado="aprobado")
        resp = self.client.post(f"{PLANES}{plan.id}/cerrar/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["estado"], "cerrado")

    def test_cerrar_dado_plan_ya_cerrado_o_cancelado_cuando_cierra_entonces_400(self):
        for estado in ("cerrado", "cancelado"):
            with self.subTest(estado=estado):
                plan = PlanProduccionFactory(sede=self.sede, estado=estado)
                self.assertEqual(
                    self.client.post(f"{PLANES}{plan.id}/cerrar/").status_code, status.HTTP_400_BAD_REQUEST
                )

    def test_necesidades_dado_admin_con_sede_cuando_consulta_entonces_analiza_esa_sede(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=["admin_sistemas"]))
        with patch(
            "gestion.views.mes_views.ReposicionService.analizar_necesidades_reposicion", return_value=[]
        ) as analizar:
            resp = self.client.get(f"{PLANES}necesidades-reposicion/", {"sede": self.sede.id})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        analizar.assert_called_once_with(sede_id=self.sede.id)

    def test_necesidades_dado_jefe_sin_sede_cuando_consulta_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=["jefe_planta"]))
        resp = self.client.get(f"{PLANES}necesidades-reposicion/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)


class CrearPlanDesdeAlertasAlcanceTest(_BaseMes):
    URL = f"{PLANES}crear-desde-alertas/"

    def _items(self):
        return [{"producto_id": ProductoFactory(sede=self.sede).id, "deficit": "10.000"}]

    def test_crear_dado_admin_sin_sede_id_cuando_crea_entonces_400(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=["admin_sistemas"]))
        resp = self.client.post(self.URL, {"items": self._items()}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("sede_id", resp.data["error"]["fields"])

    def test_crear_dado_jefe_sin_sede_cuando_crea_entonces_403(self):
        self.client.force_authenticate(user=CustomUserFactory(sede=None, groups=["jefe_planta"]))
        resp = self.client.post(self.URL, {"items": self._items()}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_crear_dado_jefe_que_pide_otra_sede_cuando_crea_entonces_403(self):
        resp = self.client.post(self.URL, {"items": self._items(), "sede_id": SedeFactory().id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_crear_dado_supervisor_de_otra_sede_cuando_crea_entonces_404(self):
        ajeno = CustomUserFactory(sede=SedeFactory(), groups=["jefe_planta"])
        resp = self.client.post(self.URL, {"items": self._items(), "supervisor_id": ajeno.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_crear_dado_error_inesperado_del_servicio_cuando_crea_entonces_500_generico(self):
        with patch("gestion.views.mes_views.ReposicionService.crear_plan_desde_alertas", side_effect=RuntimeError):
            resp = self.client.post(self.URL, {"items": self._items()}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)


class GenerarOrdenDesdePlanTest(_BaseMes):
    def setUp(self):
        super().setUp()
        self.plan = PlanProduccionFactory(sede=self.sede, estado="aprobado")
        self.detalle = DetallePlanProduccionFactory(plan=self.plan)
        self.url = f"{PLANES}{self.plan.id}/generar-orden/"

    def test_generar_dado_bodegas_y_maquina_de_la_sede_cuando_genera_entonces_las_pasa_al_servicio(self):
        salida, entrada = BodegaFactory(sede=self.sede), BodegaFactory(sede=self.sede)
        op = OrdenProduccionFactory(sede=self.sede, area=self.area)
        with patch("gestion.views.mes_views.ReposicionService.generar_orden_desde_plan", return_value=op) as generar:
            resp = self.client.post(
                self.url,
                {
                    "detalle_plan_id": self.detalle.id,
                    "bodega_salida_id": salida.id,
                    "bodega_entrada_id": entrada.id,
                    "maquina_asignada_id": self.maquina.id,
                },
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        kwargs = generar.call_args.kwargs
        self.assertEqual(
            (kwargs["bodega_salida"], kwargs["bodega_entrada"], kwargs["maquina_asignada"]),
            (salida, entrada, self.maquina),
        )

    def test_generar_dado_bodega_de_otra_sede_cuando_genera_entonces_404(self):
        ajena = BodegaFactory(sede=SedeFactory())
        resp = self.client.post(
            self.url, {"detalle_plan_id": self.detalle.id, "bodega_entrada_id": ajena.id}, format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_generar_dado_detalle_de_otro_plan_cuando_genera_entonces_404_con_el_motivo(self):
        otro = DetallePlanProduccionFactory(plan=PlanProduccionFactory(sede=self.sede))
        resp = self.client.post(self.url, {"detalle_plan_id": otro.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("no pertenece al plan", resp.data["error"])

    def test_generar_dado_error_inesperado_del_servicio_cuando_genera_entonces_500_generico(self):
        with patch("gestion.views.mes_views.ReposicionService.generar_orden_desde_plan", side_effect=RuntimeError):
            resp = self.client.post(self.url, {"detalle_plan_id": self.detalle.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
