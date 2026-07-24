# Scripts de Test Manual

Scripts de verificación rápida y smoke tests para validar componentes específicos durante el desarrollo. No son parte de la suite de pruebas automatizadas de Django/pytest.

| Script | Propósito |
|--------|-----------|
| `test_regex.py` | Valida el patrón regex de rutas de reporting (`export/`, `vendedores/`, `gerencial/`) |
| `test_url.py` | Verifica que las URLs de reporting resuelven correctamente en Django (`resolve()`) |
| `test_pd.py` | Valida la función de conversión de fechas con pandas (`_fecha_a_texto`) |
| `smoke_test_transfer.py` | Smoke test E2E de transferencia de inventario entre bodegas |
| `print_service_manual_test.py` | Llama al printing_service manualmente para probar generación de PDF/ZPL |

## Uso

Requieren el entorno Django activo (`.env` cargado, BD disponible):

```bash
# Con el backend corriendo
docker exec texcore-backend-1 python scripts/tests/test_url.py

# O directamente si tienes el entorno local
python scripts/tests/smoke_test_transfer.py
```
