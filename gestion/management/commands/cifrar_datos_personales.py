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
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction

from gestion.crypto import ErrorDeCifrado, cifrar, descifrar, indice_ciego
from gestion.models import Cliente, CustomUser


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


CAMPOS = [
    _Campo(Cliente, "ruc_cedula", "ruc_cedula_hash"),
    _Campo(CustomUser, "date_of_birth"),
]


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

    def _leer(self, campo):
        columnas = [campo.pk_columna, campo.columna]
        if campo.columna_indice:
            columnas.append(campo.columna_indice)
        sql = f"SELECT {', '.join(columnas)} FROM {campo.tabla}"  # noqa: S608 — identificadores de _meta, no de entrada
        with connection.cursor() as cursor:
            cursor.execute(sql)
            yield from cursor.fetchall()

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

    def _procesar(self, campo, *, reparar, recalcular):
        en_claro = 0
        indices_malos = 0
        ilegibles = 0
        corregidos = 0

        with transaction.atomic():
            for fila in self._leer(campo):
                pk, guardado = fila[0], fila[1]
                indice_guardado = fila[2] if campo.columna_indice else None

                if guardado in (None, ""):
                    continue

                try:
                    claro = descifrar(guardado)
                    estaba_cifrado = True
                except ErrorDeCifrado:
                    # Puede ser texto en claro (reparable) o un token de una clave que
                    # ya no está en FIELD_ENCRYPTION_KEYS (no reparable: falta la clave).
                    claro = str(guardado)
                    estaba_cifrado = False
                    if self._parece_token_fernet(claro):
                        ilegibles += 1
                        self.stderr.write(
                            self.style.ERROR(
                                f"  {campo.etiqueta} pk={pk}: parece cifrado pero ninguna clave activa "
                                f"lo descifra. Falta una clave en FIELD_ENCRYPTION_KEYS."
                            )
                        )
                        continue
                    en_claro += 1

                indice_esperado = indice_ciego(claro) if campo.columna_indice else None
                indice_desfasado = campo.columna_indice and indice_guardado != indice_esperado
                if indice_desfasado and estaba_cifrado:
                    indices_malos += 1

                hay_que_escribir = (reparar and (not estaba_cifrado or indice_desfasado)) or (
                    recalcular and indice_desfasado
                )
                if hay_que_escribir:
                    # Si ya estaba cifrado se reescribe con la clave activa, que es lo
                    # que se quiere tras una rotación.
                    self._escribir(campo, pk, cifrar(claro), indice_esperado)
                    corregidos += 1

        self.stdout.write(
            f"{campo.etiqueta}: {en_claro} en claro, {indices_malos} con índice desfasado, "
            f"{ilegibles} ilegibles, {corregidos} corregidos."
        )
        return corregidos if (reparar or recalcular) else en_claro + indices_malos + ilegibles

    @staticmethod
    def _parece_token_fernet(valor: str) -> bool:
        """Los tokens Fernet empiezan por 'gAAAAA' (versión 0x80 en base64 urlsafe)."""
        return valor.startswith("gAAAAA")
