
import os
import sys
import time
import pyodbc

# Get database connection details from environment variables
db_host = os.environ.get('DB_HOST')
db_user = os.environ.get('DB_USER')
db_password = os.environ.get('DB_PASSWORD')
db_name = os.environ.get('DB_NAME')
db_driver = os.environ.get('DB_DRIVER')

# Connection string for the master database
master_conn_str = (
    f'DRIVER={{{db_driver}}};'
    f'SERVER={db_host};'
    f'DATABASE=master;'
    f'UID={db_user};'
    f'PWD={db_password};'
    'Encrypt=yes;'
    'TrustServerCertificate=yes;'
)

retries = 5
wait_time = 10

for i in range(retries):
    try:
        print(f"Attempt {i+1}/{retries}: Connecting to the master database...")
        # Connect to the master database to check if our target database exists
        with pyodbc.connect(master_conn_str, autocommit=True) as conn:
            with conn.cursor() as cursor:
                print("Connection successful.")
                # Check if the database already exists
                cursor.execute("SELECT name FROM sys.databases WHERE name = ?", (db_name,))
                if cursor.fetchone():
                    print(f"Database '{db_name}' already exists.")
                else:
                    # If it doesn't exist, create it
                    print(f"Database '{db_name}' does not exist. Creating...")
                    cursor.execute(f"CREATE DATABASE {db_name}")
                    print(f"Database '{db_name}' created successfully.")
                
                # If we get here, everything is done. Exit the loop.
                sys.exit(0)

    except pyodbc.Error as ex:
        sqlstate = ex.args[0]
        print(f"Database connection failed with SQLSTATE {sqlstate}")
        print(ex)
        if i < retries - 1:
            print(f"Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
        else:
            print("Could not connect to the database after several retries. Exiting.")
            sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)
