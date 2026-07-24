"""
Pruebas de internal_api/audit.py — AuditLogger.log.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): status_code < 400 (INFO) / 4xx (WARNING) /
  >= 500 (ERROR).
- Caja blanca: ramas opcionales duration_ms/extra que enriquecen el SD.
"""
import logging

from django.test import TestCase

from internal_api.audit import AuditLogger


class AuditLoggerTestCase(TestCase):
    def test_log_dado_status_200_cuando_registra_entonces_nivel_info(self):
        with self.assertLogs('internal_api.audit', level='INFO') as cm:
            AuditLogger.log(service='qa-service', action='get_productos', resource='reports', status_code=200)
        self.assertEqual(cm.records[0].levelno, logging.INFO)

    def test_log_dado_status_403_cuando_registra_entonces_nivel_warning(self):
        with self.assertLogs('internal_api.audit', level='WARNING') as cm:
            AuditLogger.log(service='qa-service', action='get_productos', resource='reports', status_code=403)
        self.assertEqual(cm.records[0].levelno, logging.WARNING)

    def test_log_dado_status_500_cuando_registra_entonces_nivel_error(self):
        with self.assertLogs('internal_api.audit', level='ERROR') as cm:
            AuditLogger.log(service='qa-service', action='get_productos', resource='reports', status_code=500)
        self.assertEqual(cm.records[0].levelno, logging.ERROR)

    def test_log_dado_duration_ms_cuando_registra_entonces_lo_incluye_en_sd(self):
        with self.assertLogs('internal_api.audit', level='INFO') as cm:
            AuditLogger.log(
                service='qa-service', action='get_productos', resource='reports',
                status_code=200, duration_ms=42,
            )
        self.assertIn('duration_ms', cm.records[0].sd)
        self.assertEqual(cm.records[0].sd['duration_ms'], 42)

    def test_log_dado_extra_cuando_registra_entonces_lo_mergea_en_sd(self):
        with self.assertLogs('internal_api.audit', level='INFO') as cm:
            AuditLogger.log(
                service='qa-service', action='get_productos', resource='reports',
                status_code=200, extra={'sede_id': 3},
            )
        self.assertEqual(cm.records[0].sd['sede_id'], 3)

    def test_log_dado_sin_duration_ni_extra_cuando_registra_entonces_sd_minimo(self):
        with self.assertLogs('internal_api.audit', level='INFO') as cm:
            AuditLogger.log(service='qa-service', action='get_productos', resource='reports')
        self.assertNotIn('duration_ms', cm.records[0].sd)
