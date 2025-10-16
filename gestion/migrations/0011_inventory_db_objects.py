from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0010_inventory'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_inventory_view AS
            SELECT id, material_id, sede_id, area_id, quantity
            FROM gestion_inventory;
            """,
            "DROP VIEW IF EXISTS gestion_inventory_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_inventory(p_material_id INTEGER, p_sede_id INTEGER, p_area_id INTEGER, p_quantity DECIMAL(10,2))
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_inventory(material_id, sede_id, area_id, quantity) VALUES (p_material_id, p_sede_id, p_area_id, p_quantity);
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_inventory(p_material_id INTEGER, p_sede_id INTEGER, p_area_id INTEGER, p_quantity DECIMAL(10,2));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_inventory(p_id INTEGER, p_material_id INTEGER, p_sede_id INTEGER, p_area_id INTEGER, p_quantity DECIMAL(10,2))
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_inventory SET material_id = p_material_id, sede_id = p_sede_id, area_id = p_area_id, quantity = p_quantity WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_inventory(p_id INTEGER, p_material_id INTEGER, p_sede_id INTEGER, p_area_id INTEGER, p_quantity DECIMAL(10,2));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_inventory(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_inventory WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_inventory(p_id INTEGER);"
        ),
    ]