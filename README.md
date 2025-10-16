# TexCore Project

This project aims to develop a comprehensive system for a textile company with multiple branches (sedes) and areas, focusing on material tracking, inventory control, production orders (especially for dyeing), and user management with role-based access control.

## Project Structure

-   **`TexCore/`**: Main Django project settings and URL configurations.
-   **`gestion/`**: Django app containing core models, serializers, views, and database migrations.
-   **`frontend/`**: React frontend application.

## Backend Development (Django REST Framework)

### Features Implemented in this Phase:

1.  **JWT Authentication Setup:**
    *   Integrated `djangorestframework-simplejwt` for token-based authentication.
    *   Configured `settings.py` with `rest_framework_simplejwt` and `JWTAuthentication`.
    *   Added `/api/token/` (for obtaining tokens) and `/api/token/refresh/` (for refreshing tokens) endpoints to `TexCore/urls.py`.

2.  **Enhanced CustomUser Model & API:**
    *   **`CustomUser` Model (`gestion/models.py`):**
        *   Added `date_of_birth` field.
        *   Implemented many-to-many `superior` relationship to track hierarchical structure within the same `Sede`.
    *   **`CustomUserSerializer` (`gestion/serializers.py`):**
        *   Updated to include `date_of_birth` and `superior` (read-only for now).
    *   **`CustomUserAPIView` (`gestion/views.py`):**
        *   Modified `post` and `put` methods to handle `date_of_birth` and `superior` relationships using Django ORM, while retaining stored procedure calls for other fields.
    *   **Migrations:** Created `0005_customuser_date_of_birth_customuser_superior.py`.

3.  **Material & Inventory Management System:**
    *   **`Material` Model & API:**
        *   **Model (`gestion/models.py`):** Represents different types of raw materials (`name`, `unit_of_measure`).
        *   **Serializer (`gestion/serializers.py`):** `MaterialSerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `MaterialAPIView` for `/api/materials/` and `/api/materials/<int:pk>/`.
        *   **Database Objects (Migration `0007_material_db_objects.py`):** Defined `gestion_material_view` and `create_material`, `update_material`, `delete_material` stored procedures.
    *   **`Batch` Model & API:**
        *   **Model (`gestion/models.py`):** Tracks incoming lots of specific materials (`material`, `code`, `initial_quantity`, `current_quantity`, `unit_of_measure`, `date_received`).
        *   **Serializer (`gestion/serializers.py`):** `BatchSerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `BatchAPIView` for `/api/batches/` and `/api/batches/<int:pk>/`.
        *   **Database Objects (Migration `0009_batch_db_objects.py`):** Defined `gestion_batch_view` and `create_batch`, `update_batch`, `delete_batch` stored procedures.
    *   **`Inventory` Model & API:**
        *   **Model (`gestion/models.py`):** Tracks current stock of `Material` per `Sede` and `Area` (`material`, `sede`, `area`, `quantity`).
        *   **Serializer (`gestion/serializers.py`):** `InventorySerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `InventoryAPIView` for `/api/inventory/` and `/api/inventory/<int:pk>/`.
        *   **Database Objects (Migration `0011_inventory_db_objects.py`):** Defined `gestion_inventory_view` and `create_inventory`, `update_inventory`, `delete_inventory` stored procedures.
    *   **`ProcessStep` Model & API:**
        *   **Model (`gestion/models.py`):** Defines stages of production (`name`, `description`).
        *   **Serializer (`gestion/serializers.py`):** `ProcessStepSerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `ProcessStepAPIView` for `/api/process-steps/` and `/api/process-steps/<int:pk>/`.
        *   **Database Objects (Migration `0013_processstep_db_objects.py`):** Defined `gestion_processstep_view` and `create_processstep`, `update_processstep`, `delete_processstep` stored procedures.
    *   **`MaterialMovement` Model & API:**
        *   **Model (`gestion/models.py`):** Logs material transfers (`batch`, `from_sede`, `from_area`, `to_sede`, `to_area`, `process_step`, `quantity`, `movement_type`, `timestamp`, `responsible_user`).
        *   **Serializer (`gestion/serializers.py`):** `MaterialMovementSerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `MaterialMovementAPIView` for `/api/material-movements/` and `/api/material-movements/<int:pk>/`.
        *   **Database Objects (Migration `0015_materialmovement_db_objects.py`):** Defined `gestion_materialmovement_view` and `create_materialmovement`, `update_materialmovement`, `delete_materialmovement` stored procedures.

4.  **Chemical Control System:**
    *   **`Chemical` Model & API:**
        *   **Model (`gestion/models.py`):** Manages chemicals (`code`, `name`, `description`, `current_stock`, `unit_of_measure`).
        *   **Serializer (`gestion/serializers.py`):** `ChemicalSerializer` for CRUD operations.
        *   **API View (`gestion/views.py`):** `ChemicalAPIView` for `/api/chemicals/` and `/api/chemicals/<int:pk>/`.
        *   **Database Objects (Migration `0017_chemical_db_objects.py`):** Defined `gestion_chemical_view` and `create_chemical`, `update_chemical`, `delete_chemical` stored procedures.
    *   **`Formula` and `FormulaChemical` Models & API:**
        *   **Models (`gestion/models.py`):** `Formula` for dyeing formulas (`name`, `description`) and `FormulaChemical` (intermediate model) to link `Formula` to `Chemical` with specific `quantity` and `unit_of_measure`.
        *   **Serializers (`gestion/serializers.py`):** `FormulaSerializer` and `FormulaChemicalSerializer` for CRUD operations.
        *   **API Views (`gestion/views.py`):** `FormulaAPIView` for `/api/formulas/` and `/api/formulas/<int:pk>/`, and `FormulaChemicalAPIView` for `/api/formula-chemicals/` and `/api/formula-chemicals/<int:pk>/`.
        *   **Database Objects (Migration `0018_formula_formulachemical_formula_chemicals.py`):** Defined `gestion_formula_view`, `gestion_formulachemical_view` and their respective CRUD stored procedures.

## Getting Started

### Prerequisites

-   Python 3.x
-   PostgreSQL
-   Node.js and npm (for frontend)

### Backend Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/DevBrandonArellano/TexCore.git
    cd TexCore
    ```
2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
3.  **Install Python dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Configure PostgreSQL:**
    *   Ensure PostgreSQL is running.
    *   Create a database named `TexCore` (or as configured in `TexCore/settings.py`).
    *   Update `DATABASES` settings in `TexCore/settings.py` with your PostgreSQL credentials.

5.  **Run migrations:**
    ```bash
    python manage.py migrate
    ```
6.  **Create a superuser (for Django Admin):**
    ```bash
    python manage.py createsuperuser
    ```
7.  **Run the Django development server:**
    ```bash
    python manage.py runserver
    ```
    (If port 8000 is in use, try `python manage.py runserver 8001`)

### Frontend Setup

1.  **Navigate to the frontend directory:**
    ```bash
    cd frontend
    ```
2.  **Install Node.js dependencies:**
    ```bash
    npm install
    ```
3.  **Start the React development server:**
    ```bash
    npm start
    ```

## API Endpoints

All API endpoints are prefixed with `/api/`.

### Authentication
-   `POST /api/token/`: Obtain JWT access and refresh tokens.
-   `POST /api/token/refresh/`: Refresh JWT access token.

### Gestion App
-   **Sedes:**
    -   `GET /api/sedes/`: List all sedes.
    -   `GET /api/sedes/<int:pk>/`: Retrieve a single sede.
    -   `POST /api/sedes/`: Create a new sede.
    -   `PUT /api/sedes/<int:pk>/`: Update a sede.
    -   `DELETE /api/sedes/<int:pk>/`: Delete a sede.
-   **Areas:**
    -   `GET /api/areas/`: List all areas.
    -   `GET /api/areas/<int:pk>/`: Retrieve a single area.
    -   `POST /api/areas/`: Create a new area.
    -   `PUT /api/areas/<int:pk>/`: Update an area.
    -   `DELETE /api/areas/<int:pk>/`: Delete an area.
-   **Users:**
    -   `GET /api/users/`: List all users.
    -   `GET /api/users/<int:pk>/`: Retrieve a single user.
    -   `POST /api/users/`: Create a new user.
    -   `PUT /api/users/<int:pk>/`: Update a user.
    -   `DELETE /api/users/<int:pk>/`: Deactivate a user.
-   **Materials:**
    -   `GET /api/materials/`: List all materials.
    -   `GET /api/materials/<int:pk>/`: Retrieve a single material.
    -   `POST /api/materials/`: Create a new material.
    -   `PUT /api/materials/<int:pk>/`: Update a material.
    -   `DELETE /api/materials/<int:pk>/`: Delete a material.
-   **Batches:**
    -   `GET /api/batches/`: List all batches.
    -   `GET /api/batches/<int:pk>/`: Retrieve a single batch.
    -   `POST /api/batches/`: Create a new batch.
    -   `PUT /api/batches/<int:pk>/`: Update a batch.
    -   `DELETE /api/batches/<int:pk>/`: Delete a batch.
-   **Inventory:**
    -   `GET /api/inventory/`: List all inventory items.
    -   `GET /api/inventory/<int:pk>/`: Retrieve a single inventory item.
    -   `POST /api/inventory/`: Create a new inventory item.
    -   `PUT /api/inventory/<int:pk>/`: Update an inventory item.
    -   `DELETE /api/inventory/<int:pk>/`: Delete an inventory item.
-   **Process Steps:**
    -   `GET /api/process-steps/`: List all process steps.
    -   `GET /api/process-steps/<int:pk>/`: Retrieve a single process step.
    -   `POST /api/process-steps/`: Create a new process step.
    -   `PUT /api/process-steps/<int:pk>/`: Update a process step.
    -   `DELETE /api/process-steps/<int:pk>/`: Delete a process step.
-   **Material Movements:**
    -   `GET /api/material-movements/`: List all material movements.
    -   `GET /api/material-movements/<int:pk>/`: Retrieve a single material movement.
    -   `POST /api/material-movements/`: Create a new material movement.
    -   `PUT /api/material-movements/<int:pk>/`: Update a material movement.
    -   `DELETE /api/material-movements/<int:pk>/`: Delete a material movement.
-   **Chemicals:**
    -   `GET /api/chemicals/`: List all chemicals.
    -   `GET /api/chemicals/<int:pk>/`: Retrieve a single chemical.
    -   `POST /api/chemicals/`: Create a new chemical.
    -   `PUT /api/chemicals/<int:pk>/`: Update a chemical.
    -   `DELETE /api/chemicals/<int:pk>/`: Delete a chemical.
-   **Formulas:**
    -   `GET /api/formulas/`: List all formulas.
    -   `GET /api/formulas/<int:pk>/`: Retrieve a single formula.
    -   `POST /api/formulas/`: Create a new formula.
    -   `PUT /api/formulas/<int:pk>/`: Update a formula.
    -   `DELETE /api/formulas/<int:pk>/`: Delete a formula.
-   **Formula Chemicals:**
    -   `GET /api/formula-chemicals/`: List all formula-chemical relationships.
    -   `GET /api/formula-chemicals/<int:pk>/`: Retrieve a single formula-chemical relationship.
    -   `POST /api/formula-chemicals/`: Create a new formula-chemical relationship.
    -   `PUT /api/formula-chemicals/<int:pk>/`: Update a formula-chemical relationship.
    -   `DELETE /api/formula-chemicals/<int:pk>/`: Delete a formula-chemical relationship.

## Future Enhancements

-   Implement role-based access control (RBAC) in API views.
-   Develop frontend CRUD interfaces for all new models.
-   Implement login/logout functionality in the frontend.
-   Create dashboards for material tracking, inventory, and production statistics.
-   Add unit tests for all new backend functionalities.
