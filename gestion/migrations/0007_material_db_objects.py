from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0006_material'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_material_view AS
            SELECT id, name, unit_of_measure
            FROM gestion_material;
            """,
            "DROP VIEW IF EXISTS gestion_material_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_material(p_name VARCHAR(100), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_material(name, unit_of_measure) VALUES (p_name, p_unit_of_measure);
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_material(p_name VARCHAR(100), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_material(p_id INTEGER, p_name VARCHAR(100), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_material SET name = p_name, unit_of_measure = p_unit_of_measure WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_material(p_id INTEGER, p_name VARCHAR(100), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_material(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_material WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_material(p_id INTEGER);"
        ),
    ]