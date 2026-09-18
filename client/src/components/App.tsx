import React, { useEffect, useMemo, useState } from 'react';

interface LocationResult { lat: number; lon: number; location: string; }
interface ForecastDay { date: string; icon: string; description: string; max_c: number; min_c: number; rain_probability: number; precipitation: number; uv_index: number; max_wind: number; sunrise: string; sunset: string; }
interface HourlyItem { time: string; temperature_c: number; rain_probability: number; icon: string; description: string; wind_speed: number; }
interface WeatherData {
  timezone: string;
  elevation: number;
  location: { latitude: number; longitude: number };
  current: { time: string; temperature_c: number; feels_like_c: number; humidity: number; precipitation: number; rain_probability: number; wind_speed: number; pressure: number; visibility: number; uv_index: number; is_day: number; description: string; icon: string };
  forecast: ForecastDay[];
  hourly: HourlyItem[];
  raw_json: unknown;
}

const toF = (c: number) => Math.round((c * 9) / 5 + 32);
const formatHour = (value: string) => new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
const formatDay = (value: string, index: number) => index === 0 ? 'Today' : new Date(`${value}T12:00:00`).toLocaleDateString([], { weekday: 'short' });

function App() {
  const [query, setQuery] = useState('');
  const [locations, setLocations] = useState<LocationResult[]>([]);
  const [location, setLocation] = useState({ lat: 51.9225, lon: 4.47917, name: 'Rotterdam, South Holland, Netherlands' });
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [unit, setUnit] = useState<'C' | 'F'>('C');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [rawOpen, setRawOpen] = useState(false);

  const loadWeather = async (lat: number, lon: number) => {
    setLoading(true); setError('');
    try {
      const response = await fetch(`/server/current_weather?lat=${lat}&lon=${lon}`);
      if (!response.ok) throw new Error('Weather service unavailable.');
      setWeather(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unable to load weather.');
    } finally { setLoading(false); }
  };

  useEffect(() => { loadWeather(location.lat, location.lon); }, [location.lat, location.lon]);

  const search = async (event?: React.FormEvent) => {
    event?.preventDefault();
    if (!query.trim()) return;
    try {
      const response = await fetch(`/server/coordinates?city_name=${encodeURIComponent(query.trim())}`);
      if (!response.ok) throw new Error();
      const results = await response.json();
      setLocations(results);
      if (!results.length) setError('No matching cities found.'); else setError('');
    } catch { setError('Could not search for that city.'); }
  };

  const selectLocation = (item: LocationResult) => {
    setLocation({ lat: item.lat, lon: item.lon, name: item.location });
    setQuery(''); setLocations([]);
  };

  const current = weather?.current;
  const temp = current ? (unit === 'C' ? current.temperature_c : toF(current.temperature_c)) : 0;
  const feels = current ? (unit === 'C' ? current.feels_like_c : toF(current.feels_like_c)) : 0;
  const forecast = weather?.forecast ?? [];
  const hourly = useMemo(() => weather?.hourly?.slice(0, 12) ?? [], [weather]);

  const exportForecast = () => {
    if (!forecast.length) return;
    const rows = [['Date', 'Condition', 'Max', 'Min', 'Rain %', 'Precipitation mm', 'UV', 'Max wind km/h'], ...forecast.map(day => [day.date, day.description, `${day.max_c} °C`, `${day.min_c} °C`, day.rain_probability, day.precipitation, day.uv_index, day.max_wind])];
    const csv = rows.map(row => row.map(value => `"${String(value).replaceAll('"', '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob); const link = document.createElement('a');
    link.href = url; link.download = 'weather-forecast.csv'; link.click(); URL.revokeObjectURL(url);
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div className="title-block">
          <h1>Weather Dashboard <span aria-hidden="true">🌤️</span></h1>
        </div>
        <div className="top-actions">
          <button className="text-button" onClick={() => setUnit(unit === 'C' ? 'F' : 'C')}>°{unit}</button>
          <button className="text-button" onClick={() => loadWeather(location.lat, location.lon)}>Refresh</button>
        </div>
      </header>

      <section className="search-section">
        <form onSubmit={search} className="search-box">
          <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search City" aria-label="Search city" />
          <button type="submit" aria-label="Search">⌕</button>
        </form>
        {locations.length > 0 && <div className="results">{locations.map((item, index) => <button key={`${item.lat}-${item.lon}-${index}`} onClick={() => selectLocation(item)}>{item.location}</button>)}</div>}
        {error && <div className="error">{error}</div>}
      </section>

      {loading && <section className="loading-card"><div className="spinner" /> Loading weather...</section>}
      {!loading && weather && current && <>
        <section className="weather-card">
          <div className="weather-header">
            <div>
              <h2>{location.name}</h2>
              <div className="coordinates">Latitude: {weather.location.latitude.toFixed(3)} &nbsp;&nbsp; Longitude: {weather.location.longitude.toFixed(3)}</div>
            </div>
            <div className="current-time">{formatHour(current.time)}</div>
          </div>

          <div className="current-row">
            <div className="temperature-block">
              <div className="weather-icon">{current.icon}</div>
              <div className="temperature">{temp}°</div>
              <div className="condition">{current.description}</div>
            </div>
            <div className="current-date">{new Date(current.time).toLocaleDateString([], { weekday: 'long', day: '2-digit', month: '2-digit' })}<br />{current.description}</div>
          </div>

          <div className="quick-stats">
            <span>💧 Precipitation: {current.precipitation} mm</span>
            <span>Humidity: {current.humidity}%</span>
            <span>Wind speed: {current.wind_speed} km/h</span>
            <span>Feels like: {feels}°</span>
          </div>

          <div className="card-actions">
            <button className="accent-button" onClick={() => setRawOpen(true)}>VIEW OUTPUT <span>◉</span></button>
          </div>

          <div className="forecast-divider" />

          <div className="section-title-row"><h3>Next 12 hours</h3></div>
          <div className="hourly-grid">{hourly.map((item, index) => <article className={`hour-card ${index === 0 ? 'active' : ''}`} key={item.time}><span>{index === 0 ? 'Now' : formatHour(item.time)}</span><strong>{item.icon}</strong><b>{unit === 'C' ? item.temperature_c : toF(item.temperature_c)}°</b><small>💧 {item.rain_probability}%</small></article>)}</div>

          <div className="section-title-row forecast-heading"><h3>Last 7 days:</h3><button className="accent-button small" onClick={exportForecast}>DOWNLOAD EXCEL <span>⇩</span></button></div>
          <div className="forecast-grid">{forecast.map((day, index) => <article className="forecast-card" key={day.date}><span>{formatDay(day.date, index)}</span><strong>{day.icon}</strong><b>{unit === 'C' ? day.max_c : toF(day.max_c)}°</b><small>{day.description}</small><em>{day.rain_probability}% rain</em></article>)}</div>

          <div className="details-grid">
            <span>UV index <b>{current.uv_index}</b></span>
            <span>Max wind <b>{forecast[0]?.max_wind ?? '—'} km/h</b></span>
            <span>Sunrise <b>{forecast[0]?.sunrise ? formatHour(forecast[0].sunrise) : '—'}</b></span>
            <span>Sunset <b>{forecast[0]?.sunset ? formatHour(forecast[0].sunset) : '—'}</b></span>
          </div>
        </section>
      </>}

      {rawOpen && weather && <div className="modal-backdrop" onClick={() => setRawOpen(false)}><div className="modal" onClick={e => e.stopPropagation()}><div className="modal-header"><h2>API response</h2><button onClick={() => setRawOpen(false)}>×</button></div><pre>{JSON.stringify(weather.raw_json, null, 2)}</pre></div></div>}
      <footer>Weather data provided by Open-Meteo · No API key required</footer>
    </main>
  );
}

export default App;
