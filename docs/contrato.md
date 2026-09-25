# Contrato de API - Muévete CB

## Fuente de datos

Todos los datos de transporte usados por rutas, mapa, horarios, estado de la fuente y cálculo de recorridos provienen exclusivamente de la capa 15 del FeatureServer de planificación SITP de TransMilenio, consultada como GeoJSON con `outSR=4326` y filtrada a Ciudad Bolívar (`loc_orig = 19 OR loc_dest = 19`). No se combinan fuentes CKAN, GTFS ni datasets alternos. Las estaciones independientes no forman parte de esa capa y se devuelven como colección vacía.

## 0. Contexto y Alcance (Fases Iniciales)

*IMPORTANTE PARA EL EQUIPO:* 
Este documento define la estructura de comunicación (JSON) estricta *únicamente para las primeras etapas del desarrollo (Fase MVP)*. 

El objetivo de este contrato es *desbloquear el trabajo en paralelo*. Al tener esta estructura acordada desde el día uno:
* El *Frontend* no tiene que esperar a que el backend o la IA funcionen para empezar a diseñar la interfaz y el mapa.
* El *Backend* no tiene que esperar al algoritmo matemático del motor de rutas para empezar a probar sus prompts con el LLM.
* El *Motor de Rutas* sabe exactamente qué formato de salida debe construir al final de sus cálculos con grafos.

*Evolución futura:* 
A medida que el proyecto avance hacia fases superiores, esta estructura JSON evolucionará. En el futuro se añadirán nodos dinámicos como alertas_en_tiempo_real, clima, o rutas_dinamicas_por_incidentes, pero *para las primeras semanas de código, esta será la única y absoluta fuente de verdad*.

---

## 1. Flujo Principal: Solicitar una Ruta al Agente

*Endpoint:* POST /api/v1/chat/recomendar
*Descripción:* Envía el mensaje natural del usuario y su contexto (ubicación, hora) y recibe la respuesta del LLM junto con las alternativas de rutas estructuradas.

### 1.1 Formato de Petición (Request)

Lo que el *Frontend* le envía al *Backend* cuando el usuario presiona "Enviar" en el chat.

```json
{
  "usuario_id": "user_123",
  "mensaje": "Mañana tengo clase a las 7:00 a.m. en la Universidad Distrital. Estoy en Vista Hermosa, quiero llegar 10 minutos antes y caminar lo menos posible.",
  "contexto": {
    "ubicacion_actual": {
      "lat": 4.5684,
      "lng": -74.1502
    },
    "hora_consulta": "2026-09-24T13:00:00Z"
  }
}