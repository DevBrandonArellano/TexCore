"""
RUP - Migración: Stored Procedures de Reportes de Producción
=============================================================
Artefacto   : Diseño de Base de Datos
Módulo      : Producción / Reportes Excel Ejecutivos
Caso de Uso : CU-EJ-02 Ver Resumen de Producción / CU-EJ-03 Ver Tendencia de Producción

SPs creados:
  1. sp_GetOrdenesProduccionGerencial  — detalle de OPs por rango de fechas y sede
  2. sp_GetLotesProduccionGerencial    — detalle de lotes producidos por rango y sede
  3. sp_GetTendenciaProduccionGerencial — kg producidos por día (serie temporal)

Cada SP acepta @SedeID nullable para soportar vista global (todas las sedes)
o filtrada por sede específica del ejecutivo.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0019_sp_stock_cero_bodega'),
    ]

    operations = [

        # ─────────────────────────────────────────────────────────────────────
        # 1. Órdenes de Producción Gerencial
        #    Retorna el detalle completo de OPs en el rango indicado,
        #    con producto, fórmula de color, área, máquina y operario.
        # ─────────────────────────────────────────────────────────────────────
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetOrdenesProduccionGerencial
                @FechaInicio DATE,
                @FechaFin    DATE,
                @SedeID      INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT
                    op.id                           AS id_orden,
                    op.codigo                       AS codigo_orden,
                    p.codigo                        AS codigo_producto,
                    p.descripcion                   AS producto,
                    fc.nombre_color                 AS formula_color,
                    fc.tipo_sustrato                AS tipo_sustrato,
                    op.peso_neto_requerido          AS peso_requerido_kg,
                    ISNULL(op.peso_producido, 0)    AS peso_producido_kg,
                    CASE
                        WHEN op.peso_neto_requerido > 0
                        THEN CAST(
                                 ROUND(
                                     ISNULL(op.peso_producido, 0) * 100.0
                                     / op.peso_neto_requerido,
                                 2) AS DECIMAL(8,2))
                        ELSE 0
                    END                             AS avance_pct,
                    op.estado                       AS estado,
                    sd.nombre                       AS sede,
                    a.nombre                        AS area,
                    m.nombre                        AS maquina,
                    CONCAT(u.first_name, ' ', u.last_name) AS operario,
                    -- Fecha de inicio: primer lote registrado para esta OP
                    (
                        SELECT MIN(lp2.hora_inicio)
                        FROM   gestion_loteproduccion lp2
                        WHERE  lp2.orden_produccion_id = op.id
                    )                               AS fecha_inicio,
                    -- Fecha de fin: último lote finalizado
                    (
                        SELECT MAX(lp3.hora_final)
                        FROM   gestion_loteproduccion lp3
                        WHERE  lp3.orden_produccion_id = op.id
                          AND  lp3.hora_final IS NOT NULL
                    )                               AS fecha_fin
                FROM  gestion_ordenproduccion op
                INNER JOIN gestion_producto        p   ON p.id  = op.producto_id
                INNER JOIN gestion_sede            sd  ON sd.id = op.sede_id
                LEFT  JOIN gestion_formulacolor    fc  ON fc.id = op.formula_color_id
                LEFT  JOIN gestion_area            a   ON a.id  = op.area_id
                LEFT  JOIN gestion_maquina         m   ON m.id  = op.maquina_asignada_id
                LEFT  JOIN auth_user               u   ON u.id  = op.operario_asignado_id
                WHERE
                    -- Filtro de sede opcional
                    (@SedeID IS NULL OR op.sede_id = @SedeID)
                    -- Filtro de rango: OPs que tienen al menos un lote en el período
                    -- o que fueron creadas en el período (sin lotes aún)
                    AND (
                        EXISTS (
                            SELECT 1
                            FROM   gestion_loteproduccion lp
                            WHERE  lp.orden_produccion_id = op.id
                              AND  CAST(lp.hora_inicio AS DATE) BETWEEN @FechaInicio AND @FechaFin
                        )
                        OR (
                            NOT EXISTS (
                                SELECT 1
                                FROM gestion_loteproduccion lp
                                WHERE lp.orden_produccion_id = op.id
                            )
                        )
                    )
                ORDER BY sd.nombre, op.estado, op.codigo;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetOrdenesProduccionGerencial"
        ),

        # ─────────────────────────────────────────────────────────────────────
        # 2. Lotes de Producción Gerencial
        #    Retorna lotes registrados en el rango con pesos, tiempos y
        #    métricas de productividad por operario/máquina.
        # ─────────────────────────────────────────────────────────────────────
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetLotesProduccionGerencial
                @FechaInicio DATE,
                @FechaFin    DATE,
                @SedeID      INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                SELECT
                    lp.codigo_lote                          AS codigo_lote,
                    op.codigo                               AS orden_produccion,
                    p.codigo                                AS codigo_producto,
                    p.descripcion                           AS producto,
                    sd.nombre                               AS sede,
                    a.nombre                                AS area,
                    m.nombre                                AS maquina,
                    CONCAT(u.first_name, ' ', u.last_name)  AS operario,
                    lp.turno                                AS turno,
                    lp.peso_bruto                           AS peso_bruto_kg,
                    lp.tara                                 AS tara_kg,
                    lp.peso_neto_producido                  AS peso_neto_kg,
                    lp.unidades_empaque                     AS unidades_empaque,
                    lp.presentacion                         AS presentacion,
                    CONVERT(VARCHAR(19), lp.hora_inicio, 120)   AS hora_inicio,
                    CONVERT(VARCHAR(19), lp.hora_final,  120)   AS hora_fin,
                    CASE
                        WHEN lp.hora_final IS NOT NULL AND lp.hora_inicio IS NOT NULL
                        THEN CAST(
                                 ROUND(
                                     DATEDIFF(MINUTE, lp.hora_inicio, lp.hora_final),
                                 0) AS INT)
                        ELSE NULL
                    END                                     AS duracion_minutos,
                    CASE
                        WHEN lp.hora_final IS NOT NULL
                             AND lp.hora_inicio IS NOT NULL
                             AND DATEDIFF(MINUTE, lp.hora_inicio, lp.hora_final) > 0
                        THEN CAST(
                                 ROUND(
                                     lp.peso_neto_producido * 60.0
                                     / DATEDIFF(MINUTE, lp.hora_inicio, lp.hora_final),
                                 2) AS DECIMAL(10,2))
                        ELSE NULL
                    END                                     AS kg_por_hora
                FROM  gestion_loteproduccion        lp
                INNER JOIN gestion_ordenproduccion  op  ON op.id = lp.orden_produccion_id
                INNER JOIN gestion_producto         p   ON p.id  = op.producto_id
                INNER JOIN gestion_sede             sd  ON sd.id = op.sede_id
                LEFT  JOIN gestion_area             a   ON a.id  = op.area_id
                LEFT  JOIN gestion_maquina          m   ON m.id  = lp.maquina_id
                LEFT  JOIN auth_user                u   ON u.id  = lp.operario_id
                WHERE
                    CAST(lp.hora_inicio AS DATE) BETWEEN @FechaInicio AND @FechaFin
                    AND (@SedeID IS NULL OR op.sede_id = @SedeID)
                ORDER BY lp.hora_inicio DESC;
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetLotesProduccionGerencial"
        ),

        # ─────────────────────────────────────────────────────────────────────
        # 3. Tendencia de Producción Gerencial
        #    Serie temporal diaria de kg producidos.
        #    Incluye todos los días del rango (incluso días sin producción = 0)
        #    usando un CTE de calendario para no dejar huecos en el gráfico.
        # ─────────────────────────────────────────────────────────────────────
        migrations.RunSQL(
            sql="""
            CREATE OR ALTER PROCEDURE sp_GetTendenciaProduccionGerencial
                @FechaInicio DATE,
                @FechaFin    DATE,
                @SedeID      INT = NULL
            AS
            BEGIN
                SET NOCOUNT ON;

                -- CTE: calendario continuo entre las fechas solicitadas
                WITH Calendario AS (
                    SELECT @FechaInicio AS fecha
                    UNION ALL
                    SELECT DATEADD(DAY, 1, fecha)
                    FROM   Calendario
                    WHERE  fecha < @FechaFin
                ),
                -- CTE: producción real agrupada por día y sede
                ProduccionDiaria AS (
                    SELECT
                        CAST(lp.hora_inicio AS DATE)    AS fecha,
                        op.sede_id                      AS sede_id,
                        sd.nombre                       AS sede,
                        SUM(lp.peso_neto_producido)     AS kg_producidos
                    FROM  gestion_loteproduccion        lp
                    INNER JOIN gestion_ordenproduccion  op ON op.id = lp.orden_produccion_id
                    INNER JOIN gestion_sede             sd ON sd.id = op.sede_id
                    WHERE
                        CAST(lp.hora_inicio AS DATE) BETWEEN @FechaInicio AND @FechaFin
                        AND (@SedeID IS NULL OR op.sede_id = @SedeID)
                    GROUP BY
                        CAST(lp.hora_inicio AS DATE),
                        op.sede_id,
                        sd.nombre
                )
                SELECT
                    c.fecha                             AS fecha,
                    ISNULL(pd.kg_producidos, 0)         AS kg_producidos,
                    ISNULL(pd.sede, 'Todas')            AS sede
                FROM  Calendario c
                LEFT  JOIN ProduccionDiaria pd ON pd.fecha = c.fecha
                ORDER BY c.fecha
                OPTION (MAXRECURSION 365);   -- Permite hasta 1 año de rango
            END
            """,
            reverse_sql="DROP PROCEDURE IF EXISTS sp_GetTendenciaProduccionGerencial"
        ),
    ]
