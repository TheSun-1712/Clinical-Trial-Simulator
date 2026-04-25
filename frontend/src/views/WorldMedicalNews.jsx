import React, { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, ExternalLink, RefreshCw, Newspaper, MapPin, Clock, ZoomIn, ZoomOut } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Country centroid coordinates [lng, lat]
const COUNTRY_COORDS = {
  'United States': [-98, 39], 'USA': [-98, 39],
  'Canada': [-96, 60], 'Germany': [10, 51],
  'France': [2, 46], 'UK': [-2, 54],
  'United Kingdom': [-2, 54], 'Australia': [134, -25],
  'China': [105, 35], 'India': [78, 22],
  'Japan': [138, 36], 'Brazil': [-51, -14],
  'Mexico': [-102, 24], 'South Korea': [128, 37],
  'Russia': [105, 61], 'Sweden': [18, 62],
  'Norway': [15, 65], 'Denmark': [10, 56],
  'Netherlands': [5, 52], 'World': [0, 20],
  'Spain': [-3.7, 40.4], 'Italy': [12.5, 42],
  'Switzerland': [8.2, 46.8], 'Israel': [34.8, 31.5],
  'Singapore': [103.8, 1.3], 'New Zealand': [172, -41],
  'South Africa': [25, -29], 'Argentina': [-64, -34],
};

const COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f97316','#a78bfa'];

// Equirectangular projection: convert [lng, lat] to [x%, y%] on the map canvas
function project(lng, lat, width, height) {
  const x = ((lng + 180) / 360) * width;
  const y = ((90 - lat) / 180) * height;
  return [x, y];
}

// Simple SVG world map paths from Natural Earth data (simplified polygons as a static fallback)
// We'll load actual GeoJSON via fetch from a CDN
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Minimal TopoJSON decoder — extract the arcs for country borders
async function loadWorldPaths(width, height) {
  try {
    const res = await fetch(GEO_URL);
    const topo = await res.json();
    // Use the countries object from topojson
    const land = topo.objects?.land;
    if (!land) return [];
    // Decode arcs into SVG path strings using equirectangular projection
    const arcs = topo.arcs || [];
    const transform = topo.transform || { scale: [1, 1], translate: [0, 0] };
    const [sx, sy] = transform.scale;
    const [tx, ty] = transform.translate;
    // Decode a single arc
    function decodeArc(arcIdx) {
      const reversed = arcIdx < 0;
      const arc = arcs[reversed ? ~arcIdx : arcIdx];
      let x = 0, y = 0;
      const points = arc.map(([dx, dy]) => {
        x += dx; y += dy;
        const lng = x * sx + tx;
        const lat = y * sy + ty;
        return project(lng, lat, width, height);
      });
      if (reversed) points.reverse();
      return points;
    }
    // Decode a geometry
    function geomToPath(geom) {
      if (!geom) return '';
      const arcsLists = geom.type === 'Polygon' ? geom.arcs : geom.type === 'MultiPolygon' ? geom.arcs.flat() : [];
      return arcsLists.map(ring => {
        const pts = ring.flatMap(decodeArc);
        if (pts.length === 0) return '';
        return `M${pts.map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`).join('L')}Z`;
      }).join(' ');
    }
    // Collect all country geometries
    const countries = topo.objects?.countries;
    if (!countries || !countries.geometries) {
      // Fallback: just render land
      return [{ d: geomToPath(land), id: 'land' }];
    }
    return countries.geometries.map((g, i) => ({
      id: g.id || i,
      d: geomToPath(g),
    }));
  } catch {
    return [];
  }
}

export default function WorldMedicalNews() {
  const [news, setNews] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [paths, setPaths] = useState([]);
  const mapRef = useRef(null);
  const timerRef = useRef(null);
  const [mapSize, setMapSize] = useState({ w: 800, h: 420 });

  // Load world paths once
  useEffect(() => {
    loadWorldPaths(mapSize.w, mapSize.h).then(setPaths);
  }, [mapSize.w, mapSize.h]);

  // Track map container size
  useEffect(() => {
    const obs = new ResizeObserver(entries => {
      for (const e of entries) {
        const { width, height } = e.contentRect;
        if (width > 0 && height > 0) setMapSize({ w: Math.round(width), h: Math.round(height) });
      }
    });
    if (mapRef.current) obs.observe(mapRef.current);
    return () => obs.disconnect();
  }, []);

  const fetchNews = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulation/news?limit=25`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const enriched = (data.news || []).map((item, i) => ({
        ...item,
        coords: COUNTRY_COORDS[item.location] ?? COUNTRY_COORDS['World'],
        color: COLORS[i % COLORS.length],
        jitter: [(Math.random() - 0.5) * 6, (Math.random() - 0.5) * 4],
      }));
      setNews(enriched);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Medical news fetch error:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNews();
    timerRef.current = setInterval(fetchNews, 2 * 60 * 1000);
    return () => clearInterval(timerRef.current);
  }, [fetchNews]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 18, minHeight: 0 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 14,
            background: 'linear-gradient(135deg, rgba(59,130,246,0.2), rgba(139,92,246,0.2))',
            border: '1px solid rgba(59,130,246,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Globe size={22} style={{ color: '#3b82f6' }} />
          </div>
          <div>
            <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>Global Medical Intelligence</h2>
            <p style={{ fontSize: 12, color: '#475569', margin: 0 }}>
              Live SerpAPI feed · Click pins to read articles · Refreshes every 2 min
              {lastUpdated && ` · Updated ${lastUpdated.toLocaleTimeString()}`}
            </p>
          </div>
        </div>
        <motion.button
          onClick={fetchNews}
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          style={{
            padding: '8px 16px', borderRadius: 10, border: '1px solid rgba(59,130,246,0.3)',
            background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
            display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}
        >
          <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          {loading ? 'Loading...' : 'Refresh'}
        </motion.button>
      </div>

      {/* Main layout */}
      <div style={{ display: 'flex', gap: 18, flex: 1, minHeight: 0 }}>
        {/* Map */}
        <div
          ref={mapRef}
          style={{
            flex: 2, background: 'rgba(5,8,22,0.9)', borderRadius: 20,
            border: '1px solid rgba(255,255,255,0.06)', overflow: 'hidden',
            position: 'relative', minHeight: 360,
          }}
        >
          <svg
            width="100%" height="100%"
            viewBox={`0 0 ${mapSize.w} ${mapSize.h}`}
            style={{ position: 'absolute', inset: 0 }}
          >
            {/* Gradient background */}
            <defs>
              <radialGradient id="oceanGrad" cx="50%" cy="50%" r="70%">
                <stop offset="0%" stopColor="#0c1628" />
                <stop offset="100%" stopColor="#050810" />
              </radialGradient>
            </defs>
            <rect width={mapSize.w} height={mapSize.h} fill="url(#oceanGrad)" />

            {/* Country paths */}
            {paths.map((p) =>
              p.d ? (
                <path
                  key={p.id}
                  d={p.d}
                  fill="#0f2040"
                  stroke="#1e3a5f"
                  strokeWidth={0.5}
                  style={{ transition: 'fill 0.2s' }}
                />
              ) : null
            )}

            {/* Grid lines */}
            {[-60, -30, 0, 30, 60].map(lat => {
              const [, y] = project(0, lat, mapSize.w, mapSize.h);
              return <line key={lat} x1={0} x2={mapSize.w} y1={y} y2={y} stroke="rgba(59,130,246,0.07)" strokeWidth={0.5} />;
            })}
            {[-120, -60, 0, 60, 120].map(lng => {
              const [x] = project(lng, 0, mapSize.w, mapSize.h);
              return <line key={lng} x1={x} x2={x} y1={0} y2={mapSize.h} stroke="rgba(59,130,246,0.07)" strokeWidth={0.5} />;
            })}

            {/* News markers */}
            {news.map((item, idx) => {
              const [lng, lat] = item.coords;
              const [px, py] = project(lng + item.jitter[0], lat + item.jitter[1], mapSize.w, mapSize.h);
              const isSelected = selected?.title === item.title;
              return (
                <g key={idx} style={{ cursor: 'pointer' }} onClick={() => setSelected(item === selected ? null : item)}>
                  {/* Pulse ring */}
                  <circle cx={px} cy={py} r={isSelected ? 16 : 10} fill="none" stroke={item.color} strokeWidth={1} opacity={0.3}>
                    <animate attributeName="r" values={`${isSelected ? 14 : 8};${isSelected ? 22 : 16};${isSelected ? 14 : 8}`} dur="2s" repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.4;0;0.4" dur="2s" repeatCount="indefinite" />
                  </circle>
                  {/* Dot */}
                  <circle
                    cx={px} cy={py} r={isSelected ? 6 : 4}
                    fill={item.color}
                    stroke={isSelected ? '#fff' : 'rgba(255,255,255,0.3)'}
                    strokeWidth={isSelected ? 1.5 : 0.8}
                    filter={isSelected ? `drop-shadow(0 0 6px ${item.color})` : 'none'}
                  />
                  {/* Label on hover — shown for selected */}
                  {isSelected && (
                    <text x={px + 9} y={py + 4} fontSize={9} fill={item.color} fontWeight={700} style={{ pointerEvents: 'none' }}>
                      {item.location}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Selected article popup */}
          <AnimatePresence>
            {selected && (
              <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 10 }}
                style={{
                  position: 'absolute', bottom: 16, left: 16, right: 16,
                  background: 'rgba(8,12,28,0.97)', backdropFilter: 'blur(20px)',
                  border: `1px solid ${selected.color}40`,
                  borderLeft: `3px solid ${selected.color}`,
                  borderRadius: 14, padding: '14px 18px',
                  display: 'flex', alignItems: 'flex-start', gap: 12,
                }}
              >
                {selected.thumbnail && (
                  <img
                    src={selected.thumbnail}
                    alt=""
                    onError={e => { e.target.style.display = 'none'; }}
                    style={{ width: 56, height: 56, borderRadius: 8, objectFit: 'cover', flexShrink: 0 }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, lineHeight: 1.4, marginBottom: 5, color: '#f1f5f9' }}>
                    {selected.title}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: 10, color: '#64748b', flexWrap: 'wrap' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 3, color: selected.color }}>
                      <MapPin size={9} /> {selected.location}
                    </span>
                    {selected.source && <span>· {selected.source}</span>}
                    {selected.date && <span>· {selected.date}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                  {selected.link && (
                    <a
                      href={selected.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '7px 12px', borderRadius: 8, fontSize: 11, fontWeight: 700,
                        background: selected.color, color: '#fff',
                        display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none',
                      }}
                    >
                      <ExternalLink size={10} /> Read
                    </a>
                  )}
                  <button
                    onClick={() => setSelected(null)}
                    style={{
                      padding: '7px 10px', borderRadius: 8,
                      background: 'rgba(255,255,255,0.05)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      color: '#94a3b8', cursor: 'pointer', fontSize: 12,
                    }}
                  >✕</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Map hint */}
          {news.length > 0 && !selected && (
            <div style={{
              position: 'absolute', top: 14, right: 14,
              background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(8px)',
              borderRadius: 8, padding: '5px 10px', fontSize: 10, color: '#475569',
            }}>
              {news.length} stories · Click a pin to read
            </div>
          )}
        </div>

        {/* Sidebar feed */}
        <div style={{
          width: 300, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8,
          overflowY: 'auto',
        }}>
          <div style={{
            fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5,
            color: '#334155', marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6,
            flexShrink: 0,
          }}>
            <Newspaper size={10} /> {news.length} Live Stories
          </div>

          {loading && news.length === 0
            ? Array.from({ length: 6 }).map((_, i) => (
              <div key={i} style={{
                height: 72, borderRadius: 10,
                background: 'rgba(255,255,255,0.03)',
                animation: 'pulse 1.5s ease-in-out infinite',
                animationDelay: `${i * 0.1}s`,
              }} />
            ))
            : news.map((item, i) => (
              <motion.div
                key={i}
                onClick={() => setSelected(item === selected ? null : item)}
                whileHover={{ x: 3 }}
                style={{
                  padding: '10px 13px', borderRadius: 10, cursor: 'pointer',
                  background: selected?.title === item.title ? `${item.color}15` : 'rgba(255,255,255,0.03)',
                  border: `1px solid ${selected?.title === item.title ? item.color + '40' : 'rgba(255,255,255,0.05)'}`,
                  borderLeft: `3px solid ${item.color}`,
                  transition: 'all 0.15s', flexShrink: 0,
                }}
              >
                <div style={{
                  fontSize: 12, fontWeight: 600, lineHeight: 1.4, color: '#e2e8f0', marginBottom: 5,
                  display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden',
                }}>
                  {item.title}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#475569' }}>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: 3,
                    padding: '1px 6px', background: `${item.color}20`,
                    borderRadius: 4, color: item.color, fontWeight: 700,
                  }}>
                    <MapPin size={8} /> {item.location}
                  </span>
                  {item.source && <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{item.source}</span>}
                </div>
              </motion.div>
            ))
          }
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:0.3} 50%{opacity:0.7} }
      `}</style>
    </div>
  );
}
