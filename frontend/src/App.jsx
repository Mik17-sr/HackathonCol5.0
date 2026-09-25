import { useEffect, useRef, useState } from 'react'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'
import { useDarkMode } from './useDarkMode'
import { buscarDireccion, calcularRuta, cargarGoogleMapsPlaces, cargarMapa, recomendarRuta } from './api'

const savedPlaces = [
  { icon: '⌂', name: 'Casa', address: 'Vista Hermosa, Bogotá', tone: 'lime' },
  { icon: '✦', name: 'Universidad Distrital', address: 'Carrera 7 #40-62', tone: 'gold' },
  { icon: '⌁', name: 'Oficina', address: 'Chapinero, Bogotá', tone: 'sky' },
]

const favoriteRoutes = [
  { id: 'morning-route', name: 'Casa → Universidad', origin: 'Vista Hermosa', destination: 'Universidad Distrital', fromCurrent: 38, totalTime: 38, startedAt: Date.now() - 21 * 60000, startLabel: '06:12', tone: 'lime', icon: '↗' },
  { id: 'office-route', name: 'Casa → Oficina', origin: 'Vista Hermosa', destination: 'Chapinero', fromCurrent: 52, totalTime: 52, startedAt: Date.now() - 8 * 60000, startLabel: '06:25', tone: 'sky', icon: '◒' },
  { id: 'return-route', name: 'Universidad → Casa', origin: 'Universidad Distrital', destination: 'Vista Hermosa', fromCurrent: 41, totalTime: 41, startedAt: Date.now() - 34 * 60000, startLabel: '17:40', tone: 'violet', icon: '←' },
]

const routeHistory = [
  { id: 'history-1', date: 'Hoy, 06:12', route: 'Vista Hermosa → Universidad Distrital', duration: '38 min', distance: '6.4 km', tone: 'lime' },
  { id: 'history-2', date: 'Ayer, 17:40', route: 'Universidad Distrital → Vista Hermosa', duration: '42 min', distance: '7.1 km', tone: 'sky' },
  { id: 'history-3', date: 'Lun, 07:03', route: 'Vista Hermosa → Chapinero', duration: '51 min', distance: '8.8 km', tone: 'violet' },
]

const incidents = [
  { id: 1, type: 'Accidente', title: 'Colisión en Av. Boyacá', location: 'Carrera 70 con Calle 65 Sur', time: 'Hace 8 min', status: 'active', impact: 'Alto', color: 'coral' },
  { id: 2, type: 'Congestión', title: 'Tráfico lento en Autopista Sur', location: 'Entre Venecia y Sevillana', time: 'Hace 19 min', status: 'active', impact: 'Medio', color: 'gold' },
  { id: 3, type: 'Incidente resuelto', title: 'Vehículo detenido en Portal Tunal', location: 'Carrera 24 con Calle 47 Sur', time: 'Resuelto hace 12 min', status: 'resolved', impact: 'Bajo', color: 'teal' },
]

const localNews = [
  { id: 'news-cable', category: 'Transporte', tone: 'transport', title: 'TransMiCable amplía su operación en Ciudad Bolívar', description: 'La conexión entre El Tunal y Mirador del Paraíso tendrá más frecuencia en las horas de mayor movimiento.', date: 'Hace 18 min', readTime: '2 min de lectura', image: 'https://images.unsplash.com/photo-1544620347-c4fd4a3d5957?auto=format&fit=crop&w=1000&q=85' },
  { id: 'news-road', category: 'Movilidad', tone: 'mobility', title: 'Nuevo plan de movilidad para la Avenida Boyacá', description: 'Conoce los cambios temporales, desvíos y recomendaciones para moverte por el sur de Bogotá.', date: 'Hoy, 08:40', readTime: '3 min de lectura', image: 'https://images.unsplash.com/photo-1519501025264-65ba15a82390?auto=format&fit=crop&w=1000&q=85' },
  { id: 'news-community', category: 'Comunidad', tone: 'community', title: 'Barrios se unen para mejorar sus rutas seguras', description: 'Vecinos de Arborizadora y San Francisco comparten puntos de encuentro para caminar acompañados.', date: 'Ayer, 16:20', readTime: '4 min de lectura', image: 'https://images.unsplash.com/photo-1529156069898-49953e39b3ac?auto=format&fit=crop&w=1000&q=85' },
  { id: 'news-culture', category: 'Cultura', tone: 'culture', title: 'Agenda local: música y encuentros al aire libre', description: 'Este fin de semana hay actividades gratuitas para disfrutar la localidad sin salir de tu barrio.', date: 'Ayer, 11:05', readTime: '2 min de lectura', image: 'https://images.unsplash.com/photo-1501386761578-eac5c94b800a?auto=format&fit=crop&w=1000&q=85' },
]

const initialBusSchedules = [
  { id: 'schedule-morning', route: 'TransMiCable + B14', origin: 'Portal El Tunal', destination: 'Universidad Distrital', departure: '06:12', arrival: '06:50', reminder: 10, tone: 'lime' },
  { id: 'schedule-office', route: 'SITP 6-4 + TransMi', origin: 'Vista Hermosa', destination: 'Chapinero', departure: '07:05', arrival: '07:57', reminder: 15, tone: 'sky' },
]

function toVisualRoute(route, index = 0, serviceGroups = []) {
  const serviceLegs = (route.legs || []).filter((leg) => leg.modo !== 'caminata')
  const services = [...new Set(serviceLegs.map((leg) => leg.route_id).filter(Boolean))]
  const transfers = Math.max(
    Number.isFinite(Number(route.transfers)) ? Number(route.transfers) : 0,
    Math.max(0, services.length - 1),
  )
  return {
    id: `api-route-${index}`,
    label: index === 0 ? 'Ruta recomendada' : `Alternativa ${index}`,
    title: services.length ? services.join(' + ') : 'Trayecto a pie',
    services,
    serviceGroups,
    time: `${route.total_time} min`,
    detail: `${services.length ? `Bus ${services.join(' + ')} · ` : ''}${transfers} transbordos · ${Number(route.walking || 0).toFixed(1)} km caminando`,
    tone: 'lime',
    icon: services.length ? '🚌' : '🚶',
    incidence: Math.round((1 - Number(route.reliability || 0)) * 100),
    coordinates: (route.coordinates || []).map((point) => [point.lat, point.lng]),
  }
}

function hasCoordinates(point) {
  return point && Number.isFinite(Number(point.lat)) && Number.isFinite(Number(point.lng))
}

function App() {
  const [selectedRoute, setSelectedRoute] = useState(null)
  const [tripOrigin, setTripOrigin] = useState(null)
  const [tripDestination, setTripDestination] = useState(null)
  const [activeView, setActiveView] = useState('planificar')
  const [isSettingsOpen, setIsSettingsOpen] = useState(false)
  const [isAssistantOpen, setIsAssistantOpen] = useState(false)
  const [isPreferencesOpen, setIsPreferencesOpen] = useState(false)
  const [travelPreferences, setTravelPreferences] = useState({ priority: 'time', routeMode: 'any', accessibility: false, avoidIncidents: true, fewerTransfers: false })
  const [busSchedules, setBusSchedules] = useState(initialBusSchedules)
  const [scheduleNotice, setScheduleNotice] = useState('')
  const { isDark, toggleTheme } = useDarkMode()

  useEffect(() => {
    const checkSchedules = () => {
      const current = new Date()
      const currentMinutes = current.getHours() * 60 + current.getMinutes()
      const upcoming = busSchedules.find((schedule) => {
        const [hours, minutes] = schedule.departure.split(':').map(Number)
        const departureMinutes = hours * 60 + minutes
        return departureMinutes - currentMinutes === schedule.reminder
      })
      if (!upcoming) return
      setScheduleNotice(`Tu ruta ${upcoming.route} sale en ${upcoming.reminder} minutos.`)
      if ('Notification' in window && Notification.permission === 'granted') new Notification('Muévete CB · Próxima salida', { body: `Tu bus hacia ${upcoming.destination} sale a las ${upcoming.departure}.` })
    }
    const timer = window.setInterval(checkSchedules, 60000)
    return () => window.clearInterval(timer)
  }, [busSchedules])

  function navigateTo(view) {
    setActiveView(view)
    setIsSettingsOpen(false)
  }

  return (
    <main className="app-shell transition-colors duration-300 ease-out">
      <header className="topbar transition-colors duration-300 ease-out">
        <button className="brand transition-transform duration-300 ease-out hover:scale-[1.03]" type="button" onClick={() => navigateTo('planificar')} aria-label="Muévete CB, inicio">
          <span className="brand-mark">m</span>
          <span>muévete<span>CB</span></span>
        </button>
        <nav className="main-nav" aria-label="Navegación principal">
          <button className={`transition-colors duration-300 ${activeView === 'planificar' ? 'active' : ''}`} type="button" onClick={() => navigateTo('planificar')}>Planificar</button>
          <button className={`transition-colors duration-300 ${activeView === 'explorar' ? 'active' : ''}`} type="button" onClick={() => navigateTo('explorar')}>Explorar ciudad</button>
          <button className={`transition-colors duration-300 ${activeView === 'guardados' ? 'active' : ''}`} type="button" onClick={() => navigateTo('guardados')}>Guardados</button>
          <button className="nav-preferences transition-all duration-300 hover:-translate-y-0.5" type="button" onClick={() => setIsPreferencesOpen(true)}><span>⚙</span> Preferencias</button>
        </nav>
        <div className="topbar-tools">
          <button className="round-button transition-transform duration-300 ease-out hover:scale-110" type="button" aria-label="Notificaciones">♢<i /></button>
          <button className="profile transition-transform duration-300 ease-out hover:scale-[1.03]" type="button" onClick={() => setIsSettingsOpen(true)} aria-label="Abrir ajustes"><span>LM</span><small>Laura M.</small><b>⌄</b></button>
        </div>
      </header>

      <div key={activeView} className="screen-transition animate-in fade-in slide-in-from-bottom-2 duration-500 ease-out">
        {activeView === 'planificar' && <PlannerView origin={tripOrigin} destination={tripDestination} setOrigin={setTripOrigin} setDestination={setTripDestination} selectedRoute={selectedRoute} setSelectedRoute={setSelectedRoute} busSchedules={busSchedules} setBusSchedules={setBusSchedules} onScheduleNotice={setScheduleNotice} travelPreferences={travelPreferences} setTravelPreferences={setTravelPreferences} onOpenPreferences={() => setIsPreferencesOpen(true)} />}
        {activeView === 'explorar' && <ExploreView onPlan={() => navigateTo('planificar')} />}
        {activeView === 'guardados' && <SavedView onPlan={() => navigateTo('planificar')} />}
      </div>

      <footer><span><b>muéveteCB</b> · Bogotá en movimiento</span><span>Hecho para moverte mejor <strong>✦</strong></span></footer>

      <LocalTravelAssistant activeView={activeView} origin={tripOrigin} destination={tripDestination} isOpen={isAssistantOpen} onToggle={() => setIsAssistantOpen((current) => !current)} />
      {scheduleNotice && <div className="schedule-toast" role="status"><span>◷</span><div><strong>Recordatorio de viaje</strong><small>{scheduleNotice}</small></div><button type="button" onClick={() => setScheduleNotice('')} aria-label="Cerrar recordatorio">×</button></div>}
      {isPreferencesOpen && <TravelPreferencesModal preferences={travelPreferences} setPreferences={setTravelPreferences} onClose={() => setIsPreferencesOpen(false)} />}
      {isSettingsOpen && <SettingsPanel isDark={isDark} toggleTheme={toggleTheme} onClose={() => setIsSettingsOpen(false)} />}
    </main>
  )
}

function GoogleLocationInput({ value, onChange, onLocation, placeholder, ariaLabel }) {
  const inputRef = useRef(null)

  useEffect(() => {
    let autocomplete
    let listener
    cargarGoogleMapsPlaces().then((google) => {
      if (!inputRef.current) return
      autocomplete = new google.maps.places.Autocomplete(inputRef.current, {
        componentRestrictions: { country: 'co' },
        fields: ['formatted_address', 'geometry', 'name'],
      })
      listener = autocomplete.addListener('place_changed', () => {
        const place = autocomplete.getPlace()
        const location = place.geometry?.location
        if (!location) return
        onLocation({
          lat: location.lat(),
          lng: location.lng(),
          label: place.formatted_address || place.name || `${location.lat()}, ${location.lng()}`,
        })
      })
    }).catch(() => {})
    return () => listener?.remove()
  }, [onLocation])

  return <input ref={inputRef} value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} aria-label={ariaLabel} />
}

function PlannerView({ origin, destination, setOrigin, setDestination, selectedRoute, setSelectedRoute, busSchedules, setBusSchedules, onScheduleNotice, travelPreferences, setTravelPreferences, onOpenPreferences }) {
  const [locationMode, setLocationMode] = useState('destination')
  const [originQuery, setOriginQuery] = useState('')
  const [destinationQuery, setDestinationQuery] = useState('')
  const [routeResult, setRouteResult] = useState(null)
  const [isLoadingRoute, setIsLoadingRoute] = useState(false)
  const [routeError, setRouteError] = useState('')

  function useCurrentLocation() {
    if (!navigator.geolocation) {
      setRouteError('Este navegador no permite obtener tu ubicación.')
      return
    }
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        const point = { lat: coords.latitude, lng: coords.longitude, label: 'Mi ubicación' }
        setOrigin(point)
        if (destination) showRoutes(point, destination)
        setRouteError('')
      },
      () => setRouteError('No pudimos obtener tu ubicación. Revisa los permisos del navegador.'),
      { enableHighAccuracy: true, timeout: 10000 },
    )
  }

  async function searchLocation(query, target) {
    if (!query.trim()) return
    try {
      const location = await buscarDireccion(query)
      const nextOrigin = target === 'origin' ? location : origin
      const nextDestination = target === 'destination' ? location : destination
      if (target === 'origin') setOrigin(location)
      else setDestination(location)
      setRouteError('')
      if (nextOrigin && nextDestination) showRoutes(nextOrigin, nextDestination)
    } catch (error) {
      setRouteError(error.message)
    }
  }

  async function showRoutes(originPoint = origin, destinationPoint = destination) {
    if (!hasCoordinates(originPoint) || !hasCoordinates(destinationPoint)) {
      setRouteError('Selecciona un origen y un destino con coordenadas válidas.')
      return
    }
    setIsLoadingRoute(true)
    setRouteError('')
    try {
      const result = await calcularRuta(
        { lat: Number(originPoint.lat), lng: Number(originPoint.lng) },
        { lat: Number(destinationPoint.lat), lng: Number(destinationPoint.lng) },
      )
      setRouteResult(result)
      setSelectedRoute(toVisualRoute(result.ruta, 0, result.grupos_servicios || []))
    } catch (error) {
      setRouteError(error.message || 'No pudimos calcular la ruta. Revisa que el backend este activo.')
    } finally {
      setIsLoadingRoute(false)
    }
  }

  useEffect(() => {
    cargarMapa().then(({ stops }) => {
      const availableOrigin = stops.find((stop) => stop.nombre === 'Vista Hermosa') || stops[0]
      const availableDestinations = stops.filter((stop) => stop.id !== availableOrigin?.id)
      setOrigin(availableOrigin || null)
      setDestination(availableDestinations[0] || null)
    }).catch(() => setRouteError('No pudimos cargar los destinos del backend.'))
  }, [setDestination, setOrigin])

  const displayedRoutes = routeResult
    ? (routeResult.alternativas || [routeResult.ruta]).slice(0, 3).map((route, index) => toVisualRoute(route, index, routeResult.grupos_servicios || []))
    : []
  const routeTime = routeResult ? `${routeResult.ruta.total_time} min` : 'Calculando...'

  return (
    <section className="dashboard" id="planificar">
      <aside className="control-panel transition-colors duration-300 ease-out">
        <div className="panel-intro"><div className="eyebrow"><i /> Asistente de movilidad</div><h1>Muévete a<br /><em>tu manera.</em></h1><p>Diseña tu recorrido ideal por Bogotá, sin complicaciones.</p></div>
        <div className="journey-card transition-all duration-300 ease-out hover:-translate-y-1 hover:shadow-xl">
          <div className="field-block location-field"><span className="field-icon origin">●</span><div><label>Desde</label><GoogleLocationInput value={originQuery || origin?.label || origin?.nombre || ''} onChange={setOriginQuery} onLocation={(point) => { setOrigin(point); setOriginQuery(point.label) }} placeholder="Buscar origen" ariaLabel="Buscar origen con Google Maps" /></div><button type="button" aria-label="Usar mi ubicación" onClick={useCurrentLocation}>⌖</button></div>
          <div className="field-connector"><span /></div>
          <div className="field-block destination-field location-field"><span className="field-icon destination">◆</span><div><label>Hasta</label><GoogleLocationInput value={destinationQuery || destination?.label || destination?.nombre || ''} onChange={setDestinationQuery} onLocation={(point) => { setDestination(point); setDestinationQuery(point.label) }} placeholder="Buscar destino" ariaLabel="Buscar destino con Google Maps" /></div><button type="button" aria-label="Buscar dirección" onClick={() => searchLocation(destinationQuery, 'destination')}>⌕</button></div>
          <div className="journey-divider" /><div className="journey-options"><button className="transition-colors duration-300 hover:border-lime-300" type="button">Ahora <b>⌄</b></button><button className="transition-colors duration-300 hover:border-lime-300" type="button" onClick={onOpenPreferences}>Preferencias <b>⚙</b></button></div><label className="route-mode-menu">Tipo de recorrido<select value={travelPreferences.routeMode} onChange={(event) => setTravelPreferences((current) => ({ ...current, routeMode: event.target.value }))}><option value="any">Cualquier combinación</option><option value="single">Solo un bus</option><option value="multiple">Varios buses</option><option value="nearest">Estación TransMilenio más cercana</option></select></label><button className="primary-button transition-all duration-300 ease-out hover:-translate-y-0.5" type="button" onClick={showRoutes} disabled={isLoadingRoute}>{isLoadingRoute ? 'Calculando...' : 'Mostrar rutas'} <span>→</span></button>{routeError && <small className="route-error" role="alert">{routeError}</small>}
        </div>
        <div className="preference-summary"><span>⚙</span><div><small>Preferencias del viaje</small><strong>{travelPreferences.routeMode === 'single' ? 'Solo un bus' : travelPreferences.routeMode === 'multiple' ? 'Varios buses' : travelPreferences.routeMode === 'nearest' ? 'Estación TransMilenio más cercana' : travelPreferences.priority === 'time' ? 'Llegar más rápido' : travelPreferences.priority === 'walk' ? 'Caminar menos' : 'Menos transbordos'}</strong></div><button type="button" onClick={onOpenPreferences}>Editar</button></div>
        <BusScheduleModule schedules={busSchedules} setSchedules={setBusSchedules} onScheduleNotice={onScheduleNotice} />
        <div className="saved-place"><span className="saved-icon">✦</span><div><small>Próximo destino</small><strong>Universidad Distrital</strong></div><button type="button" aria-label="Abrir destino guardado">→</button></div>
        <div className="panel-footer"><span><i /> Red conectada</span><button type="button">Ayuda <b>↗</b></button></div>
      </aside>
      <section className="map-content" aria-label="Explorador de rutas">
        <div className="map-header"><div><span className="eyebrow">Jueves, 24 de septiembre</span><h2>Buenos días, Laura <span>✦</span></h2></div><button className="filter-button" type="button">☷ <span>Filtros</span></button></div>
        <MapStage routeResult={routeResult} selectedRoute={selectedRoute} origin={origin} destination={destination} locationMode={locationMode} onLocationModeChange={setLocationMode} onPickLocation={(point) => { const nextOrigin = locationMode === 'origin' ? point : origin; const nextDestination = locationMode === 'destination' ? point : destination; if (locationMode === 'origin') setOrigin(point); else setDestination(point); if (nextOrigin && nextDestination) showRoutes(nextOrigin, nextDestination) }} onSelectRoute={setSelectedRoute} />
        <div className="route-summary"><div><span className="eyebrow">Tu mejor opción</span><h3>{routeResult ? 'Ruta calculada para ti' : 'Una ruta que se adapta a ti'}</h3></div><span className="route-summary-meta">Llegada <strong>{routeResult ? 'calculada' : '06:50'}</strong> <i /> {routeTime}</span></div>
        <div className="route-grid">{displayedRoutes.map((route) => <RouteCard key={route.id} route={route} selected={selectedRoute?.id === route.id} onSelect={setSelectedRoute} />)}</div>
        <AccidentsModule selectedRoute={selectedRoute} />
      </section>
    </section>
  )
}

function TravelPreferencesModal({ preferences, setPreferences, onClose }) {
  function updatePreference(key, value) {
    setPreferences((current) => ({ ...current, [key]: value }))
  }

  return <div className="travel-preferences-backdrop animate-in fade-in duration-300" role="presentation" onMouseDown={onClose}><section className="travel-preferences-modal animate-in slide-in-from-bottom-4 zoom-in-95 duration-300" role="dialog" aria-modal="true" aria-labelledby="travel-preferences-title" onMouseDown={(event) => event.stopPropagation()}><header><div><span className="eyebrow"><i /> Personaliza este viaje</span><h2 id="travel-preferences-title">¿Cómo quieres llegar?</h2><p>Usaremos tus preferencias para ordenar las rutas disponibles.</p></div><button type="button" onClick={onClose} aria-label="Cerrar preferencias">×</button></header><div className="preference-section"><span className="preference-label">Quiero priorizar</span><div className="priority-grid">{[['time', '◷', 'Llegar más rápido', 'Menor duración'], ['walk', '⌁', 'Caminar menos', 'Más cerca de paradas'], ['transfers', '↗', 'Menos transbordos', 'Trayecto simple']].map(([value, icon, title, detail]) => <button className={preferences.priority === value ? 'selected' : ''} key={value} type="button" onClick={() => updatePreference('priority', value)}><span>{icon}</span><strong>{title}</strong><small>{detail}</small></button>)}</div></div><div className="preference-section"><span className="preference-label">También considerar</span><label className="preference-toggle"><span className="toggle-icon">♿</span><span><strong>Ruta accesible</strong><small>Evitar escaleras y priorizar accesos cómodos</small></span><input type="checkbox" checked={preferences.accessibility} onChange={(event) => updatePreference('accessibility', event.target.checked)} /><i /></label><label className="preference-toggle"><span className="toggle-icon">!</span><span><strong>Evitar incidentes</strong><small>Reducir exposición a zonas con accidentes</small></span><input type="checkbox" checked={preferences.avoidIncidents} onChange={(event) => updatePreference('avoidIncidents', event.target.checked)} /><i /></label><label className="preference-toggle"><span className="toggle-icon">⇄</span><span><strong>Menos cambios</strong><small>Preferir recorridos con menos conexiones</small></span><input type="checkbox" checked={preferences.fewerTransfers} onChange={(event) => updatePreference('fewerTransfers', event.target.checked)} /><i /></label></div><div className="preference-footer"><span>✦ Perfil aplicado a este viaje</span><button className="primary-button" type="button" onClick={onClose}>Aplicar preferencias <b>→</b></button></div></section></div>
}

function BusScheduleModule({ schedules, setSchedules, onScheduleNotice }) {
  const [isAdding, setIsAdding] = useState(false)
  const [form, setForm] = useState({ route: '', origin: 'Vista Hermosa', destination: '', departure: '', arrival: '', reminder: '10' })
  const nextSchedule = schedules[0]

  function updateForm(event) {
    setForm((current) => ({ ...current, [event.target.name]: event.target.value }))
  }

  async function requestNotifications() {
    if ('Notification' in window && Notification.permission === 'default') await Notification.requestPermission()
  }

  function addSchedule(event) {
    event.preventDefault()
    if (!form.route || !form.destination || !form.departure || !form.arrival) return
    const newSchedule = { ...form, id: `schedule-${Date.now()}`, reminder: Number(form.reminder), tone: 'violet' }
    setSchedules((current) => [...current, newSchedule])
    onScheduleNotice(`Horario guardado. Te avisaremos ${newSchedule.reminder} minutos antes de la salida.`)
    requestNotifications()
    setForm({ route: '', origin: 'Vista Hermosa', destination: '', departure: '', arrival: '', reminder: '10' })
    setIsAdding(false)
  }

  return <section className="bus-schedule-module" aria-label="Calendario de salidas de buses"><div className="schedule-module-heading"><div><span className="eyebrow"><i /> Agenda de viaje</span><h3>Mis salidas</h3></div><button className="schedule-add-button" type="button" onClick={() => setIsAdding((current) => !current)} aria-expanded={isAdding}>{isAdding ? '×' : '+'} <span>{isAdding ? 'Cerrar' : 'Registrar horario'}</span></button></div><div className="next-departure"><span className="next-icon">◷</span><div><small>Próxima salida</small><strong>{nextSchedule.route}</strong><span>{nextSchedule.origin} → {nextSchedule.destination}</span></div><b>{nextSchedule.departure}</b></div>{isAdding && <form className="schedule-form animate-in slide-in-from-top-2 fade-in duration-300" onSubmit={addSchedule}><div className="schedule-form-title"><strong>Nuevo horario</strong><small>Recibe un aviso antes de salir</small></div><label>Ruta<input name="route" value={form.route} onChange={updateForm} placeholder="Ej. B14 + TransMiCable" /></label><div className="schedule-form-row"><label>Origen<input name="origin" value={form.origin} onChange={updateForm} /></label><label>Destino<input name="destination" value={form.destination} onChange={updateForm} placeholder="Universidad Distrital" /></label></div><div className="schedule-form-row"><label>Salida<input name="departure" type="time" value={form.departure} onChange={updateForm} /></label><label>Llegada<input name="arrival" type="time" value={form.arrival} onChange={updateForm} /></label><label>Avisar<select name="reminder" value={form.reminder} onChange={updateForm}><option value="5">5 min</option><option value="10">10 min</option><option value="15">15 min</option></select></label></div><button className="primary-button" type="submit">Guardar horario <span>→</span></button></form>}<div className="schedule-list">{schedules.map((schedule) => <article className="schedule-row" key={schedule.id}><span className={`schedule-route-dot ${schedule.tone}`} /><div><strong>{schedule.route}</strong><small>{schedule.origin} → {schedule.destination}</small></div><span className="schedule-times"><b>{schedule.departure}</b><small>llega {schedule.arrival}</small></span><button type="button" onClick={() => setSchedules((current) => current.filter((item) => item.id !== schedule.id))} aria-label={`Eliminar horario ${schedule.route}`}>×</button></article>)}</div><small className="notification-hint">◷ Avisos locales activos · {schedules.length} horarios registrados</small></section>
}

function MapStage({ routeResult, selectedRoute, origin, destination, locationMode, onLocationModeChange, onPickLocation, onSelectRoute }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const locationsLayerRef = useRef(null)
  const calculatedRouteLayerRef = useRef(null)
  const onPickLocationRef = useRef(onPickLocation)
  const onSelectRouteRef = useRef(onSelectRoute)
  const [mapStatus, setMapStatus] = useState('Cargando mapa...')

  useEffect(() => {
    onPickLocationRef.current = onPickLocation
    onSelectRouteRef.current = onSelectRoute
  }, [onPickLocation, onSelectRoute])

  useEffect(() => {
    if (!containerRef.current) return undefined
    const map = L.map(containerRef.current, { zoomControl: false }).setView([4.5684, -74.1502], 13)
    mapRef.current = map
    map.on('click', (event) => onPickLocationRef.current({ lat: event.latlng.lat, lng: event.latlng.lng, label: `${event.latlng.lat.toFixed(5)}, ${event.latlng.lng.toFixed(5)}` }))
    const streets = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { attribution: '&copy; OpenStreetMap' })
    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: 'Tiles &copy; Esri' })
    streets.addTo(map)
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    const stopsLayer = L.layerGroup().addTo(map)
    const stationsLayer = L.layerGroup().addTo(map)
    const calculatedRouteLayer = L.layerGroup().addTo(map)
    locationsLayerRef.current = L.layerGroup().addTo(map)
    calculatedRouteLayerRef.current = calculatedRouteLayer
    L.control.layers({ Calles: streets, Satélite: satellite }, { Paraderos: stopsLayer, Estaciones: stationsLayer }, { position: 'topright' }).addTo(map)

    cargarMapa().then(({ stops, stations }) => {
      const bounds = []
      stops.forEach((stop) => {
        const point = [stop.lat, stop.lng]
        bounds.push(point)
        L.circleMarker(point, { radius: 4, color: '#4d7d42', fillColor: '#b9ee68', fillOpacity: .9, weight: 1 })
          .bindPopup(`<strong>${stop.nombre}</strong><br>${stop.codigo || 'Paradero SITP'}<br>${stop.localidad || 'Bogotá'}`)
          .addTo(stopsLayer)
      })
      stations.forEach((station) => {
        const point = [station.lat, station.lng]
        bounds.push(point)
        L.circleMarker(point, { radius: 7, color: '#287b78', fillColor: '#8edbd2', fillOpacity: .95, weight: 2 })
          .bindPopup(`<strong>${station.nombre}</strong><br>${station.codigo || 'Estación'}<br>${station.estado}`)
          .addTo(stationsLayer)
      })
      if (bounds.length) map.fitBounds(bounds, { padding: [20, 20], maxZoom: 14 })
      setMapStatus(`${stops.length} paraderos · ${stations.length} estaciones`)
    }).catch(() => setMapStatus('Mapa disponible; paraderos no disponibles'))

    return () => map.remove()
  }, [])

  useEffect(() => {
    if (!mapRef.current || !locationsLayerRef.current || !calculatedRouteLayerRef.current) return
    locationsLayerRef.current.clearLayers()
    calculatedRouteLayerRef.current.clearLayers()
    if (hasCoordinates(origin)) {
      L.marker([Number(origin.lat), Number(origin.lng)])
        .bindTooltip('Origen', { permanent: true, direction: 'top' })
        .addTo(locationsLayerRef.current)
    }
    if (hasCoordinates(destination)) {
      L.marker([Number(destination.lat), Number(destination.lng)])
        .bindTooltip('Destino', { permanent: true, direction: 'top' })
        .addTo(locationsLayerRef.current)
    }
    const calculatedCoordinates = selectedRoute?.coordinates || []
    if (calculatedCoordinates.length >= 2) {
      const calculatedLine = L.polyline(calculatedCoordinates, { color: '#ef8d55', weight: 6, opacity: .95 })
        .bindTooltip(selectedRoute.title, { sticky: true })
        .addTo(calculatedRouteLayerRef.current)
      mapRef.current.fitBounds(calculatedLine.getBounds(), { padding: [36, 36], maxZoom: 14 })
    }
  }, [origin, destination, selectedRoute, routeResult])

  return <div className="map-stage real-map-stage"><div className="map-location-tools" role="group" aria-label="Elegir punto en el mapa" onClick={(event) => event.stopPropagation()}><span>Elegir en mapa:</span><button className={locationMode === 'origin' ? 'active' : ''} type="button" onClick={() => onLocationModeChange('origin')}>Origen</button><button className={locationMode === 'destination' ? 'active' : ''} type="button" onClick={() => onLocationModeChange('destination')}>Destino</button></div><div ref={containerRef} className="real-map" aria-label="Mapa de tu recorrido y puntos de referencia" /><span className="real-map-status">{mapStatus}</span></div>
}

function RouteCard({ route, selected, onSelect }) {
  const options = route.serviceGroups?.flatMap((group) => group.opciones || []) || []
  return <button className={`group route-card transition-all duration-300 ease-out hover:-translate-y-1 ${selected ? 'selected' : ''}`} type="button" onClick={() => onSelect(route)}><span className={`route-symbol transition-transform duration-300 group-hover:scale-110 ${route.tone}`}>{route.icon}</span><span className="route-info"><span className="route-label">{route.label}</span><strong>{route.title}</strong><span className="route-services">{route.services.length ? route.services.map((service) => <b key={service}>🚌 {service}</b>) : <b>🚶 Caminata</b>}</span><small>{route.detail}</small>{options.length > 1 && <small className="route-options-note">Puedes tomar cualquiera: {options.join(' / ')}</small>}</span><span className="route-time">{route.time}<b>›</b></span><span className="route-incidence"><i style={{ '--incidence': `${route.incidence * 2}%` }} />{route.incidence}% incidencia</span></button>
}

function AccidentsModule({ selectedRoute }) {
  const route = selectedRoute || { title: 'Sin ruta seleccionada', incidence: 0 }
  const [filter, setFilter] = useState('all')
  const [selectedIncident, setSelectedIncident] = useState(incidents[0])
  const filteredIncidents = filter === 'all' ? incidents : incidents.filter((incident) => incident.status === filter)

  return <section className="accidents-module" aria-label="Incidentes de Ciudad Bolívar"><div className="accidents-heading"><div><span className="eyebrow"><i /> Ciudad Bolívar · En vivo</span><h3>Incidentes en tu ruta</h3><p>Monitorea eventos que pueden cambiar tu recorrido.</p></div><span className="live-indicator"><i /> Actualizado ahora</span></div><div className="incidents-layout"><div className="incident-list"><div className="incident-tabs">{[['all', 'Todos'], ['active', 'Activos'], ['resolved', 'Resueltos']].map(([value, label]) => <button className={filter === value ? 'active' : ''} key={value} type="button" onClick={() => setFilter(value)}>{label}<b>{value === 'all' ? incidents.length : incidents.filter((incident) => incident.status === value).length}</b></button>)}</div>{filteredIncidents.map((incident) => <button className={`incident-row ${selectedIncident.id === incident.id ? 'selected' : ''}`} key={incident.id} type="button" onClick={() => setSelectedIncident(incident)}><span className={`incident-symbol ${incident.color}`}>{incident.status === 'resolved' ? '✓' : '!'}</span><span className="incident-copy"><strong>{incident.title}</strong><small>{incident.location}</small><em>{incident.time}</em></span><span className={`incident-impact ${incident.impact.toLowerCase()}`}>{incident.impact}</span></button>)}</div><aside className="incidence-card"><div className="incidence-top"><span className="eyebrow">Impacto estimado</span><span className="incidence-state"><i /> {selectedIncident.status === 'active' ? 'Activo' : 'Resuelto'}</span></div><div className="incidence-score"><span className="incidence-ring" style={{ '--score': `${route.incidence * 3.6}deg` }}><b>{route.incidence}%</b></span><div><strong>{route.title}</strong><p>Incidencia asociada a eventos reportados en Ciudad Bolívar.</p></div></div><div className="incidence-bar"><span style={{ width: `${route.incidence * 2}%` }} /></div><div className="incidence-footer"><span>Riesgo en la ruta</span><strong>{route.incidence < 15 ? 'Bajo' : 'Moderado'}</strong></div><div className="selected-incident"><span className={`incident-symbol ${selectedIncident.color}`}>{selectedIncident.status === 'resolved' ? '✓' : '!'}</span><div><small>Evento seleccionado</small><strong>{selectedIncident.title}</strong></div></div></aside></div></section>
}

function ExploreView({ onPlan }) {
  return <section className="secondary-view explore-view transition-colors duration-300 ease-out"><div className="secondary-hero"><span className="eyebrow"><i /> Explora Bogotá</span><h1>La ciudad tiene<br /><em>muchas rutas.</em></h1><p>Descubre lugares, conexiones y planes para moverte con otra perspectiva.</p><button className="primary-button transition-all duration-300 ease-out hover:-translate-y-0.5" type="button" onClick={onPlan}>Planificar un recorrido <span>→</span></button></div><div className="explore-grid"><article className="feature-card feature-large transition-all duration-300 ease-out hover:-translate-y-1"><span className="feature-orbit">✦</span><small>MAPA DE HOY</small><h2>Conoce Bogotá<br />desde otra ruta.</h2><p>Explora conexiones y barrios que quedan cerca de ti.</p><button type="button">Abrir mapa <b>↗</b></button></article><article className="feature-card feature-sun transition-all duration-300 ease-out hover:-translate-y-1"><span>☀</span><small>PLAN IDEAL</small><h3>Una pausa<br />en el camino</h3><p>Encuentra parques, cafés y lugares para hacer más amable tu recorrido.</p></article><article className="feature-card feature-night transition-all duration-300 ease-out hover:-translate-y-1"><span>◒</span><small>CONEXIONES</small><h3>La red que<br />te conecta</h3><p>Visualiza cómo se mueve la ciudad en tiempo real.</p></article></div><LocalNews /></section>
}

function LocalNews() {
  const [activeCategory, setActiveCategory] = useState('Todas')
  const categories = ['Todas', 'Transporte', 'Movilidad', 'Comunidad', 'Cultura']
  const visibleNews = activeCategory === 'Todas' ? localNews : localNews.filter((item) => item.category === activeCategory)

  return <section className="local-news" aria-labelledby="local-news-title"><div className="news-heading"><div><span className="eyebrow"><i /> Actualidad local</span><h2 id="local-news-title">Novedades de Ciudad Bolívar</h2><p>Información útil para moverte, participar y disfrutar tu localidad.</p></div><span className="news-live"><i /> 4 novedades</span></div><div className="news-filters" role="tablist" aria-label="Filtrar novedades">{categories.map((category) => <button className={activeCategory === category ? 'active' : ''} key={category} type="button" onClick={() => setActiveCategory(category)}>{category}</button>)}</div><div className="news-grid">{visibleNews.map((item) => <article className={`news-card news-${item.tone} transition-all duration-300 ease-out hover:-translate-y-1`} key={item.id}><div className="news-image-wrap"><img src={item.image} alt="" loading="lazy" /><span className="news-category">{item.category}</span><button type="button" aria-label={`Guardar noticia: ${item.title}`}>♡</button></div><div className="news-card-body"><div className="news-meta"><span>{item.date}</span><i /> <span>{item.readTime}</span></div><h3>{item.title}</h3><p>{item.description}</p><button className="news-read-more" type="button">Leer novedad <b>↗</b></button></div></article>)}</div></section>
}

function SavedView({ onPlan }) {
  const [now, setNow] = useState(() => Date.now())

  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), 60000)
    return () => window.clearInterval(timer)
  }, [])

  return <section className="secondary-view saved-view transition-colors duration-300 ease-out"><div className="saved-heading"><div><span className="eyebrow"><i /> Tus rutas</span><h1>Todo listo para<br /><em>volver.</em></h1><p>Compara tus recorridos favoritos y mira cuánto tarda cada uno desde tu ubicación actual.</p></div><button className="primary-button compact-button transition-all duration-300 ease-out hover:-translate-y-0.5" type="button" onClick={onPlan}>Nuevo recorrido <span>+</span></button></div><section className="favorite-routes-panel"><div className="favorite-panel-heading"><div><span className="eyebrow">Seguimiento de rutas</span><h2>Favoritas en movimiento</h2></div><span className="clock-badge"><i /> Actualizado {new Date(now).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' })}</span></div><div className="favorite-routes-grid">{favoriteRoutes.map((route) => <FavoriteRouteCard key={route.id} route={route} now={now} />)}</div></section><div className="saved-section-heading"><div><span className="eyebrow"><i /> Lugares guardados</span><h2>Destinos frecuentes</h2></div><span>3 lugares</span></div><div className="saved-grid">{savedPlaces.map((place) => <article className="saved-card transition-all duration-300 ease-out hover:-translate-y-1" key={place.name}><span className={`saved-place-icon ${place.tone}`}>{place.icon}</span><div><small>{place.name}</small><h3>{place.address}</h3><span>Ver rutas disponibles <b>→</b></span></div><button type="button" aria-label={`Abrir ${place.name}`}>↗</button></article>)}</div><div className="saved-section-heading history-heading"><div><span className="eyebrow"><i /> Actividad reciente</span><h2>Rutas realizadas</h2></div><span>Últimos recorridos</span></div><div className="route-history">{routeHistory.map((item) => <article className="history-row transition-colors duration-300" key={item.id}><span className={`history-icon ${item.tone}`}>✓</span><div className="history-route"><strong>{item.route}</strong><small>{item.date}</small></div><span className="history-stat"><small>Duración</small><strong>{item.duration}</strong></span><span className="history-stat"><small>Distancia</small><strong>{item.distance}</strong></span><button type="button" aria-label={`Repetir ruta ${item.route}`}>↗</button></article>)}</div></section>
}

function FavoriteRouteCard({ route, now }) {
  const elapsed = Math.min(route.totalTime, Math.max(0, Math.floor((now - route.startedAt) / 60000)))
  const progress = Math.min(100, Math.round((elapsed / route.totalTime) * 100))
  const remaining = Math.max(0, route.totalTime - elapsed)
  const isComplete = elapsed >= route.totalTime

  return <article className="favorite-route-card transition-all duration-300 ease-out hover:-translate-y-1"><div className="favorite-route-top"><span className={`route-symbol ${route.tone}`}>{route.icon}</span><div><span className="route-label">{route.name}</span><h3>{route.destination}</h3></div><span className={`journey-state ${isComplete ? 'complete' : ''}`}><i /> {isComplete ? 'Completada' : 'En curso'}</span></div><div className="route-endpoints"><span>{route.origin}</span><b>→</b><span>{route.destination}</span></div><div className="journey-progress"><span style={{ width: `${progress}%` }} /></div><div className="journey-times"><div><small>Desde ubicación actual</small><strong>{route.fromCurrent} min</strong></div><div><small>Inició a las</small><strong>{route.startLabel}</strong></div><div><small>Transcurrido</small><strong>{elapsed} min <em>/ {route.totalTime} min</em></strong></div><div><small>{isComplete ? 'Estado' : 'Faltan aprox.'}</small><strong>{isComplete ? 'Llegaste' : `${remaining} min`}</strong></div></div></article>
}

function getAssistantResponse(message, activeView) {
  const normalizedMessage = message.toLowerCase()
  if (normalizedMessage.includes('accidente') || normalizedMessage.includes('incidente') || normalizedMessage.includes('tráfico')) {
    return 'Hay 2 incidentes activos en Ciudad Bolívar. La ruta TransMiCable + B14 tiene 12% de incidencia estimada y riesgo bajo.'
  }
  if (normalizedMessage.includes('favorita') || normalizedMessage.includes('guardada')) {
    return 'Tu ruta favorita Casa → Universidad tarda aproximadamente 38 minutos desde Vista Hermosa. La última vez inició a las 06:12.'
  }
  if (normalizedMessage.includes('rápida') || normalizedMessage.includes('rapido') || normalizedMessage.includes('rápido')) {
    return 'La alternativa más rápida es TransMiCable + B14: 38 minutos, 2 transbordos y 12% de incidencia.'
  }
  if (activeView === 'explorar') return 'Estás explorando Bogotá. Puedo ayudarte a elegir una conexión, revisar incidentes o volver a planificar un recorrido.'
  if (activeView === 'guardados') return 'Estás en Guardados. Puedo comparar tus rutas favoritas o mostrarte cuánto ha tardado cada recorrido.'
  return 'Puedo comparar rutas de Ciudad Bolívar por tiempo, caminata, transbordos o incidencia. ¿Qué prefieres priorizar?'
}

function LocalTravelAssistant({ activeView, origin, destination, isOpen, onToggle }) {
  const [message, setMessage] = useState('')
  const [isSending, setIsSending] = useState(false)
  const [knownDestinations, setKnownDestinations] = useState([])
  const [messages, setMessages] = useState([{ from: 'assistant', text: 'Hola, soy tu asistente local. Puedo ayudarte a moverte por Ciudad Bolívar.' }])

  useEffect(() => {
    cargarMapa().then(({ stops }) => setKnownDestinations(stops)).catch(() => setKnownDestinations([]))
  }, [])

  async function submitMessage(event) {
    event.preventDefault()
    const cleanMessage = message.trim()
    if (!cleanMessage) return
    setMessages((current) => [...current, { from: 'user', text: cleanMessage }])
    setMessage('')
    setIsSending(true)
    try {
      const mentionedDestination = knownDestinations.find((point) => cleanMessage.toLowerCase().includes(point.nombre.toLowerCase()))
      const selectedDestination = mentionedDestination || destination
      const response = await recomendarRuta(cleanMessage, {
        origin: origin && { lat: origin.lat, lng: origin.lng },
        destination: selectedDestination && { lat: selectedDestination.lat, lng: selectedDestination.lng },
      })
      setMessages((current) => [...current, { from: 'assistant', text: `${response.respuesta} ${response.resumen}` }])
    } catch {
      setMessages((current) => [...current, { from: 'assistant', text: getAssistantResponse(cleanMessage, activeView) }])
    } finally {
      setIsSending(false)
    }
  }

  return <div className={`local-assistant ${isOpen ? 'open' : ''}`}><button className="assistant-launcher transition-all duration-300 ease-out hover:-translate-y-1 hover:scale-105" type="button" onClick={onToggle} aria-expanded={isOpen} aria-label={isOpen ? 'Cerrar asistente local' : 'Abrir asistente local'}><span className="assistant-spark">✦</span><span className="assistant-launcher-text">Asistente local</span><b>{isOpen ? '×' : '↗'}</b></button>{isOpen && <section className="assistant-panel animate-in slide-in-from-bottom-4 fade-in duration-300" aria-label="Asistente local de viajes"><header><div><span className="assistant-status"><i /> {isSending ? 'Consultando' : 'Conectado'}</span><h2>Muévete por Ciudad Bolívar</h2></div><span className="assistant-context">{activeView === 'planificar' ? 'Planificar' : activeView === 'explorar' ? 'Explorar' : 'Guardados'}</span></header><div className="assistant-messages">{messages.map((item, index) => <p className={`assistant-message ${item.from}`} key={`${item.from}-${index}`}>{item.text}</p>)}</div><div className="assistant-suggestions"><button type="button" onClick={() => setMessage('¿Cuál es la ruta más rápida?')}>Ruta más rápida</button><button type="button" onClick={() => setMessage('¿Hay accidentes en mi ruta?')}>Ver accidentes</button></div><form className="assistant-form" onSubmit={submitMessage}><input value={message} onChange={(event) => setMessage(event.target.value)} placeholder="Escribe una pregunta..." aria-label="Pregunta para el asistente" disabled={isSending} /><button type="submit" aria-label="Enviar pregunta" disabled={isSending}>→</button></form></section>}</div>
}

function SettingsPanel({ isDark, toggleTheme, onClose }) {
  return <div className="settings-backdrop animate-in fade-in duration-300" role="presentation" onMouseDown={onClose}><aside className="settings-panel animate-in slide-in-from-right-4 duration-300" role="dialog" aria-modal="true" aria-labelledby="settings-title" onMouseDown={(event) => event.stopPropagation()}><div className="settings-head"><div><span className="eyebrow"><i /> Personaliza tu espacio</span><h2 id="settings-title">Ajustes</h2></div><button className="transition-transform duration-300 hover:rotate-90" type="button" onClick={onClose} aria-label="Cerrar ajustes">×</button></div><div className="settings-section"><span className="settings-section-label">Apariencia</span><button className="theme-toggle-row transition-colors duration-300 hover:bg-(--canvas)" type="button" onClick={toggleTheme}><span className={`setting-icon ${isDark ? 'moon' : 'sun'}`}>{isDark ? '◐' : '☼'}</span><span><strong>{isDark ? 'Modo oscuro' : 'Modo claro'}</strong><small>{isDark ? 'Menos luz, misma ciudad' : 'Claro y luminoso'}</small></span><span className={`switch ${isDark ? 'on' : ''}`}><i /></span></button></div><div className="settings-section"><span className="settings-section-label">Preferencias</span><button className="settings-row transition-colors duration-300 hover:bg-(--canvas)" type="button"><span className="setting-icon">⌁</span><span><strong>Modo de transporte</strong><small>Transporte público y caminata</small></span><b>›</b></button><button className="settings-row transition-colors duration-300 hover:bg-(--canvas)" type="button"><span className="setting-icon">⌖</span><span><strong>Ubicación</strong><small>Vista Hermosa, Bogotá</small></span><b>›</b></button></div><div className="settings-note"><span>✦</span><p>Tu experiencia se guarda solo en este dispositivo.</p></div></aside></div>
}

export default App
