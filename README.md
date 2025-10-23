# Proyecto GeoChallenge

[cite_start]Este proyecto implementa una API REST usando Django, GeoDjango, PostgreSQL (PostGIS) y Docker para gestionar y consultar datos geoespaciales ("spots") según los requisitos del desafío [cite: 3-5, 47-53].

## Funcionalidades (Etapa 1 & 2 Completadas)

* **Modelo de Datos:** Modelo geoespacial para almacenar información de los spots, incluyendo ubicación (`PointField`) y seguimiento de la fuente de datos.
* **Carga de Datos:**
    * [cite_start]Comando Django (`load_spots`) para `lk_spots.csv` [cite: 8, 57-58].
    * [cite_start]Comando Django (`load_props`) para normalizar y cargar `props_list.json`, incluyendo geocodificación [cite: 41, 59-62].
* [cite_start]**API REST:** Endpoints para [cite: 10, 16-17]:
    * [cite_start]Listar/Filtrar/Ordenar/Paginar spots (`GET /api/spots/`) [cite: 19-20, 23-24, 42].
    * [cite_start]Spots cercanos (`GET /api/spots/nearby/?lat=...`) [cite: 21-22].
    * [cite_start]Spots dentro de polígono (`POST /api/spots/within/`) [cite: 25-31].
    * [cite_start]Precio promedio de renta por sector (`GET /api/spots/average-price-by-sector/`) [cite: 32-33].
    * [cite_start]Detalle de spot (`GET /api/spots/{spot_id}/`) [cite: 34-35].
    * [cite_start]Ranking por precio de renta (`GET /api/spots/top-rent/?limit=...`) [cite: 36-37].
* [cite_start]**Documentación de API:** Generación automática de Swagger UI/OpenAPI (`drf-spectacular`)[cite: 45].
* [cite_start]**Dockerizado:** Configuración completa con Docker y Docker Compose[cite: 53].
* [cite_start]**Indexación Geoespacial:** Índices espaciales automáticos de PostGIS para consultas eficientes[cite: 44].
* [cite_start]**Pruebas:** Pruebas de integración para la API y los comandos de carga de datos[cite: 43].

---

## Configuración y Ejecución

1.  **Prerrequisitos:**
    * Docker
    * Docker Compose

2.  **Clonar Repositorio:**
    * Clona este repositorio.

3.  **Configuración del Entorno (`.env`):**
    * Navega a la raíz del proyecto.
    * Crea un archivo `.env`.
    * Copia el siguiente contenido y **reemplaza los placeholders**, especialmente `DJANGO_SECRET_KEY`.

    ```env
    # .env file content
    DB_NAME=geochallenge_db       # Nombre de la base de datos
    DB_USER=geouser             # Usuario de la base de datos
    DB_PASSWORD=geopassword         # Contraseña de la base de datos
    DJANGO_SECRET_KEY='your-strong-secret-key-here!' # IMPORTANTE: ¡Genera una clave segura!
    DEBUG=1                     # Cambia a 0 para producción
    ```
    * El usuario y contraseña serán creados automáticamente por PostGIS en Docker.
    * Añade `.env` a tu `.gitignore`.

4.  **Archivos de Datos:**
    * Crea un directorio `data` en la raíz.
    * Coloca `lk_spots.csv` y `props_list.json` dentro de `data/`.

5.  **Verificar Nombre del Proyecto:**
    * Asegúrate de que el directorio de configuración Django se llame `geochallenge`. Si no, renómbralo o actualiza las referencias en `manage.py`, `settings.py`, `wsgi.py`, `asgi.py`.

6.  **Verificar Archivos Centrales:**
    * Asegúrate de que `manage.py`, `geochallenge/wsgi.py`, `geochallenge/asgi.py` tengan el contenido estándar y las rutas correctas (`geochallenge.settings`).
    * Verifica que `spots/admin.py` herede de `django.contrib.admin.ModelAdmin`.

7.  **Construir y Ejecutar Contenedores:**
    * En la terminal, desde la raíz del proyecto:
        ```bash
        docker-compose up --build -d
        ```
    * Verifica que ambos contenedores (`db` y `web`) estén `Up` con `docker-compose ps`.

8.  **Migraciones:**
    * Genera las migraciones:
        ```bash
        docker-compose exec web python manage.py makemigrations spots
        ```
    * Aplica las migraciones para crear las tablas:
        ```bash
        docker-compose exec web python manage.py migrate
        ```

9.  **Cargar Datos:**
    * Carga desde CSV:
        ```bash
        docker-compose exec web python manage.py load_spots
        ```
    * Carga y normaliza desde JSON:
        ```bash
        docker-compose exec web python manage.py load_props
        ```

10. **Acceder a la API:**
    * Lista de Spots: `http://localhost:8000/api/spots/`
    * Documentación API (Swagger UI): `http://localhost:8000/api/docs/`

---

## Detalles de la Carga de Datos

* **`lk_spots.csv` (`load_spots`):**
    * [cite_start]Lee CSV limpio, convierte tipos, crea geometrías `Point` [cite: 77-78].
    * Usa `update_or_create` (basado en `spot_id`) para idempotencia.
    * Marca `data_source='csv'`.

* [cite_start]**`props_list.json` (`load_props`):** [cite: 59-62, 41]
    * Lee JSON desnormalizado.
    * **Normalización:**
        * **ID:** Genera `spot_id` secuenciales para registros nuevos.
        * **Ubicación:** Parsea `location` string a `spot_settlement`, `spot_municipality`, `spot_state`.
        * **Geocodificación:** Usa `geopy` (Nominatim) para obtener lat/lon desde `location`. Puebla `PointField` si tiene éxito; incluye delay de 1s.
        * **Operaciones:** Extrae precios (MXN) y `spot_modality` desde `operations`.
        * **Mapeo:** `construction_size` -> `spot_area_in_sqm`, `title` -> `spot_title`, `updated_at` -> `spot_created_date`.
        * **Ignorados:** Campos no existentes en el modelo `Spot`.
    * **Base de Datos:**
        * Usa `get_or_create` (basado en `public_id`) para evitar duplicados. Asigna `spot_id` si es nuevo.
        * Actualiza campos si `public_id` existe y los datos han cambiado.
    * Marca `data_source='json'`.

---

## Endpoints de la API (Ejemplos)

* **Listar/Filtrar/Ordenar/Paginar Spots:**
    * [cite_start]`curl http://localhost:8000/api/spots/` [cite: 19-20]
    * [cite_start]`curl "http://localhost:8000/api/spots/?sector=9&municipality=Tijuana"` [cite: 23-24]
    * `curl "http://localhost:8000/api/spots/?page=2&ordering=-spot_price_total_mxn_rent"`
* **Spots Cercanos:**
    * [cite_start]`curl "http://localhost:8000/api/spots/nearby/?lat=19.4326&lng=-99.1332&radius=5000"` (Radio en metros) [cite: 21-22]
* **Spots Dentro de Polígono:**
    * [cite_start]`curl -X POST http://localhost:8000/api/spots/within/ -H "Content-Type: application/json" -d '{"polygon": {"type": "Polygon", "coordinates": [[[-99.15, 19.42], [-99.12, 19.42], [-99.12, 19.44], [-99.15, 19.44], [-99.15, 19.42]]]}}'` [cite: 25-31]
* **Precio Promedio por Sector:**
    * [cite_start]`curl http://localhost:8000/api/spots/average-price-by-sector/` [cite: 32-33]
* **Detalle de Spot:**
    * [cite_start]`curl http://localhost:8000/api/spots/25564/` (Usa un `spot_id` válido) [cite: 34-35]
* **Top Spots por Renta:**
    * [cite_start]`curl "http://localhost:8000/api/spots/top-rent/?limit=5"` [cite: 36-37]
* **Documentación API:**
    * Visita `http://localhost:8000/api/docs/` en tu navegador.

---

## [cite_start]Pruebas (Testing) [cite: 43]

El proyecto incluye pruebas de integración para verificar la funcionalidad de la API y la lógica de los comandos de carga de datos.

* **Ubicación:** Los archivos de prueba se encuentran en `spots/tests.py` (para la API) y `spots/test_commands.py` (para los comandos).
* **Cobertura:**
    * **API:** Se prueban los endpoints principales (listar, filtrar, ordenar, paginar, detalle, nearby, within, average, top-rent) usando datos de prueba creados en una base de datos temporal.
    * **Comandos:** Se prueban los comandos `load_spots` y `load_props` usando archivos CSV y JSON temporales. Se verifica la creación/actualización de datos, el manejo básico de errores y (para `load_props`) se simula (mockea) la respuesta del servicio de geocodificación.
* **Ejecución:** Para ejecutar todas las pruebas de la aplicación `spots`:
    ```bash
    docker-compose exec web python manage.py test spots
    ```
    Para ejecutar solo las pruebas de los comandos:
    ```bash
    docker-compose exec web python manage.py test spots.test_commands
    ```
    Para ejecutar solo las pruebas de la API:
    ```bash
    docker-compose exec web python manage.py test spots.tests
    ```

---

## Solución de Problemas (Troubleshooting)

* **`service "web" is not running` / `exited with code 0`:** Inicia con `docker-compose up -d`. Revisa logs (`docker-compose logs web`) o corre en primer plano (`docker-compose up --build`). Verifica `manage.py`, `wsgi.py`, `asgi.py`.
* **`relation "..." does not exist`:** Falta aplicar migraciones. Ejecuta `makemigrations spots` y luego `migrate`.
* **`database "..." does not exist`:** Verifica `DB_NAME` en `.env`. Si lo cambiaste, quizás necesites eliminar el volumen (`docker-compose down`, `docker volume rm <volume_name>`, `docker-compose up -d`). Usa `docker volume ls` para encontrar el nombre.
* **`CSV/JSON file not found`:** Verifica que `data/` exista en la raíz con los archivos. Verifica montaje (`./data:/app/data`) en `docker-compose.yml`.
* **`ModuleNotFoundError` / `ImproperlyConfigured (WSGI/ASGI)`:** Revisa nombre del directorio del proyecto vs. configuración en `manage.py`, `settings.py`, `wsgi.py`, `asgi.py`.
* **`AttributeError: ... 'OSMGeoAdmin'`:** Cambia herencia en `spots/admin.py` a `django.contrib.admin.ModelAdmin`.
* **`IntegrityError: null value in column "spot_id"` (`load_props`):** Verifica que `load_props.py` genere `spot_id` al *crear* y que las migraciones de `public_id`, `data_source` se aplicaron.
* **Errores Geocodificación (`load_props`):** Puede ser rate-limiting (revisa `time.sleep`), dirección inválida, o red. El script registra errores.
* **API URL `.../api/` da 404:** Usa rutas específicas como `.../api/spots/`.
* **Pruebas Fallan (`AssertionError: X != Y`):** Revisa si la salida real del comando o el estado de la BD después de ejecutarlo coincide con lo que la prueba espera. Ajusta la aserción (`assertEqual`, `assertIn`, etc.) para que refleje el comportamiento correcto.
* **Pruebas Fallan (`OSError: [Errno 18] Invalid cross-device link`):** Al probar comandos que leen archivos, no uses `os.rename` para mover archivos entre el directorio de pruebas y el directorio `data` (montado como volumen). Usa `shutil.copy` y `os.remove` en su lugar, asegurándote de restaurar los archivos originales en un bloque `finally`.

---

## Próximos Pasos

* **Refinar Normalización:** Mejorar análisis de direcciones en `load_props.py`. Considerar mapear `property_type` o añadir más campos.
* **Filtros/Ordenamiento Avanzados:** Implementar filtros más complejos (rangos, etc.).
* **Testing:** Incrementar la cobertura de pruebas.
* **Documentación:** Mejorar docstrings para Swagger.