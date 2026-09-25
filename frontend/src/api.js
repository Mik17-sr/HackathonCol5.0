const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8002'

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  })

  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `La API respondio con ${response.status}`)
  }

  return response.json()
}

export function calcularRuta(origen, destino, limiteDatos = 100) {
  if (![origen, destino].every((point) => point && Number.isFinite(Number(point.lat)) && Number.isFinite(Number(point.lng)))) {
    return Promise.reject(new Error('El origen y el destino deben tener coordenadas válidas.'))
  }
  return request('/api/v1/rutas/calcular', {
    method: 'POST',
    body: JSON.stringify({ origen, destino, limite_datos: limiteDatos }),
  })
}

export function consultarEstadoFuentes() {
  return request('/api/v1/fuentes/estado')
}

export function recomendarRuta(mensaje, locations = {}) {
  return request('/api/v1/chat/recomendar', {
    method: 'POST',
    body: JSON.stringify({
      usuario_id: 'frontend-local',
      mensaje,
      contexto: {
        ubicacion_actual: locations.origin || { lat: 4.5684, lng: -74.1502 },
        hora_consulta: new Date().toISOString(),
        ...(locations.destination ? { destino: locations.destination } : {}),
      },
    }),
  })
}

export function cargarMapa() {
  return Promise.all([
    request('/api/v1/paradas?limit=100'),
    request('/api/v1/estaciones?limit=100'),
  ]).then(([stops, stations]) => ({
    stops: stops.data || [],
    stations: stations.data || [],
  }))
}

export function cargarRutasMapa() {
  return request('/api/v1/rutas/zonales').then((response) => (response.data || []).map((route) => ({
    ...route,
    paths: (route.paths || []).map((path) => path
      .map((point) => Array.isArray(point) ? point : String(point).split(/\s+/).map(Number))
      .filter((point) => point.length >= 2 && point.every(Number.isFinite))
      .map(([lat, lng]) => [Number(lat), Number(lng)])),
  })))
}

export async function buscarDireccion(query) {
  const params = new URLSearchParams({ format: 'jsonv2', q: `${query}, Bogotá, Colombia`, limit: '1' })
  const response = await fetch(`https://nominatim.openstreetmap.org/search?${params}`)
  if (!response.ok) throw new Error('No se pudo buscar la dirección')
  const results = await response.json()
  if (!results.length) throw new Error('No encontramos esa dirección')
  return { lat: Number(results[0].lat), lng: Number(results[0].lon), label: results[0].display_name }
}

export function cargarGoogleMapsPlaces() {
  const apiKey = import.meta.env.VITE_GOOGLE_MAPS_API_KEY
  if (!apiKey) return Promise.reject(new Error('Google Maps no está configurado'))
  if (window.google?.maps?.places) return Promise.resolve(window.google)

  return new Promise((resolve, reject) => {
    const existingScript = document.querySelector('script[data-google-maps="places"]')
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(window.google), { once: true })
      existingScript.addEventListener('error', () => reject(new Error('No se pudo cargar Google Maps')), { once: true })
      return
    }
    const script = document.createElement('script')
    script.dataset.googleMaps = 'places'
    script.src = `https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&libraries=places&v=weekly`
    script.async = true
    script.defer = true
    script.onload = () => resolve(window.google)
    script.onerror = () => reject(new Error('No se pudo cargar Google Maps'))
    document.head.appendChild(script)
  })
}

export { API_BASE_URL }