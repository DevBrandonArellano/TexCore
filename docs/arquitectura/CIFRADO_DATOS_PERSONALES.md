# Cifrado de datos personales en reposo (RS-19)

> **Vigencia:** 19-oct-2026. Cierra el riesgo **RS-19** del `REGISTRO_RIESGOS.md`, que
> era el único ❌ del contraste con la tesis (`AUDITORIA_CALIDAD.md` §I.5).
> Migración: `gestion/0010_cifrar_datos_personales`.

## 1. Qué se cifra y por qué

La LOPDP (2021, Ecuador) exige medidas técnicas sobre los datos de identificación, y
la tesis afirma «privacidad desde el diseño». Hasta el 19-oct-2026 el sistema tenía
cifrado en tránsito (TLS 1.2/1.3 con HSTS, `Encrypt=yes` hacia SQL Server), control de
acceso por rol y auditoría inmutable, pero **los datos personales estaban en claro en
la base**. Era el defecto `SEC-08` de la auditoría de abril, diferido y nunca retomado.

| Campo | Modelo | Antes | Ahora |
|---|---|---|---|
| `ruc_cedula` (RUC o cédula) | `gestion.Cliente` | `nvarchar(20)` en claro | `nvarchar(max)` con token Fernet |
| `date_of_birth` (fecha de nacimiento) | `gestion.CustomUser` | `date` en claro | `nvarchar(max)` con token Fernet |

No se cifra el resto (`nombre_razon_social`, `direccion_envio`, correo): son datos de
contacto comercial que el sistema necesita filtrar y ordenar en la base. El alcance se
acotó a los **datos de identificación**, que son los que la LOPDP señala y los que la
tesis nombra.

## 2. Por qué cifrado de aplicación y no TDE

Se evaluaron las tres salidas que el `REGISTRO_RIESGOS.md` dejó abiertas:

| Opción | Decisión |
|---|---|
| (a) Cifrado por campo en la aplicación | **Elegida.** No depende de la edición de SQL Server que licencie la organización y protege el dato incluso ante una copia del archivo de datos o un respaldo filtrado. |
| (b) TDE (cifrado transparente de la base) | Descartada como única medida: depende de la edición licenciada (ver **RS-18**) y no protege frente a quien tenga credenciales de lectura de la base. Sigue siendo complementaria: si la organización licencia una edición con TDE, se puede activar **además** de esto. |
| (c) Corregir solo el texto de la tesis | Descartada por sí sola. Sí se corrigió la redacción, pero para que describa con precisión lo que ahora existe, no para rebajar la afirmación (ver §7). |

## 3. Cómo funciona

### Cifrado

`gestion/crypto.py` envuelve **Fernet** (AES-128-CBC más HMAC-SHA256 de
autenticación, de la biblioteca `cryptography`). `gestion/model_fields.py` expone dos
campos de modelo que cifran al escribir y descifran al leer, así que el resto del
proyecto —serializers, vistas, plantillas de impresión— los usa como el campo normal
del que heredan:

- `EncryptedCharField`: hereda de `CharField`, así que `max_length=20` sigue validando
  el valor **en claro** y DRF lo sigue serializando como texto.
- `EncryptedDateField`: hereda de `DateField`, así que la API sigue recibiendo y
  devolviendo `YYYY-MM-DD` y el admin sigue mostrando un selector de fecha.

Ambos declaran `get_internal_type() == "TextField"`, de modo que la columna es
`nvarchar(max)`: un token Fernet de un texto corto ya ocupa unos 120 caracteres.

### Índice ciego (búsqueda y unicidad)

Fernet usa un IV aleatorio: **el mismo RUC produce un texto cifrado distinto en cada
escritura**. Eso rompe dos cosas que el sistema necesitaba:

1. buscar un cliente por su identificación, y
2. la restricción de unicidad `(ruc_cedula, sede)`.

Ambas pasan ahora por `Cliente.ruc_cedula_hash`, un **índice ciego**: el HMAC-SHA256
del valor normalizado (`strip()`), en hexadecimal, con su propio índice en la base. Es
HMAC y no SHA-256 a secas porque el espacio de cédulas ecuatorianas es pequeño y un
resumen sin clave se rompería por fuerza bruta.

- La unicidad es `unique_together = ("ruc_cedula_hash", "sede")` — misma semántica y
  mismo SQL que antes.
- El índice lo recalcula `BlindIndexField.pre_save()`, el único punto por el que pasan
  **todas** las escrituras de Django, `bulk_create` incluido.

### Lo que ya no se puede hacer

`ruc_cedula` y `date_of_birth` solo admiten el lookup `isnull`. Cualquier otro
(`exact`, `startswith`, `gt`…) lanza `FieldError` con el camino correcto en el mensaje.
Es deliberado: sobre una columna cifrada esos filtros devolverían vacío **en silencio**.

```python
# ✗ FieldError
Cliente.objects.filter(ruc_cedula="1790012345001")

# ✓ por el índice ciego, sobre su índice de la base
Cliente.objects.por_identificacion("1790012345001")

# ✓ equivalente de get_or_create(ruc_cedula=...)
Cliente.objects.obtener_o_crear_por_identificacion("1790012345001", defaults={...})
```

Para filtrar por rango de fechas de nacimiento hay que traer el conjunto acotado por
otro campo y filtrar en Python. Hoy no hay ninguna consulta del sistema que lo haga.

### Auditoría

`AuditLog` es inmutable y **no** está cifrado, así que escribir ahí la fecha de
nacimiento anularía el cifrado del campo. `gestion/signals.py` audita `date_of_birth`
por su HMAC truncado (`hmac:…`): cambia cuando el dato cambia —que es lo que la
auditoría debe demostrar— y no revela la fecha. `Cliente.ruc_cedula` nunca estuvo en
`campos_auditables`, así que no hacía falta tocar nada ahí.

## 4. Claves

| Variable | Rotable | Para qué |
|---|---|---|
| `FIELD_ENCRYPTION_KEYS` | Sí | Lista separada por comas de claves Fernet. **La primera cifra; todas descifran** (`MultiFernet`), lo que permite rotar sin parar el sistema. |
| `BLIND_INDEX_KEY` | No sin reindexar | Clave HMAC del índice ciego. Si cambia, todos los índices guardados dejan de coincidir. |

Las dos son **fail-fast** (`get_env_variable`), igual que `SECRET_KEY`: sin ellas Django
no arranca. Arrancar «a medias» dejaría los datos ya cifrados ilegibles sin avisar.

**Ninguna se deriva de `SECRET_KEY`**: `SECRET_KEY` también firma los JWT y se rota
cada año (`SECURITY.md`); derivar de ella volvería ilegibles todos los datos cifrados
en cada rotación.

Generarlas:

```bash
# FIELD_ENCRYPTION_KEYS
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# BLIND_INDEX_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

> **Si se pierde `FIELD_ENCRYPTION_KEYS`, los datos cifrados no se recuperan.** Guárdala
> en el gestor de secretos **y** junto al respaldo cifrado, no solo en el `.env` del
> servidor.

### Rotar `FIELD_ENCRYPTION_KEYS`

1. Poner la clave nueva **primera** y dejar la vieja detrás:
   `FIELD_ENCRYPTION_KEYS=nueva,vieja`. Desde ese momento se cifra con la nueva y se
   sigue descifrando lo viejo.
2. Reescribir lo ya guardado con la clave nueva:
   `python manage.py cifrar_datos_personales --reparar`.
3. Retirar la clave vieja de la lista.

### Cambiar `BLIND_INDEX_KEY`

Obliga a recalcular todos los índices; mientras no se haga, las búsquedas por
identificación no encuentran nada:

```bash
python manage.py cifrar_datos_personales --recalcular-indices
```

## 5. Puesta en marcha

```bash
# 1. Respaldo (el paso que borra las columnas en claro no se revierte)
bash scripts/respaldar_bd.sh

# 2. Las dos claves en el entorno del backend (.env de producción)

# 3. Migración: cifra los datos existentes y crea el índice ciego
python manage.py migrate gestion

# 4. Verificación (no escribe nada; falla si queda algo en claro)
python manage.py cifrar_datos_personales
```

La migración `0010` recorre las filas en lotes de 500. Estrategia por campo: columna
nueva → copia cifrada → se borra la columna en claro → se renombra la nueva con el
nombre original. Se hace así, y no con un `AlterField` sobre la columna existente,
porque el `ALTER COLUMN` dejaría el texto en claro dentro de la columna nueva y la
conversión de `date` a texto en SQL Server depende del estilo de `CONVERT`.

**La marcha atrás (`migrate gestion 0009`) descifra los datos pero no puede recrear las
columnas que borró**: para volver atrás hay que restaurar el respaldo del paso 1.

## 6. El comando de operación

`python manage.py cifrar_datos_personales`

| Modo | Qué hace |
|---|---|
| (sin argumentos) o `--verificar` | Solo informa. Falla si hay filas en claro, índices desfasados o tokens que ninguna clave activa descifra. |
| `--reparar` | Cifra las filas en claro y corrige los índices que no coincidan. También reescribe con la clave activa, que es lo que se quiere al rotar. |
| `--recalcular-indices` | Recalcula todos los índices ciegos. Obligatorio tras cambiar `BLIND_INDEX_KEY`. |

Lee las columnas con SQL directo a propósito: el ORM descifra al leer y lanzaría
`ErrorDeCifrado` en la primera fila en claro, que es justo la que hay que encontrar.

## 7. Qué queda fuera

- **`dumpdata` exporta los valores en claro**, porque serializa lo que el ORM entrega.
  Un volcado de fixtures con datos reales es un archivo con datos personales: trátese
  como el respaldo de la base.
- **TDE sigue siendo complementario** (ver §2 y **RS-18**). Esto protege los dos campos
  de identificación, no todo el archivo de datos.
- **El cifrado no sustituye al control de acceso.** Quien tiene permiso en la API ve el
  dato descifrado; eso es lo que el RBAC de los 11 roles y el aislamiento por sede
  deciden, y no cambió.

## 8. Pruebas

`gestion/tests/test_cifrado_datos_personales.py` — 34 pruebas, convención ISTQB:

- que la columna **no** contiene el valor en claro (leída con SQL directo, no por el ORM);
- que el ORM lo entrega descifrado y que dos escrituras del mismo valor dan textos distintos;
- búsqueda por índice ciego, y `FieldError` en `exact` y `startswith`;
- unicidad RUC + sede (y que otra sede sí lo acepta), normalización de espacios y `bulk_create`;
- rotación de claves: con la clave vieja en la lista sigue legible; retirada, falla;
- la auditoría de `date_of_birth` sin el valor en claro;
- los tres modos del comando y el contrato de la API (`max_length` y el 400 por duplicado).
