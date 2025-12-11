
# Wallapop Fraud Radar — Smartphone Monitoring Pipeline  
**Asignatura:** Network Management (NM) — Wallapop Fraud Detection Lab  
**Categoría analizada:** *Smartphones* (Taxonomía ID: **9447**)  Marcas 'Iphone', 'Samsung' y 'Xiaomi'.
**Python utilizado:** **3.9.2**  
**Entorno:** Máquinas virtuales del laboratorio (Ubuntu ELK + Ubuntu Agent)

---

# 1. Descripción General del Proyecto

Este proyecto implementa un pipeline completo de:

- adquisición periódica de datos,
- enriquecimiento mediante reglas,
- ingesta continua en Elasticsearch mediante Fleet,
- visualización analítica a través de dashboards en Kibana,
- generación de alertas operativas con Elastalert2.

El objetivo es detectar patrones de fraude en la categoría **Smartphones**, utilizando un sistema de puntuación de riesgo (Risk Score) inspirado en detecciones reales de marketplaces.

---

# 2. Ejecución del Poller en las máquinas virtuales

Todo el trabajo se ha realizado sobre las máquinas virtuales del laboratorio.

El archivo `poller.py` se ha colocado en el servidor **elastic** dentro del directorio home del usuario root.  
El poller se ejecuta continuamente mediante **tmux**, permitiendo que siga funcionando aunque la sesión SSH se cierre.

## Ejecución con tmux

1. Crear sesión:
```bash
tmux new -s win2
```

2. Ejecutar el poller:
```bash
python3 poller.py
```

3. Desacoplar sesión:
```bash
Ctrl + B, luego D
```

4. Volver a entrar:
```bash
tmux attach -t win2
```

## Frecuencia  
El poller ejecuta el ciclo **cada 30 minutos**, obteniendo anuncios nuevos y enriqueciéndolos con un risk score.

---

# 3. Funciones principales del Poller

El archivo `poller.py` realiza:

## 3.1. Filtrado por taxonomía 9447 (Smartphones)

Los smartphones se obtienen por:

- keywords: *iphone, samsung, xiaomi*
- **filtro por taxonomía directa**:

```text
taxonomy_id = 9447
```

## 3.2. Cálculo de Risk Score (0–100)

Reglas implementadas:

| Señal | Condición | Puntos |
|------|-----------|--------|
| Precio < 50% de mediana | Muy sospechoso | +40 |
| Precio < 30€ | Extremadamente bajo | +20 |
| Keywords sospechosos | urgente, chollo, réplica, sin factura… | +20 |
| Vendedor con >20 publicaciones | Actividad elevada | +20 |
| Vendedor con 1 único anuncio | Cuenta nueva | +10 |
| Descripción corta | <20 caracteres | +10 |
| Contradicción | “no funciona” + precio >100€ | +10 |
| Solo 1 imagen o repetidas | Posible estafa | +10–15 |
| Título genérico | “movil”, “smartphone…” | +15 |

Toda la información se guarda bajo:

```json
"enrichment": {
  "median_price": X,
  "risk_score": X,
  "suspicious_keywords": [...],
  "risk_factors": [...]
}
```

## 3.3. Guardado de resultados en JSON diario

Cada ciclo guarda los resultados en:

```text
/var/log/wallapop/wallapop_smartphones_<YYYYMMDD>.json
```

Formato: **JSON Lines**, 1 anuncio por línea.

---

# 4. Ingesta de datos mediante Fleet (Elastic Agent)

Utilizamos **Elastic Agent + Fleet Server Policy**, ya configurado previamente en prácticas anteriores.

Se añadió una integración del tipo **Custom Logs (Filestream)**:

## Rutas monitorizadas:
```text
/var/log/wallapop/wallapop_smartphones_*.json
```

## Dataset configurado:
```text
wallapop_project
```

## Data stream generado automáticamente:
```text
logs-wallapop-default
```

Fleet detecta automáticamente los nuevos JSON y los envía a Elasticsearch.

---

# 5. Mapeo de campos del JSON en Elasticsearch

Al ingerir los datos, es necesario asegurar que ciertos campos del JSON se indexen correctamente.

Los campos **asegurados mediante mapeo/mapping** son:

## Campo `publication_time_at` → tipo **date**

Este campo, generado en el poller, normaliza todos los timestamps posibles del API de Wallapop (ISO8601, UNIX segundos, milisegundos, etc.).

Se define en Elasticsearch como:

```json
"publication_time_at": {
  "type": "date"
}
```

Esto permite:

- graficar evolución temporal,
- filtrar por ventanas temporales,
- usarlo como time-field en Discover si se desea.

## Campo `location_geo` → tipo **geo_point**

El poller genera automáticamente:

```json
"location_geo": { "lat": 40.41, "lon": -3.69 }
```

En Elasticsearch se mapea como:

```json
"location_geo": {
  "type": "geo_point"
}
```

Esto habilita:

- visualización en Kibana Maps,
- clustering geográfico,
- búsquedas por radio.

## El resto de campos JSON son interpretados automáticamente por Fleet

Fleet genera:

- plantillas de índice,
- mappings base,
- ILM policy de rotación,
- parámetros del data stream.

---

# 6. Dashboards creados en Kibana

Se han generado dos dashboards principales:

## 6.1 Wallapop Dashboard
Incluye:

- Histograma de precios  
- Evolución temporal de anuncios  
- Top Sellers  
- Keywords frecuentes  
- Mapa geográfico usando `location_geo`  
- Distribución por categorías/taxonomía  

## 6.2 Risk Smartphones Dashboard

Devoted to fraud analysis:

- Histograma del campo `risk_score`  
- Evolución temporal de anuncios con riesgo > 60  
- Scatterplot riesgo vs precio  
- Gráficos de factores de riesgo  
- Palabras clave sospechosas  

Capturas almacenadas en:

```text
kibana/CAPTURAS.pdf
```

---

# 7. Configuración de Elastalert2

Elastalert2 se ha instalado en la máquina elastic:

```bash
pip3 install elastalert
```

## Directorio de configuración:
```text
/etc/elastalert/
    ├── config.yaml
    └── rules/
        ├── 01_low_price.yaml
        ├── 02_high_risk_score.yaml
        └── 03_suspicious_keywords.yaml
```

## Reglas implementadas:

1. **Low Price Alert**  
2. **High Risk Score Alert (>= 70)**  
3. **Suspicious Keyword Alert**

## Logs de Elastalert

Los logs de estado se visualizan en Elasticsearch bajo el índice:

```text
elastalert_status
```

---

# 8. Estructura del repositorio en github

```text
elastalert/
│── rules/
│     ├── 01_low_price.yaml
│     ├── 02_high_risk_score.yaml
│     └── 03_suspicious_keywords.yaml
│── config.yaml

ingestion/
│── wallapop_smartphones_<fecha>.json (ejemplo de móviles observados en un día)

kibana/
│── CAPTURAS.pdf
│── Risk Smartphones.ndjson
│── Wallapop Dashboard.ndjson

poller/
│── poller.py

Preguntas ChatGPT.pdf
README.md
DETECCIÓN DE ESTAFADORES EN WALLAPOP.pptx
```

---

# 9. Conclusión

El pipeline desarrollado:

✔ monitoriza anuncios en tiempo real  
✔ aplica reglas de riesgo avanzadas  
✔ ingesta automáticamente los datos en Elasticsearch  
✔ construye dashboards profesionales  
✔ dispara alertas operativas mediante Elastalert2  

Constituye un **Fraud Radar funcional** basado en reglas y totalmente operativo dentro del entorno de laboratorio.
