"""
Despliegue en producción (§5.3 de la tesis): los scripts y el ejemplo de `.env.prod`
deben coincidir con `infrastructure/docker/docker-compose.prod.yml`.

Hasta el 13-oct-2026 los scripts usaban servicios que el compose de producción no
tiene (`redis`, `web`, `scanning_service`, `printing_service`) y esperaban a SQL Server
con un `DB_PASSWORD` que nunca cargaban: un despliegue nuevo fallaba en el paso 2. Al
ejemplo de `.env.prod` le faltaban variables obligatorias del compose.

El CD (`.github/workflows/cd.yml`) reescribía el `.env` del servidor solo con 9 variables:
faltaban los secretos de scanning y reporting, `TRAZABILIDAD_BASE_URL` y `MSSQL_PID`
(producción quedaba con la edición Developer). Además respaldaba `backend:latest` y
`nginx:latest`, etiquetas que no existen porque el compose usa `TAG=<SHA>`, así que el
rollback a `:backup` siempre fallaba.

Había además una segunda vía de producción (`scripts/deploy/deploy_prod.*`, con otro
`.env` y otro nombre de proyecto) y una variante de contenedores Windows que solo levantaba
`db` y `backend`; se eliminaron para que exista un único camino de despliegue.

Contenedores endurecidos (Fase 5 del plan de CI/CD): imágenes base fijadas por digest,
Python 3.12 en todos los servicios, satélites sin usuario root y sin el driver ODBC de
SQL Server, que dejaron de usar al perder el acceso a la base.

Migraciones fuera del arranque en producción (Fase 4.2, A-7): el backend de producción
no migra al iniciar; el despliegue respalda la base, aplica `preparar_bd.sh` con la imagen
nueva y recién entonces levanta los servicios. Un rollback de imagen ya no encuentra un
esquema migrado a medias. Desarrollo sigue migrando al arrancar.

Release en `master` (Fases 3 y 4): `release.yml` reemplaza a `cd.yml`. Corre el CI completo,
construye las 6 imágenes desde cero, las escanea, atestigua y firma, las prueba en un
staging efímero con pruebas de humo y, con aprobación, las despliega por digest desde el
runner propio del servidor (sin SSH). El rollback usa el mismo runner.

Las pruebas leen los archivos; el despliegue real se verifica con el stack en el equipo
con Docker.

Técnicas ISTQB aplicadas:
- Partición de equivalencia (EP): servicio del compose / inexistente; variable
  obligatoria / opcional / sin uso.
"""
import os
import re
import stat
import subprocess
import tempfile
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase

BASE = Path(settings.BASE_DIR)
COMPOSE_PROD = BASE / "infrastructure" / "docker" / "docker-compose.prod.yml"
ENV_EJEMPLO = BASE / ".env.prod.example"
SCRIPT_SH = BASE / "scripts" / "deploy_production.sh"
SCRIPT_PS1 = BASE / "scripts" / "deploy_production.ps1"
SCRIPTS = BASE / "scripts"
COMPOSE_DEV = BASE / "infrastructure" / "docker" / "docker-compose.yml"
ENTRYPOINT = BASE / "infrastructure" / "docker" / "entrypoint.sh"
PREPARAR_BD = BASE / "infrastructure" / "docker" / "preparar_bd.sh"
RESPALDAR_BD = BASE / "scripts" / "respaldar_bd.sh"
WORKFLOW_CI = BASE / ".github" / "workflows" / "ci.yml"
DEPENDABOT = BASE / ".github" / "dependabot.yml"
# Dockerfiles de las imágenes que se despliegan (las 6 del compose de producción).
DOCKERFILES_PRODUCCION = {
    "backend": BASE / "infrastructure" / "docker" / "Dockerfile.prod",
    "nginx": BASE / "nginx" / "Dockerfile",
    "db": BASE / "database" / "Dockerfile",
    "printing": BASE / "printing_service" / "Dockerfile",
    "scanning": BASE / "scanning_service" / "Dockerfile",
    "reporting_excel": BASE / "reporting_excel" / "Dockerfile",
}
SATELITES = ("printing", "scanning", "reporting_excel")
WORKFLOWS = BASE / ".github" / "workflows"
WORKFLOW_RELEASE = WORKFLOWS / "release.yml"
DESPLEGAR_RELEASE = BASE / "scripts" / "desplegar_release.sh"
STAGING_EFIMERO = BASE / "scripts" / "staging_efimero.sh"
WORKFLOW_ROLLBACK = BASE / ".github" / "workflows" / "rollback.yml"

# `docker compose ... <subcomando> [opciones] servicio...`
_COMANDO = re.compile(r"docker compose\b(?P<resto>[^\n]*)")
_SUBCOMANDOS_CON_SERVICIOS = ("up", "exec", "run", "build", "logs", "restart", "stop", "ps")


def _servicios_del_compose():
    return set(yaml.safe_load(COMPOSE_PROD.read_text(encoding="utf-8"))["services"])


def _servicios_usados(script: Path) -> set[str]:
    """Servicios que el script nombra en sus `docker compose` (sin opciones ni el comando
    que se ejecuta dentro del contenedor)."""
    usados = set()
    for linea in _COMANDO.finditer(script.read_text(encoding="utf-8")):
        tokens = linea.group("resto").split()
        for i, token in enumerate(tokens):
            if token in _SUBCOMANDOS_CON_SERVICIOS:
                argumentos = [t for t in tokens[i + 1:] if not t.startswith(("-", "$", "*", ">"))]
                if token in ("exec", "run"):
                    argumentos = argumentos[:1]  # lo que sigue es el comando dentro del contenedor
                usados.update(a for a in argumentos if re.fullmatch(r"[a-z_]+", a))
                break
    return usados


def _variables_del_compose():
    texto = COMPOSE_PROD.read_text(encoding="utf-8")
    obligatorias = set(re.findall(r"\$\{(\w+)\}", texto))
    opcionales = set(re.findall(r"\$\{(\w+):-", texto))
    return obligatorias, opcionales


def _imagenes_del_compose():
    """{servicio: nombre de imagen}, de `image: ${CI_REGISTRY_IMAGE}/<nombre>:${TAG}`."""
    servicios = yaml.safe_load(COMPOSE_PROD.read_text(encoding="utf-8"))["services"]
    return {
        nombre: re.fullmatch(r"\$\{CI_REGISTRY_IMAGE\}/(\w+):\$\{TAG\}", cfg["image"]).group(1)
        for nombre, cfg in servicios.items() if "image" in cfg
    }


def _script_remoto(workflow: Path) -> str:
    """El `script:` que el workflow ejecuta por SSH en el servidor."""
    trabajos = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
    return "\n".join(
        paso["with"]["script"]
        for trabajo in trabajos.values() for paso in trabajo.get("steps", [])
        if "ssh-action" in paso.get("uses", "")
    )


def _variables_del_ejemplo():
    return set(re.findall(r"^(\w+)=", ENV_EJEMPLO.read_text(encoding="utf-8"), re.MULTILINE))


class ScriptsDespliegueTest(SimpleTestCase):
    def test_deploy_sh_dado_compose_de_produccion_cuando_nombra_servicios_entonces_todos_existen(self):
        usados = _servicios_usados(SCRIPT_SH)
        self.assertTrue(usados)
        self.assertLessEqual(usados, _servicios_del_compose())

    def test_deploy_ps1_dado_compose_de_produccion_cuando_nombra_servicios_entonces_todos_existen(self):
        usados = _servicios_usados(SCRIPT_PS1)
        self.assertTrue(usados)
        self.assertLessEqual(usados, _servicios_del_compose())

    def test_scripts_dado_healthchecks_del_compose_cuando_levantan_entonces_esperan_a_que_esten_sanos(self):
        # `up --wait` espera los HEALTHCHECK de cada servicio; no hace falta leer
        # contraseñas en el script para sondear SQL Server.
        for script in (SCRIPT_SH, SCRIPT_PS1):
            with self.subTest(script=script.name):
                texto = script.read_text(encoding="utf-8")
                self.assertRegex(texto, r"docker compose[^\n]*\bup -d --wait\b")
                self.assertNotIn("DB_PASSWORD", texto)

    def test_scripts_dado_siembra_inicial_cuando_corren_entonces_la_hacen_en_el_backend(self):
        for script in (SCRIPT_SH, SCRIPT_PS1):
            with self.subTest(script=script.name):
                self.assertRegex(script.read_text(encoding="utf-8"),
                                 r"exec -T backend python manage\.py seed_production_masters")


class HostInternoBackendTest(SimpleTestCase):
    def test_compose_produccion_dado_satelites_cuando_llaman_a_backend_entonces_su_host_esta_permitido(self):
        # scanning (y el healthcheck de reporting_excel) llaman a http://backend:8000: con
        # `Host: backend` fuera de ALLOWED_HOSTS Django responde 400 y scanning nunca queda
        # sano. El nombre interno no puede depender de que el operador lo escriba en .env.prod.
        hosts = _entorno_backend(COMPOSE_PROD)["ALLOWED_HOSTS"]
        self.assertTrue(hosts.startswith("${ALLOWED_HOSTS}"))  # el primero lo usa el HEALTHCHECK
        self.assertIn("backend", hosts.split(","))


class EjemploEnvProduccionTest(SimpleTestCase):
    def test_ejemplo_dado_compose_de_produccion_cuando_se_copia_entonces_define_todas_las_obligatorias(self):
        obligatorias, _ = _variables_del_compose()
        self.assertEqual(obligatorias - _variables_del_ejemplo(), set())

    def test_ejemplo_dado_compose_de_produccion_cuando_se_lee_entonces_no_define_variables_sin_uso(self):
        obligatorias, opcionales = _variables_del_compose()
        self.assertEqual(_variables_del_ejemplo() - obligatorias - opcionales, set())


def _workflow(ruta: Path) -> dict:
    datos = yaml.safe_load(ruta.read_text(encoding="utf-8"))
    datos["on"] = datos.pop(True, datos.get("on"))  # PyYAML lee la clave `on` como True
    return datos


def _pasos_run(trabajo: dict) -> str:
    return "\n".join(paso.get("run", "") for paso in trabajo.get("steps", []))


class ReleaseTest(SimpleTestCase):
    def test_cd_dado_release_nuevo_cuando_se_busca_entonces_ya_no_existe(self):
        self.assertFalse((WORKFLOWS / "cd.yml").exists())
        self.assertFalse(re.search(r"appleboy/ssh-action", "".join(
            p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))))

    def test_release_dado_merge_a_master_cuando_dispara_entonces_corre_el_ci_completo(self):
        release = _workflow(WORKFLOW_RELEASE)
        self.assertEqual(release["on"], {"push": {"branches": ["master"]}})
        self.assertIn("workflow_call", _workflow(WORKFLOW_CI)["on"])
        self.assertEqual(release["jobs"]["ci"]["uses"], "./.github/workflows/ci.yml")

    def test_release_dado_build_cuando_construye_entonces_lo_hace_desde_cero_para_las_6_imagenes(self):
        texto = WORKFLOW_RELEASE.read_text(encoding="utf-8")
        build = _workflow(WORKFLOW_RELEASE)["jobs"]["build"]
        nombres = {s["name"] for s in build["strategy"]["matrix"]["service"]}
        self.assertEqual(nombres, set(_imagenes_del_compose().values()))
        self.assertRegex(texto, r"no-cache: true")
        self.assertRegex(texto, r"pull: true")

    def test_release_dado_imagenes_publicadas_cuando_las_certifica_entonces_atestigua_y_firma(self):
        texto = WORKFLOW_RELEASE.read_text(encoding="utf-8")
        self.assertIn("actions/attest-build-provenance@", texto)
        self.assertIn("sigstore/cosign-installer@", texto)
        self.assertRegex(texto, r"cosign sign --yes")
        self.assertRegex(texto, r"cosign verify")

    def test_release_dado_staging_efimero_cuando_prueba_entonces_corre_humo_antes_de_aprobar(self):
        trabajos = _workflow(WORKFLOW_RELEASE)["jobs"]
        self.assertIn("scripts/staging_efimero.sh", _pasos_run(trabajos["staging"]))
        self.assertIn("scripts/smoke_test.py", STAGING_EFIMERO.read_text(encoding="utf-8"))
        self.assertIn("staging", trabajos["deploy"]["needs"])

    def test_release_dado_deploy_cuando_corre_entonces_usa_el_runner_propio_con_aprobacion(self):
        deploy = _workflow(WORKFLOW_RELEASE)["jobs"]["deploy"]
        self.assertEqual(deploy["runs-on"], ["self-hosted", "texcore-prod"])
        self.assertEqual(deploy["environment"]["name"], "production")
        self.assertIn("scripts/desplegar_release.sh", _pasos_run(deploy))

    def test_desplegar_release_dado_version_nueva_cuando_corre_entonces_respalda_migra_y_luego_levanta(self):
        texto = DESPLEGAR_RELEASE.read_text(encoding="utf-8")
        respaldo_imagenes = texto.find(":backup")
        respaldo_bd = texto.find("respaldar_bd.sh")
        migracion = texto.find("preparar_bd.sh")
        levantar = re.search(r"\bup -d --wait\b", texto)
        self.assertGreaterEqual(respaldo_imagenes, 0)
        self.assertGreater(respaldo_bd, respaldo_imagenes)
        self.assertGreater(migracion, respaldo_bd)
        self.assertGreater(levantar.start(), migracion)
        self.assertNotRegex(texto, r"(cat|echo)[^\n]*>\s*[^\n]*\.env\.prod")

    def test_desplegar_release_dado_version_en_ejecucion_cuando_respalda_entonces_cubre_las_6_imagenes(self):
        texto = DESPLEGAR_RELEASE.read_text(encoding="utf-8")
        for servicio, imagen in _imagenes_del_compose().items():
            with self.subTest(servicio=servicio):
                self.assertIn(f"{servicio}:{imagen}", texto)

    def test_rollback_dado_runner_propio_cuando_revierte_entonces_no_reescribe_env_y_espera_salud(self):
        rollback = _workflow(WORKFLOWS / "rollback.yml")["jobs"]["execute-rollback"]
        self.assertEqual(rollback["runs-on"], ["self-hosted", "texcore-prod"])
        script = _pasos_run(rollback)
        self.assertNotRegex(script, r"sed -i[^\n]*\.env\b")
        self.assertRegex(script, r"up -d [^\n]*--wait\b")

    def test_workflows_dado_host_de_produccion_cuando_lo_usan_entonces_sale_de_una_sola_variable(self):
        # M-5: el health check usaba secrets.ALLOWED_HOSTS y el environment vars.ALLOWED_HOSTS.
        texto = "".join(p.read_text(encoding="utf-8") for p in WORKFLOWS.glob("*.yml"))
        self.assertNotRegex(texto, r"(secrets|vars)\.ALLOWED_HOSTS")
        self.assertIn("vars.PRODUCCION_HOST", texto)


class UnicoCaminoDespliegueTest(SimpleTestCase):
    @staticmethod
    def _scripts_de_shell():
        return sorted(p for p in SCRIPTS.rglob("*") if p.suffix in (".sh", ".ps1"))

    def test_scripts_dado_compose_de_produccion_cuando_lo_usan_entonces_solo_deploy_production(self):
        usan_produccion = {p.name for p in self._scripts_de_shell()
                           if "docker-compose.prod.yml" in p.read_text(encoding="utf-8")}
        # Despliegue manual: deploy_production.*; release: desplegar_release.sh y su prueba previa
        # staging_efimero.sh; respaldar_bd.sh opera sobre producción pero no despliega.
        self.assertEqual(usan_produccion, {"deploy_production.sh", "deploy_production.ps1", "respaldar_bd.sh",
                                           "desplegar_release.sh", "staging_efimero.sh"})

    def test_scripts_dado_archivos_compose_cuando_los_referencian_entonces_existen(self):
        for script in self._scripts_de_shell():
            for ruta in re.findall(r"(?:[\w.]+/)*docker-compose[\w.-]*\.yml", script.read_text(encoding="utf-8")):
                with self.subTest(script=script.name, compose=ruta):
                    self.assertTrue((BASE / ruta).is_file())

    def test_scripts_de_desarrollo_dado_entorno_local_cuando_levantan_entonces_usan_el_compose_de_desarrollo(self):
        for nombre in ("deploy.sh", "deploy.ps1"):
            with self.subTest(script=nombre):
                self.assertIn("infrastructure/docker/docker-compose.yml",
                              (SCRIPTS / "deploy" / nombre).read_text(encoding="utf-8"))


def _imagenes_base(dockerfile: Path) -> list[str]:
    return re.findall(r"^FROM\s+(\S+)", dockerfile.read_text(encoding="utf-8"), re.MULTILINE)


def _usuario_final(dockerfile: Path) -> str | None:
    """Último USER de la etapa final (None si la etapa final no declara usuario)."""
    etapas = re.split(r"^FROM\s", dockerfile.read_text(encoding="utf-8"), flags=re.MULTILINE)
    usuarios = re.findall(r"^USER\s+(\S+)", etapas[-1], re.MULTILINE)
    return usuarios[-1] if usuarios else None


class ContenedoresEndurecidosTest(SimpleTestCase):
    def test_dockerfiles_dado_imagen_base_cuando_construyen_entonces_la_fijan_por_digest(self):
        for servicio, dockerfile in DOCKERFILES_PRODUCCION.items():
            for imagen in _imagenes_base(dockerfile):
                with self.subTest(servicio=servicio, imagen=imagen):
                    self.assertRegex(imagen, r"@sha256:[0-9a-f]{64}$")

    def test_dockerfiles_dado_servicios_python_cuando_construyen_entonces_usan_python_312(self):
        for servicio, dockerfile in DOCKERFILES_PRODUCCION.items():
            for imagen in _imagenes_base(dockerfile):
                if imagen.startswith("python:"):
                    with self.subTest(servicio=servicio):
                        self.assertTrue(imagen.startswith("python:3.12"), imagen)

    def test_dockerfiles_dado_satelites_y_backend_cuando_corren_entonces_no_son_root(self):
        for servicio in ("backend", *SATELITES):
            with self.subTest(servicio=servicio):
                usuario = _usuario_final(DOCKERFILES_PRODUCCION[servicio])
                self.assertIsNotNone(usuario)
                self.assertNotIn(usuario, ("root", "0"))

    def test_dockerfiles_dado_satelites_sin_acceso_a_bd_cuando_construyen_entonces_no_instalan_odbc(self):
        for servicio in SATELITES:
            with self.subTest(servicio=servicio):
                self.assertNotIn("msodbcsql", DOCKERFILES_PRODUCCION[servicio].read_text(encoding="utf-8"))

    def test_ci_dado_sql_server_de_pruebas_cuando_corre_entonces_usa_una_cu_fija(self):
        imagenes = re.findall(r"image:\s*(mcr\.microsoft\.com/mssql/server\S*)", WORKFLOW_CI.read_text(encoding="utf-8"))
        self.assertTrue(imagenes)
        for imagen in imagenes:
            with self.subTest(imagen=imagen):
                self.assertNotIn("latest", imagen)
                self.assertRegex(imagen, r"@sha256:[0-9a-f]{64}$")

    def test_dependabot_dado_imagenes_fijadas_cuando_revisa_entonces_cubre_cada_dockerfile(self):
        config = yaml.safe_load(DEPENDABOT.read_text(encoding="utf-8"))
        directorios = {d for u in config["updates"] if u["package-ecosystem"] == "docker"
                       for d in u.get("directories", [u.get("directory")])}
        for servicio, dockerfile in DOCKERFILES_PRODUCCION.items():
            with self.subTest(servicio=servicio):
                self.assertIn("/" + str(dockerfile.parent.relative_to(BASE)), directorios)


def _entorno_backend(compose: Path) -> dict:
    entorno = yaml.safe_load(compose.read_text(encoding="utf-8"))["services"]["backend"].get("environment", [])
    if isinstance(entorno, dict):
        return {k: str(v) for k, v in entorno.items()}
    return dict(item.split("=", 1) for item in entorno)


def _ejecutar_entrypoint(migrar):
    """Corre entrypoint.sh con un `python` falso que anota cada llamada en un registro."""
    with tempfile.TemporaryDirectory() as tmp:
        registro = Path(tmp) / "llamadas.log"
        python_falso = Path(tmp) / "python"
        python_falso.write_text(f'#!/bin/sh\necho "$@" >> "{registro}"\n', encoding="utf-8")
        python_falso.chmod(python_falso.stat().st_mode | stat.S_IEXEC)
        entorno = {**os.environ, "PATH": f"{tmp}:{os.environ['PATH']}"}
        entorno.pop("MIGRAR_AL_INICIAR", None)
        if migrar is not None:
            entorno["MIGRAR_AL_INICIAR"] = migrar
        resultado = subprocess.run(["sh", str(ENTRYPOINT), "true"], cwd=BASE, env=entorno,
                                   capture_output=True, text=True, timeout=30)
        llamadas = registro.read_text(encoding="utf-8") if registro.exists() else ""
        return resultado.returncode, llamadas


class MigracionesFueraDelArranqueTest(SimpleTestCase):
    def test_compose_produccion_dado_backend_cuando_arranca_entonces_no_migra(self):
        self.assertEqual(_entorno_backend(COMPOSE_PROD).get("MIGRAR_AL_INICIAR"), "0")

    def test_compose_desarrollo_dado_backend_cuando_arranca_entonces_sigue_migrando(self):
        self.assertNotEqual(_entorno_backend(COMPOSE_DEV).get("MIGRAR_AL_INICIAR"), "0")

    def test_entrypoint_dado_migrar_al_iniciar_0_cuando_arranca_entonces_no_toca_la_bd(self):
        codigo, llamadas = _ejecutar_entrypoint("0")
        self.assertEqual(codigo, 0)
        self.assertEqual(llamadas, "")

    def test_entrypoint_dado_variable_ausente_cuando_arranca_entonces_prepara_la_bd(self):
        codigo, llamadas = _ejecutar_entrypoint(None)
        self.assertEqual(codigo, 0)
        for paso in ("scripts/create_db.py", "manage.py migrate", "manage.py apply_sql_optimizations",
                     "manage.py register_services"):
            with self.subTest(paso=paso):
                self.assertIn(paso, llamadas)

    def test_scripts_dado_despliegue_cuando_corren_entonces_respaldan_migran_y_luego_levantan(self):
        for script in (SCRIPT_SH, SCRIPT_PS1):
            with self.subTest(script=script.name):
                texto = script.read_text(encoding="utf-8")
                respaldo = texto.find("respaldar")
                migracion = texto.find("preparar_bd.sh")
                levantar = re.search(r"docker compose[^\n]*\bup -d --wait\b(?! db)", texto)
                self.assertGreaterEqual(respaldo, 0)
                self.assertGreater(migracion, respaldo)
                self.assertIsNotNone(levantar)
                self.assertGreater(levantar.start(), migracion)

    def test_scripts_dado_volumenes_de_auditoria_previos_cuando_despliegan_entonces_ajustan_su_dueno(self):
        # Antes del 13-oct-2026 printing y reporting_excel corrían como root y sus volúmenes
        # quedaron de root; con el usuario sin privilegios (UID 10001) no podrían escribir.
        for script in (SCRIPT_SH, SCRIPT_PS1):
            texto = script.read_text(encoding="utf-8")
            for servicio in ("printing", "reporting_excel"):
                with self.subTest(script=script.name, servicio=servicio):
                    self.assertRegex(texto, rf"run --rm --no-deps --user 0 --entrypoint chown {servicio} -R 10001:10001 /data")

    def test_respaldo_dado_script_unico_cuando_existe_entonces_omite_la_base_inexistente(self):
        texto = RESPALDAR_BD.read_text(encoding="utf-8")
        self.assertIn("DB_ID", texto)  # primera instalación: no hay base que respaldar
        self.assertIn("BACKUP DATABASE", texto)


class GobiernoTest(SimpleTestCase):
    """Fase 6 del plan de CI/CD: Scorecard, métricas DORA y política de seguridad."""

    def test_gobierno_dado_rama_por_defecto_cuando_corre_semanal_entonces_mide_scorecard_y_dora(self):
        gobierno = _workflow(WORKFLOWS / "gobierno.yml")
        self.assertIn("schedule", gobierno["on"])
        texto = (WORKFLOWS / "gobierno.yml").read_text(encoding="utf-8")
        self.assertRegex(texto, r"ossf/scorecard-action@[0-9a-f]{40}")
        self.assertIn("scripts/metricas_dora.py", texto)

    def test_security_md_dado_politica_cuando_se_lee_entonces_cubre_reporte_rotacion_y_revision(self):
        texto = (BASE / "SECURITY.md").read_text(encoding="utf-8")
        for seccion in ("Reportar una vulnerabilidad", "Rotación de secretos", "Revisión trimestral"):
            with self.subTest(seccion=seccion):
                self.assertIn(seccion, texto)
