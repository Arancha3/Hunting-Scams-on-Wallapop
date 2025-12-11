<H1 align="center"> 🕵️ Wallapop Fraud Radar: SMARTPHONES

## Descripción del Proyecto
Este proyecto implementa un sistema completo de monitorización continua y Detección de Fraude para anuncios publicados en Wallapop, centrado en la categoría Smartphones. 
El sistema simula una tubería de detección de fraude (Fraud Detection Pipeline) completa, desde la recolección de datos hasta la generación de alertas en tiempo real. La ingesta de datos se realiza a través de Elastic Agent y Fleet(Opción B), aprovechando la automatización de Index Lifecycle Management (ILM).

## **Objetivos principales:**
- Adquisición periódica y fiable de datos públicos de la API de Wallapop.
- Aplicación de un sistema de puntuación de riesgo (Risk Scoring) basado en reglas que cuantifica la sospecha de cada anuncio (0-100)
- Ingesta y gestión de datos con Elastic Stack (Elasticsearch, Kibana). 
- Creación de un "Fraud Radar Dashboard" para el análisis visual. 
- Implementación de un sistema de alertas con Elastalert2 para reaccionar ante anomalías de alto riesgo. 

**Miembros del grupo:**
- Aránzazu Araguás
- Carla Ballesteros
- Imene Mouri

**Categoría elegida:** `Smartphones`

**ID de Categoría:** `9447`

**Requisitos:**
- **Python:** Se recomienda 3.8 o superior                               
- **ElastAlert:** configurado para leer desde el índice de Wallapop
---
## **Estructura del proyecto subido a github:**
``` text
wallapop-fraud-lab/
├── poller/                              # Adquisición Enriquecimiento y Risk Scoring
│   └── poller.py                        # Script principal (adquisición, enriquecimiento, escritura JSON Lines)
├── ingestion/                           # Ingesta en Elasticsearch/Fleet
│   └── wallapop_smartphones_json/              # Muestra de datos finales (al menos 20 ítems)
├── elastalert/                          # Sistema de Alertas
│   ├── config.yaml                      # Configuración del Elastalert2
│   └── rules/                           # Reglas de alerta YAML
│       ├── 01_low_price.yaml            # Alerta de precio anómalo 
│       ├── 02_high_risk.yaml            # Alerta de riesgo >= 70 
│       └── 03_suspicious_keywords.yaml  # Alerta de keywords sospechosos
└──
```
---
## **🚨Análisis y Lógica de Sospecha**
El sistema está optimizado para detectar patrones de fraude específicos de la categoría Smartphones, buscando la desviación de lo que considera "normal" en ese segmento.

| Patrón de Fraude          | Señales de Detección                                                                                 |
|---------------------------|------------------------------------------------------------------------------------------------------|
| Precios Anómalos          | Ítems con precios muy por debajo de la mediana del mercado (ej., smartphones <50% del precio medio). |
| Riesgo por Palabras Clave | Presencia de términos como "urgente", "chollo", o específicos como "imei bloqueado" (Smartphones).   |
| Comportamiento Masivo     | Vendedores que publican un volumen inusual de ítems en un solo día (High Seller Activity).           |
| Vendedor Generalista      | Vendedor con publicaciones en 5 o más categorías no relacionadas (Category Spread).                  |

---
## **Puntuación de Riesgo**

| Categoría                      | Condición                                                | Puntos |
|--------------------------------|----------------------------------------------------------|--------|
| Price Anomaly                  | Precio <50% de la mediana de la colección                | +40    |
| Extremely low price            | Precio < 30€                                             | +20    |
| Keyword suspicion              | Palabras clave como: Urgente, Sin caja, chollo, solo hoy | +20    |
| Seller high behaviour          | Vendedor con >20 publicaciones en la colección de hoy    | +20    |
| Seller 1 post                  | Vendedor con exactamente una publicación                 | +10    |
| Short Description              | Descripción <20 caracteres                               | +10    |
| Old models overpriced          | Modelo antiguo con precio > 1.5 veces la mediana         | +10    |
| High-end with weak description | Modelo high-end con descripción < 30 caracteres          | +20    |
| Generic title                  | Título es "movil", "smartphone" o "teléfono"             | +15    |
| Repeated images                | Imágenes repetidas (si la mitad de imágenes son iguales) | +10    |
| Only one image                 | El articulo tiene solo una imagen                        | +15    |
| Contradiction in text          | Descripción incluye "no funciona" y precio > 100€        | +10    |
| Puntuación máxima              | La suma de puntos se limita a 100                        |  100   |

## EJECUCIONES
**Cómo ejecutar el poller**
El script se encarga de la recolección, el enriquecimiento con el Risk Score y la escritura al formato JSON Lines diario. 
Para asegurar la monitorización continua durante las pruebas, utilizamos **tmux* para ejecutar el Poller en una sesión 
persistente en el servidor de Elastic Agent.

Estrategia: Consulta a la API usando el filtro obligatorio time_filter: today .

Comandos de Ejecución (Usando tmux):

1. Iniciar la sesión de tmux:
    ``` tmux new -s win1 ```

2. Ejecutar el script dentro de la sesión de tmux: 
    ``` python3 poller.py ```
3. Guardar datos cada media hora en formato JSON
   
4. Desconectar (detach) de la sesión de tmux (dejar corriendo en segundo plano):
   ``` Ctrl + B, luego D ```
5. Verificación: 
    Para volver a la sesión y ver los logs del Poller, usamos
  ```  tmux attach -t win1 ```

---

**Cómo ingresar datos en Elasticsearch**
1. Dejamos el poller ejecutándose periódicamente (usando tmux) y guardamos los datos de hoy en formato JSON.

    - El poller escribe el archivo en un directorio específico que el Agente está vigilando (/var/log/wallapop/...)
      
2. Elastic Agent lee el archivo JSON y envía custom Logs

    - En Fleet se configura la integración "Custom Logs"
      
    - Monitorea la carpeta configurada (/var/log/wallapop/...)

    - Cuando se genera o se actualiza un archivo nuevo, el agente lee cada línea como objeto JSON independiente.

    - Ahora que ya tiene todos los archivos, el agente envía los documentos directamente a Elasticsearch
      
3. Elasticsearch Gestiona Data Stream

    - Elasticsearch recibe los datos en un Data Stream (logs-wallapop.default?)

    - Fleet y Data Stream se encargan automáticamente de crear las plantillas de índice, mapeos, políticas de rotación.
   
---

**Cómo ejecutar ElastAlert**
1. Requisitos Previos
    - Configuración principal (config.yaml): Verificar que el archivo (.yaml) apunte a instancia de Elasticsearch
    -  Reglas bien guardadas: Verificar que las reglas de alerta (low_price.yaml, high_risk.yaml...) estén guardadas en la carpeta...
    -  Datos de alto riesgo: Asegurarse de que el poller ha ingerido datos donde el campo enrichment.risk_score es 70 ya que son necesarios para que la alerta se dispare.
2. 
---

## **🖼️Visualizaciones (Evidencia de Funcionamiento)**
- Toda la evidencia de funcionamiento se encuentra en las carpetas de capturas de pantalla:

    - kibana/screenshots/: Contiene el Fraud Radar Dashboard ensamblado, demostrando la operatividad de las visualizaciones requeridas (Price Histogram, Geo Map, etc.)
    - elastalert/screenshots/: Contiene la prueba de la alerta disparada (ej., el log de Elastalert que muestra un match)

---
