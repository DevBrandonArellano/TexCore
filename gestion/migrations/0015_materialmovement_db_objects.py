from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0014_materialmovement'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_materialmovement_view AS
            SELECT id, batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id
            FROM gestion_materialmovement;
            """,
            "DROP VIEW IF EXISTS gestion_materialmovement_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_materialmovement(p_batch_id INTEGER, p_from_sede_id INTEGER, p_from_area_id INTEGER, p_to_sede_id INTEGER, p_to_area_id INTEGER, p_process_step_id INTEGER, p_quantity DECIMAL(10,2), p_movement_type VARCHAR(20), p_responsible_user_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_materialmovement(batch_id, from_sede_id, from_area_id, to_sede_id, to_area_id, process_step_id, quantity, movement_type, timestamp, responsible_user_id) VALUES (p_batch_id, p_from_sede_id, p_from_area_id, p_to_sede_id, p_to_area_id, p_process_step_id, p_quantity, p_movement_type, NOW(), p_responsible_user_id);
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_materialmovement(p_batch_id INTEGER, p_from_sede_id INTEGER, p_from_area_id INTEGER, p_to_sede_id INTEGER, p_to_area_id INTEGER, p_process_step_id INTEGER, p_quantity DECIMAL(10,2), p_movement_type VARCHAR(20), p_responsible_user_id INTEGER);"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_materialmovement(p_id INTEGER, p_batch_id INTEGER, p_from_sede_id INTEGER, p_from_area_id INTEGER, p_to_sede_id INTEGER, p_to_area_id INTEGER, p_process_step_id INTEGER, p_quantity DECIMAL(10,2), p_movement_type VARCHAR(20), p_responsible_user_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_materialmovement SET batch_id = p_batch_id, from_sede_id = p_from_sede_id, from_area_id = p_from_area_id, to_sede_id = p_to_sede_id, to_area_id = p_to_area_id, process_step_id = p_process_step_id, quantity = p_quantity, movement_type = p_movement_type, responsible_user_id = p_responsible_user_id WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_materialmovement(p_id INTEGER, p_batch_id INTEGER, p_from_sede_id INTEGER, p_from_area_id INTEGER, p_to_sede_id INTEGER, p_to_area_id INTEGER, p_process_step_id INTEGER, p_quantity DECIMAL(10,2), p_movement_type VARCHAR(20), p_responsible_user_id INTEGER);"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_materialmovement(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_materialmovement WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_materialmovement(p_id INTEGER);"
        ),
    ]