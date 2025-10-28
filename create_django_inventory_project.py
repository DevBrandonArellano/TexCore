
import os
import subprocess
import sys

def run_command(command, cwd=None):
    print(f"Running command: {' '.join(command)}")
    try:
        result = subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        sys.exit(1)

def create_django_inventory_project(parent_dir, project_name="TexcoreInventarios"):
    project_path = os.path.join(parent_dir, project_name)
    
    if os.path.exists(project_path):
        print(f"Directory '{project_path}' already exists. Please remove it or choose a different name.")
        sys.exit(1)

    print(f"Creating project directory: {project_path}")
    os.makedirs(project_path)
    os.chdir(project_path)

    print("Creating virtual environment...")
    run_command([sys.executable, "-m", "venv", "venv"])

    venv_python = os.path.join(project_path, "venv", "bin", "python")
    venv_pip = os.path.join(project_path, "venv", "bin", "pip")

    print("Installing Django and Django REST Framework...")
    run_command([venv_pip, "install", "Django", "djangorestframework", "psycopg2-binary"])

    print(f"Creating Django project: {project_name}")
    run_command([venv_python, "-m", "django", "startproject", project_name, "."], cwd=project_path)

    print("Creating Django app: inventory")
    run_command([venv_python, "manage.py", "startapp", "inventory"], cwd=project_path)

    print("Creating templates and static directories...")
    os.makedirs(os.path.join(project_path, project_name, "templates", "inventory"), exist_ok=True)
    os.makedirs(os.path.join(project_path, project_name, "static"), exist_ok=True)
    
    print(f"Django inventory project '{project_name}' created successfully at {project_path}")
    print("
Next steps:")
    print(f"1. Navigate to the project directory: cd {project_path}")
    print("2. Activate the virtual environment: source venv/bin/activate")
    print("3. Copy the provided code snippets into their respective files.")
    print("4. Run migrations: python manage.py makemigrations && python manage.py migrate")
    print("5. Create a superuser: python manage.py createsuperuser")
    print("6. Run the development server: python manage.py runserver")

if __name__ == "__main__":
    # You can change the parent directory where the project will be created
    # For example: parent_directory = "/home/Adminbrandon/Documentos"
    parent_directory = os.getcwd() # Current working directory
    create_django_inventory_project(parent_directory)
