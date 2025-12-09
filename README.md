<H1 align="center"> 🕵️ Wallapop Fraud Radar: SMARTPHONES

**Descripción del Proyecto**
Este proyecto implementa un sistema completo de monitorización continua y Detección de Fraude para anuncios publicados en Wallapop, centrado en la categoría Smartphones. 
El sistema simula una tubería de detección de fraude (Fraud Detection Pipeline) completa, desde la recolección de datos hasta la generación de alertas en tiempo real. La ingesta de datos se realiza a través de Elastic Agent y Fleet(Opción B), aprovechando la automatización de Index Lifecycle Management (ILM).

**Objetivos principales:**
- Adquisición periódica y fiable de datos públicos de la API de Wallapop.
- Aplicación de un sistema de puntuación de riesgo (Risk Scoring) basado en reglas que cuantifica la sospecha de cada anuncio (0-100)
- Ingesta y gestión de datos con Elastic Stack (Elasticsearch, Kibana). 
- Creación de un "Fraud Radar Dashboard" para el análisis visual. 
- Implementación de un sistema de alertas con Elastalert2 para reaccionar ante anomalías de alto riesgo. 

**Miembros del grupo:**
- 
-
-
**Categoría elegida:** `Smartphones`
**ID de Categoría:** 24201

**Requisitos:**
- **Python:** Se recomienda 3.8 o superior                               |
- **ElastAlert:** configurado para leer desde el índice de Wallapop
---
**Estructura del proyecto (archivos importantes):**

wallapop-fraud-lab/
├── poller/                     # Adquisición Enriquecimiento y Risk Scoring
│   ├── poller.py               # Script principal (adquisición, enriquecimiento, escritura JSON Lines)
│   └── README.md
├── ingestion/                  # Ingesta en Elasticsearch/Fleet
│   ├── fleet_integration.md
│   └── example_daily_json/     # Muestra de datos finales (al menos 20 ítems)
├── kibana/                     # Visualización y Dashboards
│   └── screenshots/            # Capturas de pantalla de dashboards y visualizaciones
├── elastalert/                 # Sistema de Alertas
│   ├── config.yaml             # Configuración del Elastalert2
│   └── rules/                  # Reglas de alerta YAML
│       ├── low_price.yaml      # Alerta de precio anómalo (Sección 9.4.1)
└──     └── high_risk.yaml      # Alerta de riesgo >= 70 (Sección 9.4.2)

---
**🚨Análisis y Lógica de Sospecha**
El sistema está optimizado para detectar patrones de fraude específicos de la categoría Smartphones, buscando la desviación de lo que considera "normal" en ese segmento.

| Patrón de Fraude          | Señales de Detección                                                                                 |
|---------------------------|------------------------------------------------------------------------------------------------------|
| Precios Anómalos          | Ítems con precios muy por debajo de la mediana del mercado (ej., smartphones <50% del precio medio). |
| Riesgo por Palabras Clave | Presencia de términos como "urgente", "chollo", o específicos como "imei bloqueado" (Smartphones).   |
| Comportamiento Masivo     | Vendedores que publican un volumen inusual de ítems en un solo día (High Seller Activity).           |
| Vendedor Generalista      | Vendedor con publicaciones en 5 o más categorías no relacionadas (Category Spread).                  |

---
**Puntuación de Riesgo**

| Señal                | Condición                                                | Puntos |
|----------------------|----------------------------------------------------------|        |
| Price Anomaly        | Precio <50% de la mediana de la colección                | +40    |
| Keyword Match        | Palabras clave como: Urgente, Sin caja, chollo, solo hoy | +20    |
| High Seller Activity | Vendedor con >20 publicaciones en la colección de hoy    | +20    |
| Short Description    | Descripción <20 caracteres                               | +10    |


**Cómo ejecutar el poller**
El script se encarga de la recolección, el enriquecimiento con el Risk Score y la escritura al formato JSON Lines diario. 
Para asegurar la monitorización continua durante las pruebas, utilizamos **tmux* para ejecutar el Poller en una sesión 
persistente en el servidor de Elastic Agent.

Estrategia: Consulta a la API usando el filtro obligatorio time_filter: today .

Comandos de Ejecución (Usando tmux):

1. Iniciar la sesión de tmux:
    tmux new -s wallapop_poller

2. Ejecutar el script dentro de la sesión de tmux: 
    python3 poller/poller.py

3. Desconectar (detach) de la sesión de tmux (dejar corriendo en segundo plano):
    Ctrl + B, luego D
4. Verificación: 
    Para volver a la sesión y ver los logs del Poller, usamos
    tmux attach -t wallapop_poller

---

**Cómo ingresar datos en Elasticsearch**


**Cómo ejecutar ElastAlert (local / en vivo)**


**🖼️Visualizaciones (Evidencia de Funcionamiento)**
Toda la evidencia de funcionamiento se encuentra en las carpetas de capturas de pantalla.
    - kibana/screenshots/: Contiene el Fraud Radar Dashboard ensamblado, demostrando la operatividad de las visualizaciones requeridas (Price Histogram, Geo Map, etc.) .
    - elastalert/screenshots/: Contiene la prueba de la alerta disparada (ej., el log de Elastalert que muestra un match).

**💡Conclusiones**
Resultados: 
