# Investigación de la API de GBIF para Consumo de Datos de Biodiversidad

La **Infraestructura Mundial de Información en Biodiversidad (GBIF)** ofrece un conjunto robusto de APIs RESTful gratuitas que permiten acceder a millones de registros sobre biodiversidad a nivel mundial. Migrar o complementar nuestro actual script de *web scraping* (o consumo de catálogos locales) hacia la API de GBIF presenta ventajas sustanciales de velocidad, escalabilidad y estandarización de datos.

## Beneficios Principales de usar GBIF

> [!TIP]
> **Estandarización Darwin Core (DwC):** Todos los datos en GBIF se entregan bajo este estándar internacional, lo que facilita la interoperabilidad con otros sistemas científicos.

1. **Evitar Web Scraping y Bloqueos:** Al ser una API pública y oficial, no dependemos del parseo de HTML ni corremos un riesgo alto de que nuestra IP sea baneada por consumo masivo, siempre y cuando respetemos sus cuotas o utilicemos el sistema de "Descargas Asíncronas".
2. **Consultas a Gran Escala:** Se pueden solicitar descargas masivas (`Downloads API`) y GBIF se encarga de empaquetarlas en sus servidores y enviarnos un enlace cuando estén listas (archivos CSV o Darwin Core Archive).
3. **Calidad de Taxonomía:** La *Species API* permite resolver problemas taxonómicos comunes como sinónimos, nombres aceptados y nombres comunes (vernáculos) con gran facilidad.

---

## Módulos de la API Analizados

### 1. Species API
Esta API interactúa con el "Backbone" taxonómico de GBIF. Es fundamental para alinear nuestras especies (polinizadores y plantas) con los IDs globales taxonómicos (TaxonKeys).

- **Name Match (`/v1/species/match`):** Dado el nombre de una especie (ej. *Passer domesticus*), devuelve su `usageKey` (el ID interno de GBIF), su clasificación jerárquica (reino, filo, clase, orden, familia) y si el nombre es aceptado o un sinónimo.
- **Nombres Comunes (`/v1/species/{id}/vernacularNames`):** Obtiene todos los nombres vernáculos o comunes asociados a la especie en distintos idiomas.
- **Búsquedas Jerárquicas:** Se puede buscar todas las especies que pertenezcan a un orden o familia específicos (ej. todas las aves o todas las plantas vasculares).

### 2. Maps API
La **Maps API (`/v2/maps`)** de GBIF es extremadamente útil para el frontend si deseamos visualizar dónde se distribuyen estas especies.

> [!NOTE]
> En lugar de descargar todos los vectores ZIP o Shapefiles y renderizarlos nosotros mismos (lo cual es muy pesado), la Maps API de GBIF proporciona **mapas de calor interactivos (tiles vectoriales y raster)** que se pueden integrar directamente en librerías como Leaflet o Mapbox GL.

- Devuelve *tiles* de densidad (raster `.png` o vectoriales `.mvt`) basados en puntos de ocurrencias reales de las especies (`taxonKey`).
- Podemos customizar colores, resolución y proyecciones geográficas.

### 3. Occurrence / Downloads API
Para descargar observaciones biológicas masivas.
En lugar de iterar página por página (paginación) para miles de especies, podemos armar un archivo `JSON` con nuestra consulta (ej. "Descargar todas las ocurrencias de las especies X, Y, Z en México") y enviarlo por `POST` a `/v1/occurrence/download/request`.

- GBIF procesará el archivo en segundo plano.
- Nos enviará un correo (o consultamos el estado) cuando el archivo `.zip` (CSV) gigante esté listo.
- Soporta filtros avanzados (coordenadas geográficas espaciales, años, identificadores).

### 4. Registry API
Proporciona metadatos sobre las instituciones, redes y conjuntos de datos (datasets) que publican información en GBIF. Es útil para dar créditos adecuados a los proveedores de la información de nuestras especies.

---

## Propuesta de Integración

> [!IMPORTANT]
> **Transición:** Si decidimos implementar GBIF en un futuro, el flujo cambiaría de ser un *"bucle de peticiones simultáneas a una web"* a un flujo **híbrido y optimizado**:

1. **Paso 1: Mapeo (Species API)**
   Tomamos nuestro catálogo de `1,188` plantas melíferas y `2,732` polinizadores, y cruzamos los nombres científicos con `/v1/species/match` para obtener los `taxonKey` de GBIF.
2. **Paso 2: Descarga de Datos (Downloads API)**
   Agrupamos esos `taxonKey` y solicitamos una descarga asíncrona masiva. Esperamos a que GBIF genere el CSV comprimido y lo descargamos de una sola vez.
3. **Paso 3: Visualización (Maps API)**
   Las aplicaciones cliente / web simplemente llamarán a los *Tiles* de GBIF pasándole el `taxonKey`, evitando que tengamos que almacenar y servir gigabytes de datos geográficos.

## Referencias
- [GBIF API Beginner's Guide](https://data-blog.gbif.org/post/gbif-api-beginners-guide/)
- [GBIF Technical Docs](https://techdocs.gbif.org/)
