"""
Pruebas de los documentos imprimibles de Despacho (HistorialDespachoViewSet):
- imprimir: listado del historial de despachos filtrado por fecha, en PDF.
- guia_remision: Guía de Remisión informativa (NO autorizada por el SRI).

Técnicas ISTQB aplicadas:
- Partición de equivalencia: servicio de impresión disponible / caído.
- Caja negra: validación de campos requeridos de la guía de remisión.
"""

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import Group
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from gestion.models import Bodega, Cliente, CustomUser, LoteProduccion, OrdenProduccion, PedidoVenta, Producto, Sede
from inventory.models import (
    DetalleHistorialDespacho,
    DetalleHistorialDespachoPedido,
    HistorialDespacho,
)


class HistorialDespachosDocumentosTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.sede = Sede.objects.create(nombre="Sede Test Documentos", location="Quito")
        self.usuario = CustomUser.objects.create_user(
            username="despacho_docs",
            password="test123",
            sede=self.sede,
        )
        despacho_group, _ = Group.objects.get_or_create(name="despacho")
        self.usuario.groups.add(despacho_group)
        self.client.force_authenticate(user=self.usuario)

        self.bodega = Bodega.objects.create(nombre="Bodega Test", sede=self.sede)
        self.producto = Producto.objects.create(
            codigo="TELA-DOC",
            descripcion="Tela de prueba",
            tipo="tela",
            stock_minimo=Decimal("0.00"),
            unidad_medida="kg",
        )
        self.cliente = Cliente.objects.create(
            ruc_cedula="1790000000001",
            nombre_razon_social="Cliente Documentos",
            direccion_envio="Av. Prueba 123",
            nivel_precio="normal",
        )
        # Con sede: el historial de despachos se acota a la sede de sus pedidos (OWASP A01).
        self.pedido = PedidoVenta.objects.create(
            cliente=self.cliente,
            guia_remision="GR-DOC-001",
            estado="despachado",
            sede=self.sede,
        )
        orden = OrdenProduccion.objects.create(
            codigo="OP-DOC-001",
            peso_neto_requerido=Decimal("50.00"),
            producto_salida=self.producto,
        )
        self.lote = LoteProduccion.objects.create(
            codigo_lote="LOTE-DOC-001",
            orden_produccion=orden,
            peso_neto_producido=Decimal("50.000"),
            turno="DIURNO",
            hora_inicio=datetime(2026, 8, 20, 8, 0, tzinfo=UTC),
            hora_final=datetime(2026, 8, 20, 9, 0, tzinfo=UTC),
        )
        self.historial = HistorialDespacho.objects.create(
            usuario=self.usuario,
            total_bultos=1,
            total_peso=Decimal("50.000"),
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=self.historial,
            pedido=self.pedido,
            cantidad_despachada=Decimal("50.000"),
        )
        DetalleHistorialDespacho.objects.create(
            historial=self.historial,
            lote=self.lote,
            producto=self.producto,
            peso=Decimal("50.000"),
            pedido=self.pedido,
        )

    # ------------------------------------------------------------------ imprimir

    def test_imprimir_dado_servicio_disponible_cuando_get_entonces_200_pdf(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            resp = self.client.get(reverse("historial-despachos-imprimir"))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "application/pdf")
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(len(data_enviada["despachos"]), 1)
        self.assertEqual(data_enviada["despachos"][0]["id"], self.historial.id)
        self.assertIn("Cliente Documentos", data_enviada["despachos"][0]["pedidos"])

    def test_imprimir_dado_filtro_de_fecha_fuera_de_rango_cuando_get_entonces_lista_vacia(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            resp = self.client.get(
                reverse("historial-despachos-imprimir"),
                {"fecha_desde": "2020-01-01", "fecha_hasta": "2020-01-02"},
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada["despachos"], [])
        self.assertEqual(data_enviada["fecha_desde"], "2020-01-01")

    def test_imprimir_dado_servicio_caido_cuando_get_entonces_503(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=None,
        ):
            resp = self.client.get(reverse("historial-despachos-imprimir"))
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)

    def _crear_despachos_con_pedido(self, cantidad):
        for i in range(cantidad):
            historial = HistorialDespacho.objects.create(
                usuario=self.usuario,
                total_bultos=1,
                total_peso=Decimal("1.000"),
            )
            DetalleHistorialDespachoPedido.objects.create(
                historial=historial,
                pedido=self.pedido,
                cantidad_despachada=Decimal(f"{i + 1}.000"),
            )

    def _ids_impresos(self, **params):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            resp = self.client.get(reverse("historial-despachos-imprimir"), params)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return [d["id"] for d in mock_pdf.call_args[0][0]["despachos"]]

    def _ids_del_listado(self, **params):
        resp = self.client.get(reverse("historial-despachos-list"), params)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        return [fila["id"] for fila in resp.data["results"]]

    def test_imprimir_dado_mas_de_una_pagina_cuando_get_sin_page_entonces_imprime_solo_la_primera(self):
        self._crear_despachos_con_pedido(60)  # 61 en total; la pagina trae 50

        impresos = self._ids_impresos()

        self.assertEqual(len(impresos), 50)
        self.assertEqual(impresos, self._ids_del_listado())

    def test_imprimir_dado_pagina_dos_cuando_get_entonces_imprime_exactamente_las_filas_que_muestra_el_listado(self):
        self._crear_despachos_con_pedido(60)

        impresos = self._ids_impresos(page=2)

        self.assertEqual(len(impresos), 11)
        self.assertEqual(impresos, self._ids_del_listado(page=2))

    def test_imprimir_dado_pagina_y_fechas_cuando_get_entonces_respeta_ambos_como_el_listado(self):
        self._crear_despachos_con_pedido(60)
        filtros = {"fecha_desde": "2020-01-01", "fecha_hasta": "2099-12-31"}

        impresos = self._ids_impresos(page=2, **filtros)

        self.assertEqual(impresos, self._ids_del_listado(page=2, **filtros))

    def _datos_enviados_al_pdf(self, **params):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            self.client.get(reverse("historial-despachos-imprimir"), params)
        return mock_pdf.call_args[0][0]

    def test_imprimir_dado_mas_de_una_pagina_cuando_get_entonces_envia_total_de_registros_y_de_paginas(self):
        self._crear_despachos_con_pedido(120)  # 121 en total => 3 paginas de 50

        datos = self._datos_enviados_al_pdf(page=2)

        self.assertEqual(datos["total_registros"], 121)
        self.assertEqual(datos["pagina"], 2)
        self.assertEqual(datos["total_paginas"], 3)

    def test_imprimir_dado_filtro_de_un_dia_cuando_get_entonces_el_total_cuenta_solo_ese_dia(self):
        self._crear_despachos_con_pedido(60)
        hoy = timezone.localdate().isoformat()

        datos = self._datos_enviados_al_pdf(fecha_desde=hoy, fecha_hasta=hoy)

        self.assertEqual(datos["total_registros"], 61)
        self.assertEqual(datos["total_paginas"], 2)
        self.assertEqual(len(datos["despachos"]), 50)

    def test_imprimir_dado_una_sola_pagina_cuando_get_entonces_total_de_paginas_es_uno(self):
        datos = self._datos_enviados_al_pdf()

        self.assertEqual(datos["total_registros"], 1)
        self.assertEqual(datos["pagina"], 1)
        self.assertEqual(datos["total_paginas"], 1)

    def test_imprimir_dado_pagina_inexistente_cuando_get_entonces_404_como_el_listado(self):
        resp = self.client.get(reverse("historial-despachos-imprimir"), {"page": 99})

        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_imprimir_dado_muchos_despachos_cuando_get_entonces_parametros_sql_acotados_por_la_pagina(self):
        """
        Sin filtro de fechas el historial real supera los ~26 000 despachos. Con
        prefetch_related, cada consulta llevaba un IN con un parametro por
        despacho y superaba el limite de 2100 parametros de SQL Server (500).
        Ahora se imprime solo la pagina visible, asi que los parametros estan
        acotados por el tamano de pagina (50), no por el total.
        """
        self._crear_despachos_con_pedido(120)
        parametros_por_consulta = []

        def _contar_parametros(execute, sql, params, many, context):
            parametros_por_consulta.append(len(params or ()))
            return execute(sql, params, many, context)

        with (
            patch(
                "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
                return_value=b"%PDF-fake",
            ) as mock_pdf,
            connection.execute_wrapper(_contar_parametros),
        ):
            resp = self.client.get(reverse("historial-despachos-imprimir"))

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(mock_pdf.call_args[0][0]["despachos"]), 50)
        self.assertLessEqual(max(parametros_por_consulta), 60)

    def _usuarios_en_pdf(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            self.client.get(reverse("historial-despachos-imprimir"))
        return {d["id"]: d["usuario_nombre"] for d in mock_pdf.call_args[0][0]["despachos"]}

    def _historial_con_pedido(self, usuario):
        historial = HistorialDespacho.objects.create(usuario=usuario, total_bultos=1, total_peso=Decimal("1.000"))
        DetalleHistorialDespachoPedido.objects.create(
            historial=historial,
            pedido=self.pedido,
            cantidad_despachada=Decimal("1.000"),
        )
        return historial

    def test_imprimir_dado_usuario_con_nombre_completo_cuando_get_entonces_usa_el_nombre(self):
        self.usuario.first_name, self.usuario.last_name = "Ana", "Pérez"
        self.usuario.save(update_fields=["first_name", "last_name"])
        self.assertEqual(self._usuarios_en_pdf()[self.historial.id], "Ana Pérez")

    def test_imprimir_dado_usuario_sin_nombre_cuando_get_entonces_usa_el_username(self):
        self.assertEqual(self._usuarios_en_pdf()[self.historial.id], "despacho_docs")

    def test_imprimir_dado_despacho_sin_usuario_cuando_get_entonces_usuario_nombre_es_none(self):
        sin_usuario = self._historial_con_pedido(usuario=None)
        self.assertIsNone(self._usuarios_en_pdf()[sin_usuario.id])

    def test_imprimir_dado_pedido_sin_cliente_cuando_get_entonces_muestra_na(self):
        pedido_sin_cliente = PedidoVenta.objects.create(
            cliente=None,
            guia_remision="GR-SIN-CLI",
            estado="despachado",
            sede=self.sede,
        )
        DetalleHistorialDespachoPedido.objects.create(
            historial=self.historial,
            pedido=pedido_sin_cliente,
            cantidad_despachada=Decimal("1.000"),
        )
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            self.client.get(reverse("historial-despachos-imprimir"))
        pedidos = mock_pdf.call_args[0][0]["despachos"][0]["pedidos"]
        self.assertEqual(pedidos, "Cliente Documentos (GR-DOC-001), N/A (GR-SIN-CLI)")

    def test_imprimir_dado_despacho_a_las_18_23_utc_cuando_arma_el_pdf_entonces_13_23_hora_de_la_planta(self):
        HistorialDespacho.objects.filter(id=self.historial.id).update(
            fecha_despacho=datetime(2026, 10, 27, 18, 23, tzinfo=UTC)
        )
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_historial_despachos_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            self.client.get(reverse("historial-despachos-imprimir"))

        self.assertEqual(mock_pdf.call_args[0][0]["despachos"][0]["fecha_despacho"], "27/10/2026 13:23")

    # -------------------------------------------------------------- guia_remision

    def _payload_guia_valido(self, **overrides):
        payload = {
            "motivo_traslado": "Venta",
            "punto_partida": "Planta Quito, Av. Industrial s/n",
            "fecha_inicio_transporte": "20/08/2026",
            "fecha_fin_transporte": "20/08/2026",
            "transporte_propio": True,
            "placa_vehiculo": "PBX-1234",
        }
        payload.update(overrides)
        return payload

    def test_guia_remision_dado_madrugada_utc_cuando_emite_entonces_fecha_del_dia_en_la_planta(self):
        # 02:00 UTC del 28 son las 21:00 del 27 en la planta: la guía no puede salir con fecha de mañana.
        with (
            patch("gestion.hora_planta.timezone.now", return_value=datetime(2026, 10, 28, 2, 0, tzinfo=UTC)),
            patch(
                "inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf",
                return_value=b"%PDF-fake",
            ) as mock_pdf,
        ):
            self.client.post(
                reverse("historial-despachos-guia-remision", args=[self.historial.id]),
                self._payload_guia_valido(),
                format="json",
            )

        self.assertEqual(mock_pdf.call_args[0][0]["fecha_emision"], "27/10/2026")

    def test_guia_remision_dado_datos_validos_cuando_post_entonces_200_pdf(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            resp = self.client.post(
                reverse("historial-despachos-guia-remision", args=[self.historial.id]),
                self._payload_guia_valido(),
                format="json",
            )

        self.assertEqual(resp.status_code, status.HTTP_200_OK, f"Error: {getattr(resp, 'data', None)}")
        self.assertEqual(resp["Content-Type"], "application/pdf")
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada["numero"], f"001-001-{self.historial.id:09d}")
        self.assertEqual(len(data_enviada["destinatarios"]), 1)
        self.assertEqual(data_enviada["destinatarios"][0]["razon_social"], "Cliente Documentos")
        self.assertEqual(data_enviada["destinatarios"][0]["identificacion"], "1790000000001")
        self.assertEqual(len(data_enviada["detalles"]), 1)
        self.assertEqual(data_enviada["detalles"][0]["cantidad"], 50.0)
        self.assertTrue(data_enviada["transporte_propio"])

    def test_guia_remision_dado_transporte_tercero_sin_transportista_cuando_post_entonces_400(self):
        resp = self.client.post(
            reverse("historial-despachos-guia-remision", args=[self.historial.id]),
            self._payload_guia_valido(transporte_propio=False),
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("transportista_nombre", resp.data)

    def test_guia_remision_dado_transporte_tercero_con_transportista_cuando_post_entonces_200(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf",
            return_value=b"%PDF-fake",
        ) as mock_pdf:
            resp = self.client.post(
                reverse("historial-despachos-guia-remision", args=[self.historial.id]),
                self._payload_guia_valido(
                    transporte_propio=False,
                    transportista_nombre="Transportes Andinos S.A.",
                    transportista_ruc="1790000000099",
                ),
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        data_enviada = mock_pdf.call_args[0][0]
        self.assertEqual(data_enviada["transportista_nombre"], "Transportes Andinos S.A.")

    def test_guia_remision_dado_motivo_faltante_cuando_post_entonces_400(self):
        payload = self._payload_guia_valido()
        del payload["motivo_traslado"]
        resp = self.client.post(
            reverse("historial-despachos-guia-remision", args=[self.historial.id]),
            payload,
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("motivo_traslado", resp.data)

    def test_guia_remision_dado_servicio_caido_cuando_post_entonces_503(self):
        with patch(
            "inventory.views.despacho_views.PrintingService.generate_guia_remision_pdf",
            return_value=None,
        ):
            resp = self.client.post(
                reverse("historial-despachos-guia-remision", args=[self.historial.id]),
                self._payload_guia_valido(),
                format="json",
            )
        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
