# Microservicio de Reportes Excel

Servicio especializado en la generación masiva de reportes en formato Excel (.xlsx), desacoplado del backend principal para no bloquear el hilo de ejecución de la API.

## Características
- Consumo de datos vía Internal API con JWT.
- Uso de bibliotecas optimizadas para streaming de Excel.
- Reducción de carga de CPU en el backend de Django.
