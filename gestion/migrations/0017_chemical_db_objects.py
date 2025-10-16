from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0016_chemical'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_chemical_view AS
            SELECT id, code, name, description, current_stock, unit_of_measure
            FROM gestion_chemical;
            """,
            "DROP VIEW IF EXISTS gestion_chemical_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_chemical(p_code VARCHAR(50), p_name VARCHAR(100), p_description TEXT, p_current_stock DECIMAL(10,2), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_chemical(code, name, description, current_stock, unit_of_measure) VALUES (p_code, p_name, p_description, p_current_stock, p_unit_of_measure);
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_chemical(p_code VARCHAR(50), p_name VARCHAR(100), p_description TEXT, p_current_stock DECIMAL(10,2), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_chemical(p_id INTEGER, p_code VARCHAR(50), p_name VARCHAR(100), p_description TEXT, p_current_stock DECIMAL(10,2), p_unit_of_measure VARCHAR(50))
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_chemical SET code = p_code, name = p_name, description = p_description, current_stock = p_current_stock, unit_of_measure = p_unit_of_measure WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_chemical(p_id INTEGER, p_code VARCHAR(50), p_name VARCHAR(100), p_description TEXT, p_current_stock DECIMAL(10,2), p_unit_of_measure VARCHAR(50));"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_chemical(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_chemical WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_chemical(p_id INTEGER);"
        ),
    ]