from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0008_batch'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_batch_view AS
            SELECT id, material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received
            FROM gestion_batch;
            """,
            "DROP VIEW IF EXISTS gestion_batch_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_batch(p_material_id INTEGER, p_code VARCHAR(100), p_initial_quantity DECIMAL(10,2), p_current_quantity DECIMAL(10,2), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_batch(material_id, code, initial_quantity, current_quantity, unit_of_measure, date_received) VALUES (p_material_id, p_code, p_initial_quantity, p_current_quantity, p_unit_of_measure, NOW());
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_batch(p_material_id INTEGER, p_code VARCHAR(100), p_initial_quantity DECIMAL(10,2), p_current_quantity DECIMAL(10,2), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_batch(p_id INTEGER, p_material_id INTEGER, p_code VARCHAR(100), p_initial_quantity DECIMAL(10,2), p_current_quantity DECIMAL(10,2), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_batch SET material_id = p_material_id, code = p_code, initial_quantity = p_initial_quantity, current_quantity = p_current_quantity, unit_of_measure = p_unit_of_measure WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_batch(p_id INTEGER, p_material_id INTEGER, p_code VARCHAR(100), p_initial_quantity DECIMAL(10,2), p_current_quantity DECIMAL(10,2), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_batch(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_batch WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_batch(p_id INTEGER);"
        ),
    ]