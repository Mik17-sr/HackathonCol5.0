# Muévete CB — Agente Inteligente de Recomendación de Rutas

## 1. Visión del proyecto

**Muévete CB** será una plataforma inteligente de movilidad enfocada en la localidad de **Ciudad Bolívar, Bogotá**, cuyo objetivo es recomendar rutas personalizadas utilizando inteligencia artificial, datos de movilidad y análisis predictivo.

La propuesta no busca ser únicamente un buscador tradicional de rutas. El sistema funcionará como un **agente de movilidad**, capaz de comprender la intención del usuario, comparar alternativas, explicar sus decisiones, anticipar posibles retrasos y adaptar la recomendación ante cambios en la red de transporte.

### Propuesta de valor

> **No solamente mostrar una ruta, sino entender el viaje completo del usuario y recomendar la alternativa más conveniente según su contexto.**

---

## 2. Inspiración tecnológica

La propuesta toma como referencia conceptos utilizados en ecosistemas de movilidad inteligente de países con alto desarrollo tecnológico, especialmente:

- **Japón:** MaaS (Mobility as a Service), integración de diferentes medios de transporte y transporte bajo demanda.
- **China:** inteligencia artificial aplicada a la gestión del tráfico, predicción, detección de anomalías, optimización dinámica y agentes inteligentes de movilidad.
- **Ciudades inteligentes:** integración de datos de transporte, información geográfica, sensores, incidencias y modelos predictivos.

Estas referencias no se pretenden copiar directamente. Se adaptan al contexto, infraestructura y disponibilidad de datos de **Ciudad Bolívar**.

---

## 3. Concepto del agente

El agente central, denominado **Muévete CB AI**, recibirá una solicitud en lenguaje natural y la transformará en una consulta estructurada.

### Ejemplo

**Usuario:**

> Estoy en Vista Hermosa y mañana tengo clase a las 7:00 a. m. en la Universidad Distrital. Quiero llegar máximo 10 minutos antes y no caminar más de 10 minutos.

### El agente interpreta

```text
Origen:
Vista Hermosa

Destino:
Universidad Distrital

Hora objetivo:
07:00

Margen:
10 minutos antes

Preferencia:
Limitar caminata
```

Posteriormente consulta el motor de rutas, modelos predictivos y fuentes de información para generar alternativas.

---

## 4. Recomendación multimodal

El sistema debe considerar diferentes medios de transporte:

- Caminata.
- SITP.
- TransMilenio.
- TransMiCable.
- Bicicleta, cuando sea aplicable.
- Combinaciones entre diferentes medios.
- Futuras modalidades de transporte bajo demanda.

La ruta debe representarse como una secuencia de segmentos:

```text
Origen
  ↓
Caminata
  ↓
SITP
  ↓
TransMiCable
  ↓
TransMilenio
  ↓
Caminata
  ↓
Destino
```

---

## 5. Rutas con múltiples criterios

La ruta más rápida no necesariamente será la recomendación final.

El motor debe evaluar diferentes variables:

| Variable | Descripción |
|---|---|
| Tiempo | Duración estimada del viaje |
| Costo | Costo total del recorrido |
| Caminata | Distancia caminando |
| Transbordos | Número de cambios de transporte |
| Espera | Tiempo estimado esperando |
| Congestión | Nivel actual o previsto |
| Confiabilidad | Probabilidad de cumplir el tiempo estimado |
| Accesibilidad | Escaleras, pendientes y distancia |
| Estado del servicio | Alteraciones o interrupciones |
| Contexto temporal | Hora, día y comportamiento histórico |

Esto permitirá generar diferentes alternativas:

### Ruta rápida

- Menor tiempo estimado.
- Puede tener más transbordos.
- Puede presentar mayor variabilidad.

### Ruta confiable

- Puede tardar algunos minutos más.
- Menor variabilidad.
- Menor probabilidad de retraso.

### Ruta de baja caminata

- Reduce desplazamientos a pie.
- Puede incrementar el tiempo total.

El usuario podrá conocer las diferencias antes de seleccionar una opción.

---

## 6. Predicción de tiempos

Una de las funciones principales del componente de IA será estimar el tiempo futuro de viaje.

En lugar de calcular únicamente:

> ¿Cuánto tarda esta ruta ahora?

el sistema buscará responder:

> ¿Cuánto probablemente tardará esta ruta cuando el usuario realice el viaje?

Para ello se podrán considerar:

- Historial de tiempos.
- Hora del día.
- Día de la semana.
- Demanda histórica.
- Congestión.
- Estado del transporte.
- Incidentes.
- Condiciones externas disponibles.
- Cambios conocidos en la operación.

### Ejemplo

```text
Ruta A
Tiempo ideal: 42 min
Tiempo previsto: 51 min
Confiabilidad: alta

Ruta B
Tiempo ideal: 45 min
Tiempo previsto: 47 min
Confiabilidad: muy alta
```

El agente podrá explicar por qué una ruta aparentemente más lenta puede ser una alternativa más conveniente.

---

## 7. Detección y gestión de incidentes

El sistema debe poder reaccionar ante eventos que modifiquen las condiciones de movilidad.

Ejemplos:

- Cierre de estaciones.
- Alteraciones de rutas.
- Mantenimiento.
- Accidentes.
- Congestión.
- Interrupción de TransMiCable.
- Cambios temporales de operación.
- Otros eventos disponibles mediante fuentes de datos.

### Flujo

```text
Incidente detectado
       ↓
Evaluar rutas afectadas
       ↓
Recalcular alternativas
       ↓
Comparar nuevas opciones
       ↓
Notificar al usuario
       ↓
Proponer nueva ruta
```

### Ejemplo

> ⚠️ La ruta seleccionada presenta una alteración. Se encontró una alternativa que incrementa el tiempo estimado en 6 minutos, pero evita el tramo afectado.

---

## 8. TransMiCable como elemento estratégico

Debido a las características geográficas de Ciudad Bolívar, **TransMiCable** debe tratarse como un elemento importante del modelo de movilidad.

El sistema podrá comparar dinámicamente:

```text
SITP → TransMiCable → TransMilenio
```

contra:

```text
SITP → Ruta alternativa → TransMilenio
```

considerando tiempo, espera, demanda, transbordos y condiciones actuales.

---

## 9. Personalización

El agente podrá considerar las preferencias del usuario.

### Perfil orientado al tiempo

```text
Prioridad:
Tiempo ↑↑↑
Confiabilidad ↑↑
Costo ↑
Caminata ↑
```

### Perfil orientado al ahorro

```text
Prioridad:
Costo ↑↑↑
Tiempo ↑
Transbordos ↑
```

### Perfil de baja caminata

```text
Prioridad:
Caminata ↑↑↑
Accesibilidad ↑↑↑
Transbordos ↓
```

Las preferencias deben poder modificarse manualmente. El sistema no debe asumir que una misma ruta es adecuada para todas las personas.

---

## 10. Accesibilidad

El agente debe contemplar necesidades de movilidad diferentes.

Podrá utilizar preferencias como:

- Reducir caminata.
- Evitar escaleras.
- Reducir pendientes.
- Reducir transbordos.
- Priorizar estaciones accesibles.

Ejemplo:

> Esta alternativa tarda 7 minutos más, pero reduce la caminata aproximadamente 650 metros y evita dos tramos con escaleras.

---

## 11. Explicabilidad

Una característica fundamental será que el agente pueda explicar sus recomendaciones.

### Pregunta

> ¿Por qué me recomiendas esta ruta?

### Respuesta esperada

> La ruta A tiene un tiempo estimado de 43 minutos, pero presenta mayor variabilidad y tres transbordos. La ruta B tarda aproximadamente 47 minutos y tiene menor variabilidad. Como priorizaste la confiabilidad, se recomienda la ruta B.

El agente debe diferenciar entre:

- Datos observados.
- Predicciones.
- Preferencias del usuario.
- Decisiones tomadas por el motor de rutas.

---

## 12. Radar de movilidad

La plataforma podrá incluir un mapa de estado de movilidad de Ciudad Bolívar.

### Estados

```text
🟢 Normal
🟡 Demora
🟠 Congestión
🔴 Incidente
🔵 Transporte especial / TransMiCable
```

El sistema no solo visualizará información, sino que podrá generar interpretaciones.

Ejemplo:

> Se detecta una alteración en el sector X. Las rutas que atraviesan esta zona presentan un incremento estimado de 8 a 14 minutos.

---

## 13. Agentes especializados

El sistema puede dividir las responsabilidades de IA en agentes especializados.

```text
Muévete CB AI
│
├── RouteAgent
│   └── Busca y compara rutas
│
├── PredictionAgent
│   └── Predice tiempos y posibles retrasos
│
├── IncidentAgent
│   └── Detecta y analiza alteraciones
│
├── PreferenceAgent
│   └── Gestiona preferencias del usuario
│
└── MobilityAnalysisAgent
    └── Analiza patrones de movilidad
```

Un agente central coordinará las respuestas.

---

## 14. Papel del LLM

El modelo de lenguaje no debe encargarse directamente de calcular las rutas.

Su función principal será:

1. Comprender lenguaje natural.
2. Identificar intención.
3. Extraer restricciones.
4. Consultar herramientas.
5. Comparar resultados.
6. Explicar recomendaciones.
7. Gestionar conversaciones.
8. Solicitar información adicional cuando sea necesaria.

El cálculo de rutas debe quedar en herramientas especializadas.

```text
Usuario
   ↓
LLM / Agente
   ↓
Interpretación
   ↓
Route Engine ──────→ Grafo de transporte
   ↓
Prediction Engine ─→ Modelos predictivos
   ↓
Incident Engine ───→ Eventos
   ↓
Agente
   ↓
Explicación
   ↓
Usuario
```

---

## 15. Motor de rutas

El motor podrá utilizar algoritmos clásicos de grafos y optimización.

Posibles algoritmos:

- Dijkstra.
- A*.
- Multi-Criteria Shortest Path.
- Optimización mediante funciones de costo.
- Ruteo sobre grafos dinámicos.

Cada conexión del grafo puede almacenar:

```text
tiempo
costo
distancia
espera
congestión
confiabilidad
accesibilidad
estado
```

Una función de costo podría combinar estas variables según las preferencias del usuario.

---

## 16. Datos

La plataforma debe priorizar fuentes reales y abiertas de Bogotá.

Posibles fuentes:

- GTFS del SITP.
- Rutas troncales y zonales.
- Información de TransMilenio.
- Información de TransMiCable.
- Datos geográficos.
- Semáforos.
- Incidentes.
- Datos históricos disponibles.
- Otras fuentes abiertas de movilidad.

Los datos deben almacenarse y normalizarse antes de ser utilizados por los modelos.

---

## 17. Arquitectura propuesta

```text
MUÉVETE CB
│
├── frontend/
│   ├── mapa/
│   ├── rutas/
│   ├── chat/
│   ├── perfil/
│   └── alertas/
│
├── backend/
│   ├── api/
│   ├── agents/
│   ├── routes/
│   ├── predictions/
│   ├── incidents/
│   ├── users/
│   └── services/
│
├── data/
│   ├── raw/
│   ├── processed/
│   └── gtfs/
│
├── models/
│   ├── eta/
│   ├── demand/
│   └── congestion/
│
├── database/
│   ├── migrations/
│   └── seeds/
│
└── docs/
    └── ia/
```

---

## 18. Gemelo digital simplificado

Como una línea avanzada del proyecto, se plantea construir un modelo digital simplificado de la movilidad de Ciudad Bolívar.

El modelo permitiría representar:

- Rutas.
- Estaciones.
- Paraderos.
- TransMiCable.
- Conexiones.
- Demanda.
- Incidentes.

Posteriormente podría utilizarse para simulaciones del tipo:

> ¿Qué ocurre si una estación deja de operar?

> ¿Qué rutas se ven afectadas si una conexión presenta congestión?

> ¿Qué alternativas absorben la demanda?

Esta funcionalidad puede plantearse inicialmente como una línea futura y no como un requisito obligatorio del MVP.

---

## 19. Análisis de demanda

Una evolución importante consiste en analizar consultas y patrones de movilidad de forma agregada y anonimizada.

Ejemplo:

```text
Origen A
    ↓
Destino B
    ↓
Alta cantidad de solicitudes
    ↓
Franja horaria recurrente
    ↓
Baja oferta directa
    ↓
Indicador de posible necesidad de movilidad
```

El sistema no debe decidir por las autoridades qué infraestructura construir. Su función sería proporcionar información y patrones que puedan servir como apoyo para análisis posteriores.

---

## 20. MVP recomendado

Para mantener el proyecto realizable, la primera versión debería concentrarse en:

### Fase 1 — Datos

- Integración de GTFS.
- Normalización de rutas.
- Paraderos.
- Estaciones.
- Representación geográfica.

### Fase 2 — Motor de rutas

- Grafo de transporte.
- Dijkstra/A*.
- Rutas multimodales básicas.
- Función de costo.

### Fase 3 — Agente

- Chat en lenguaje natural.
- Extracción de origen y destino.
- Preferencias.
- Consulta al motor de rutas.
- Explicación.

### Fase 4 — Inteligencia

- Predicción de ETA.
- Comparación de alternativas.
- Detección de incidencias.
- Recomendación dinámica.

### Fase 5 — Funciones avanzadas

- Perfil adaptativo.
- Radar de movilidad.
- Simulación.
- Análisis de demanda.
- Gemelo digital simplificado.

---

## 21. Demostración principal

La demostración ideal del proyecto sería:

### Solicitud

> Estoy en Ciudad Bolívar y mañana necesito llegar a la Universidad Distrital a las 7:00 a. m. Quiero llegar unos minutos antes y caminar lo menos posible.

### Sistema

1. Interpreta la solicitud.
2. Obtiene origen y destino.
3. Consulta la red de transporte.
4. Genera varias rutas.
5. Predice tiempos.
6. Evalúa transbordos y caminata.
7. Consulta alteraciones conocidas.
8. Compara alternativas.
9. Selecciona una recomendación según las preferencias.
10. Explica la decisión.
11. Muestra las rutas en el mapa.

### Resultado

```text
Ruta recomendada
────────────────────────────
⏱ Tiempo estimado: 47 min
🚶 Caminata: 8 min
🔄 Transbordos: 2
💰 Costo: $X
📈 Confiabilidad: Alta

¿Por qué?

La ruta tarda 4 minutos más que la alternativa
más rápida, pero presenta menor variabilidad,
menos caminata y menor cantidad de transbordos.
```

---

## 22. Diferenciador del proyecto

El principal diferenciador de **Muévete CB** será combinar:

> **Agente IA + rutas multimodales + predicción + contexto territorial + personalización + explicabilidad.**

El objetivo no es competir con plataformas globales de navegación general, sino desarrollar un **agente especializado en la movilidad de Ciudad Bolívar**, capaz de utilizar información local para producir recomendaciones contextualizadas.

---

## 23. Frase conceptual

> **Muévete CB: una IA que no solo encuentra el camino, sino que entiende cómo, cuándo y por qué conviene recorrerlo.**
