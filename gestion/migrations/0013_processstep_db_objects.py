from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0012_processstep'),
    ]

    operations = [
        migrations.RunSQL(
            """
            CREATE OR REPLACE VIEW gestion_processstep_view AS
            SELECT id, name, description
            FROM gestion_processstep;
            """,
            "DROP VIEW IF EXISTS gestion_processstep_view;"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION create_processstep(p_name VARCHAR(100), p_description TEXT)
            RETURNS VOID AS $$
            BEGIN
                INSERT INTO gestion_processstep(name, description) VALUES (p_name, p_description);
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS create_processstep(p_name VARCHAR(100), p_description TEXT);"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION update_processstep(p_id INTEGER, p_name VARCHAR(100), p_description TEXT)
            RETURNS VOID AS $$
            BEGIN
                UPDATE gestion_processstep SET name = p_name, description = p_description WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS update_processstep(p_id INTEGER, p_name VARCHAR(100), p_description TEXT);"
        ),
        migrations.RunSQL(
            """
            CREATE OR REPLACE FUNCTION delete_processstep(p_id INTEGER)
            RETURNS VOID AS $$
            BEGIN
                DELETE FROM gestion_processstep WHERE id = p_id;
            END;
            $$ LANGUAGE plpgsql;
            """,
            "DROP FUNCTION IF EXISTS delete_processstep(p_id INTEGER);"
        ),
    ]