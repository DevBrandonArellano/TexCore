"""
Verifica, repara y reindexa los datos personales cifrados en reposo (RS-19).

La migración `gestion/0010` ya cifra los datos existentes. Este comando es la
herramienta de operación posterior:

- `--verificar` (lo que hace por omisión, sin escribir nada): comprueba que cada valor
  guardado se descifra con las claves activas y que su índice ciego coincide.
- `--reparar`: cifra las filas que hayan quedado en claro (p. ej. escritas por SQL
  directo o por una restauración parcial de respaldo) y corrige los índices que no
  coincidan.
- `--recalcular-indices`: recalcula todos los índices ciegos. Es el paso obligatorio
  después de cambiar `BLIND_INDEX_KEY`.

Lee las columnas con SQL directo a propósito: el ORM descifra al leer y lanzaría
`ErrorDeCifrado` en la primera fila en claro, que es justo la que hay que encontrar.

Cada hallazgo y cada corrección se registra con el modelo, el campo y la clave primaria
de la fila; nunca con el valor, que es el dato personal que se está protegiendo.
"""

import logging
from dataclasses import dataclass

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from gestion.crypto import ErrorDeCifrado, cifrar, descifrar, indice_ciego
from gestion.models import Cliente, CustomUser

logger = logging.getLogger(__name__)

# Filas por lote y por transacción: acota la memoria y el tiempo que se mantienen los
# bloqueos en tablas grandes. Mismo valor que usa la migración `gestion/0010`.
LOTE = 500

# Los tokens Fernet empiezan por 'gAAAAA' (versión 0x80 en base64 urlsafe).
_PREFIJO_FERNET = "gAAAAA"


class _Campo:
    """Un campo cifrado y, si lo tiene, su columna de índice ciego."""

    def __init__(self, modelo, campo, campo_indice=None):
        self.modelo = modelo
        self.tabla = modelo._meta.db_table
        self.columna = modelo._meta.get_field(campo).column
        self.etiqueta = f"{modelo.__name__}.{campo}"
        self.columna_indice = modelo._meta.get_field(campo_indice).column if campo_indice else None

    @property
    def pk_columna(self):
        return self.modelo._meta.pk.column

    @property
    def columnas(self):
        columnas = [self.pk_columna, self.columna]
        if self.columna_indice:
            columnas.append(self.columna_indice)
        return columnas


CAMPOS = [
    _Campo(Cliente, "ruc_cedula", "ruc_cedula_hash"),
    _Campo(CustomUser, "date_of_birth"),
]


@dataclass
class _Resumen:
    en_claro: int = 0
    indices_malos: int = 0
    ilegibles: int = 0
    corregidos: int = 0

    @property
    def problemas(self):
        return self.en_claro + self.indices_malos + self.ilegibles


@dataclass
class _Diagnostico:
    claro: str
    estaba_cifrado: bool
    indice_esperado: str | None
    indice_desfasado: bool


class Command(BaseCommand):
    help = "Verifica, repara y reindexa el cifrado en reposo de los datos personales (RS-19)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reparar",
            action="store_true",
            help="Cifra las filas que estén en claro y corrige los índices ciegos que no coincidan.",
        )
        parser.add_argument(
            "--recalcular-indices",
            action="store_true",
            help="Recalcula todos los índices ciegos (obligatorio tras cambiar BLIND_INDEX_KEY).",
        )
        parser.add_argument(
            "--verificar",
            action="store_true",
            help="Solo informa, sin escribir. Es el comportamiento por omisión.",
        )

    def handle(self, *args, **opciones):
        reparar = opciones["reparar"]
        recalcular = opciones["recalcular_indices"]
        escribe = reparar or recalcular

        if not escribe:
            self.stdout.write("Modo verificación: no se escribe nada en la base.")

        total_problemas = 0
        for campo in CAMPOS:
            total_problemas += self._procesar(campo, reparar=reparar, recalcular=recalcular)

        if total_problemas and not escribe:
            raise CommandError(
                f"{total_problemas} valor(es) con problemas. Ejecuta de nuevo con --reparar "
                f"(o --recalcular-indices si cambiaste BLIND_INDEX_KEY)."
            )
        if total_problemas:
            self.stdout.write(self.style.SUCCESS(f"Corregidos {total_problemas} valor(es)."))
        else:
            self.stdout.write(self.style.SUCCESS("Todos los datos personales están cifrados y bien indexados."))

    def _procesar(self, campo, *, reparar, recalcular):
        """Recorre el campo por lotes; cada lote es una transacción propia."""
        resumen = _Resumen()
        for lote in self._leer_por_lotes(campo):
            with transaction.atomic():
                for fila in lote:
                    self._tratar_fila(campo, fila, resumen, reparar=reparar, recalcular=recalcular)
        self._informar(campo, resumen)
        return resumen.corregidos if (reparar or recalcular) else resumen.problemas

    def _leer_por_lotes(self, campo):
        """
        Lotes de a `LOTE` filas, paginados por clave primaria.

        Cada lote usa un cursor nuevo y lo cierra antes de devolverlo, así que escribir
        mientras se recorre no choca con un resultado abierto en la misma conexión.
        """
        ultimo = None
        while True:
            condicion = "" if ultimo is None else f" WHERE {campo.pk_columna} > %s"
            columnas = ", ".join(campo.columnas)
            # Los identificadores salen de `_meta`, no de la entrada.
            sql = f"SELECT {columnas} FROM {campo.tabla}{condicion} ORDER BY {campo.pk_columna}"  # noqa: S608
            with connection.cursor() as cursor:
                cursor.execute(sql, [] if ultimo is None else [ultimo])
                lote = cursor.fetchmany(LOTE)
            if not lote:
                return
            yield lote
            if len(lote) < LOTE:
                return
            ultimo = lote[-1][0]

    def _tratar_fila(self, campo, fila, resumen, *, reparar, recalcular):
        pk, guardado = fila[0], fila[1]
        indice_guardado = fila[2] if campo.columna_indice else None
        if guardado in (None, ""):
            return

        diagnostico = self._diagnosticar(campo, guardado, indice_guardado)
        if diagnostico is None:
            resumen.ilegibles += 1
            mensaje = (
                f"{campo.etiqueta} pk={pk}: parece cifrado pero ninguna clave activa lo descifra. "
                f"Falta una clave en FIELD_ENCRYPTION_KEYS."
            )
            logger.error(mensaje)
            self.stderr.write(self.style.ERROR(f"  {mensaje}"))
            return

        if not diagnostico.estaba_cifrado:
            resumen.en_claro += 1
            logger.warning("%s pk=%s: dato personal sin cifrar.", campo.etiqueta, pk)
        elif diagnostico.indice_desfasado:
            resumen.indices_malos += 1
            logger.warning("%s pk=%s: índice ciego desfasado.", campo.etiqueta, pk)

        if self._hay_que_escribir(diagnostico, reparar=reparar, recalcular=recalcular):
            # Si ya estaba cifrado se reescribe con la clave activa, que es lo que se
            # quiere tras una rotación.
            self._escribir(campo, pk, cifrar(diagnostico.claro), diagnostico.indice_esperado)
            resumen.corregidos += 1
            logger.info("%s pk=%s: dato cifrado e indexado con las claves activas.", campo.etiqueta, pk)

    @staticmethod
    def _diagnosticar(campo, guardado, indice_guardado):
        """`None` si el valor parece un token pero ninguna clave activa lo descifra."""
        try:
            claro, estaba_cifrado = descifrar(guardado, registrar=False), True
        except ErrorDeCifrado:
            # Puede ser texto en claro (reparable) o un token de una clave que ya no está
            # en FIELD_ENCRYPTION_KEYS (no reparable: falta la clave).
            claro, estaba_cifrado = str(guardado), False
            if claro.startswith(_PREFIJO_FERNET):
                return None

        indice_esperado = indice_ciego(claro) if campo.columna_indice else None
        indice_desfasado = bool(campo.columna_indice) and indice_guardado != indice_esperado
        return _Diagnostico(claro, estaba_cifrado, indice_esperado, indice_desfasado)

    @staticmethod
    def _hay_que_escribir(diagnostico, *, reparar, recalcular):
        repara = reparar and (not diagnostico.estaba_cifrado or diagnostico.indice_desfasado)
        return repara or (recalcular and diagnostico.indice_desfasado)

    def _escribir(self, campo, pk, valor_cifrado, indice):
        asignaciones = [f"{campo.columna} = %s"]
        parametros = [valor_cifrado]
        if campo.columna_indice:
            asignaciones.append(f"{campo.columna_indice} = %s")
            parametros.append(indice)
        parametros.append(pk)
        asignadas = ", ".join(asignaciones)
        # Los identificadores salen de `_meta`, no de la entrada; los valores van como parámetros.
        sql = f"UPDATE {campo.tabla} SET {asignadas} WHERE {campo.pk_columna} = %s"  # noqa: S608
        with connection.cursor() as cursor:
            cursor.execute(sql, parametros)

    def _informar(self, campo, resumen):
        self.stdout.write(
            f"{campo.etiqueta}: {resumen.en_claro} en claro, {resumen.indices_malos} con índice desfasado, "
            f"{resumen.ilegibles} ilegibles, {resumen.corregidos} corregidos."
        )
