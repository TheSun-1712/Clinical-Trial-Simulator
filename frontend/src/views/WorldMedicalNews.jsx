import React, { useEffect, useState, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe, ExternalLink, RefreshCw, Newspaper, MapPin } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Country centroid coordinates [lng, lat] — WGS84 decimal degrees
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
  'Netherlands': [5, 52], 'Spain': [-3.7, 40.4],
  'Italy': [12.5, 42], 'Switzerland': [8.2, 46.8],
  'Israel': [34.8, 31.5], 'Singapore': [103.8, 1.3],
  'New Zealand': [172, -41], 'South Africa': [25, -29],
  'Argentina': [-64, -34], 'World': [-20, 30],
};

const COLORS = ['#3b82f6','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#f97316','#a78bfa'];

// Equirectangular projection: convert [lng, lat] to [x, y] within a 1000×500 canvas
function lngLatToXY(lng, lat) {
  const x = (lng + 180) * (1000 / 360);
  const y = (90 - lat) * (500 / 180);
  return [x, y];
}

// The full equirectangular canvas is 1000×500 (full world).
// We crop to the "inhabited" viewport to remove the polar black gaps:
//   Top crop:    lat 80°N → y = (90-80)/180*500 = 27.8  → crop from y=20
//   Bottom crop: lat 60°S → y = (90+60)/180*500 = 416.7 → crop to  y=420
// viewBox: "x y w h" where x=0, y=20, w=1000, h=400
const MAP_VIEWBOX = '0 22 1000 398';

// We embed a tiny simplified world SVG path string from Natural Earth.
// Source: https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson
// We fetch it at runtime so we always get the right coordinates.
const GEOJSON_URL = 'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson';

function geojsonToSvgPaths(geojson) {
  const paths = [];
  for (const feature of geojson.features || []) {
    const { geometry } = feature;
    if (!geometry) continue;
    const polys = geometry.type === 'Polygon'
      ? [geometry.coordinates]
      : geometry.type === 'MultiPolygon'
        ? geometry.coordinates
        : [];
    for (const poly of polys) {
      for (const ring of poly) {
        let d = '';
        for (let i = 0; i < ring.length; i++) {
          const [x, y] = lngLatToXY(ring[i][0], ring[i][1]);
          d += i === 0 ? `M${x.toFixed(1)},${y.toFixed(1)}` : `L${x.toFixed(1)},${y.toFixed(1)}`;
        }
        d += 'Z';
        paths.push({ d, id: `${feature.id ?? feature.properties?.name ?? ''}-${paths.length}` });
      }
    }
  }
  return paths;
}

export default function WorldMedicalNews() {
  const [news, setNews] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mapPaths, setMapPaths] = useState([]);
  const [lastUpdated, setLastUpdated] = useState(null);
  const timerRef = useRef(null);

  // Load world GeoJSON once
  useEffect(() => {
    fetch(GEOJSON_URL)
      .then(r => r.json())
      .then(geojson => setMapPaths(geojsonToSvgPaths(geojson)))
      .catch(() => setMapPaths([]));
  }, []);

  const fetchNews = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/simulation/news?limit=25`);
      if (!res.ok) throw new Error('API error');
      const data = await res.json();
      const enriched = (data.news || []).map((item, i) => {
        // Use coords provided by the backend (already jittered + location-extracted)
        const coords = item.coords ?? COUNTRY_COORDS[item.location] ?? COUNTRY_COORDS['World'];
        const [px, py] = lngLatToXY(coords[0], coords[1]);
        return { ...item, px, py, color: COLORS[i % COLORS.length] };
      });
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
              Live SerpAPI feed · {news.length} stories · Refreshes every 2 min
              {lastUpdated && ` · ${lastUpdated.toLocaleTimeString()}`}
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
          {loading ? 'Loading…' : 'Refresh'}
        </motion.button>
      </div>

      {/* Body */}
      <div style={{ display: 'flex', gap: 18, flex: 1, minHeight: 0 }}>
        {/* SVG Map */}
        <div style={{
          flex: 1, background: 'rgba(4,8,20,0.95)', borderRadius: 20,
          border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden',
          position: 'relative',
        }}>
          <svg
            viewBox={MAP_VIEWBOX}
            style={{ width: '100%', height: '100%', display: 'block' }}
            preserveAspectRatio="xMidYMid meet"
          >
            <defs>
              <radialGradient id="bgGrad" cx="50%" cy="50%" r="70%">
                <stop offset="0%" stopColor="#0c1a30" />
                <stop offset="100%" stopColor="#040810" />
              </radialGradient>
            </defs>
            <rect width={1000} height={500} fill="url(#bgGrad)" />

            {/* Graticule lines */}
            {[-60, -30, 0, 30, 60].map(lat => {
              const [, y] = lngLatToXY(0, lat);
              return <line key={lat} x1={0} x2={1000} y1={y} y2={y} stroke="rgba(59,130,246,0.08)" strokeWidth={0.6} />;
            })}
            {[-120, -60, 0, 60, 120].map(lng => {
              const [x] = lngLatToXY(lng, 0);
              return <line key={lng} x1={x} x2={x} y1={0} y2={500} stroke="rgba(59,130,246,0.08)" strokeWidth={0.6} />;
            })}

            {/* Country paths */}
            {mapPaths.map(p => (
              <path key={p.id} d={p.d} fill="#0d2040" stroke="#1a3a60" strokeWidth={0.4} />
            ))}

            {/* News pins */}
            {news.map((item, idx) => {
              const isSelected = selected?.title === item.title;
              return (
                <g
                  key={idx}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelected(isSelected ? null : item)}
                >
                  {/* Outer pulse ring */}
                  <circle cx={item.px} cy={item.py} fill="none" stroke={item.color} strokeWidth={1} opacity={0.4}>
                    <animate attributeName="r" values="7;14;7" dur={`${1.8 + idx * 0.1}s`} repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.5;0;0.5" dur={`${1.8 + idx * 0.1}s`} repeatCount="indefinite" />
                  </circle>
                  {/* Inner dot */}
                  <circle
                    cx={item.px} cy={item.py}
                    r={isSelected ? 6 : 4}
                    fill={item.color}
                    stroke={isSelected ? '#fff' : 'rgba(255,255,255,0.5)'}
                    strokeWidth={isSelected ? 1.5 : 0.7}
                  >
                    {isSelected && (
                      <animate attributeName="r" values="5;7;5" dur="1s" repeatCount="indefinite" />
                    )}
                  </circle>
                  {/* Location label when selected */}
                  {isSelected && (
                    <text
                      x={item.px + 8} y={item.py + 4}
                      fontSize={9} fill={item.color}
                      fontWeight={700} fontFamily="monospace"
                      style={{ pointerEvents: 'none', userSelect: 'none' }}
                    >
                      {item.location}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Article popup */}
          <AnimatePresence>
            {selected && (
              <motion.div
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 12 }}
                style={{
                  position: 'absolute', bottom: 16, left: 16, right: 16,
                  background: 'rgba(6,10,24,0.97)', backdropFilter: 'blur(24px)',
                  border: `1px solid ${selected.color}50`,
                  borderLeft: `4px solid ${selected.color}`,
                  borderRadius: 14, padding: '14px 18px',
                  display: 'flex', alignItems: 'flex-start', gap: 14,
                }}
              >
                {selected.thumbnail && (
                  <img
                    src={selected.thumbnail}
                    alt=""
                    onError={e => { e.target.style.display = 'none'; }}
                    style={{ width: 58, height: 58, borderRadius: 10, objectFit: 'cover', flexShrink: 0 }}
                  />
                )}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 700, lineHeight: 1.45, color: '#f1f5f9', marginBottom: 6 }}>
                    {selected.title}
                  </div>
                  <div style={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, fontSize: 10, color: '#64748b' }}>
                    <span style={{ color: selected.color, display: 'flex', alignItems: 'center', gap: 3 }}>
                      <MapPin size={9} /> {selected.location}
                    </span>
                    {selected.source && <span>· {selected.source}</span>}
                    {selected.date && <span>· {selected.date}</span>}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: 6, flexShrink: 0, alignItems: 'center' }}>
                  {selected.link && (
                    <a
                      href={selected.link}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{
                        padding: '7px 14px', borderRadius: 9, fontSize: 11, fontWeight: 700,
                        background: selected.color, color: '#fff',
                        display: 'flex', alignItems: 'center', gap: 4, textDecoration: 'none',
                      }}
                    >
                      <ExternalLink size={11} /> Read
                    </a>
                  )}
                  <button
                    onClick={() => setSelected(null)}
                    style={{
                      width: 32, height: 32, borderRadius: 8,
                      background: 'rgba(255,255,255,0.06)',
                      border: '1px solid rgba(255,255,255,0.1)',
                      color: '#94a3b8', cursor: 'pointer', fontSize: 14,
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                    }}
                  >✕</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Hint */}
          {!loading && news.length > 0 && !selected && (
            <div style={{
              position: 'absolute', top: 14, right: 14,
              background: 'rgba(0,0,0,0.65)', backdropFilter: 'blur(8px)',
              borderRadius: 8, padding: '5px 11px', fontSize: 10, color: '#475569',
            }}>
              {news.length} stories · Click a pin to read
            </div>
          )}

          {/* Loading overlay */}
          {loading && mapPaths.length === 0 && (
            <div style={{
              position: 'absolute', inset: 0, display: 'flex', alignItems: 'center',
              justifyContent: 'center', flexDirection: 'column', gap: 12,
            }}>
              <Globe size={36} style={{ color: '#3b82f6', animation: 'spin 2s linear infinite' }} />
              <span style={{ fontSize: 13, color: '#475569' }}>Loading world map…</span>
            </div>
          )}
        </div>

        {/* News sidebar */}
        <div style={{
          width: 296, flexShrink: 0, display: 'flex', flexDirection: 'column', gap: 8, overflowY: 'auto',
        }}>
          <div style={{
            fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5,
            color: '#334155', flexShrink: 0, display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <Newspaper size={10} /> Live Feed
          </div>

          {loading && news.length === 0
            ? Array.from({ length: 7 }).map((_, i) => (
              <div key={i} style={{
                height: 68, borderRadius: 10,
                background: 'rgba(255,255,255,0.03)',
                animationDelay: `${i * 0.1}s`,
                animation: 'pulse 1.5s ease-in-out infinite',
              }} />
            ))
            : news.map((item, i) => {
              const isSelected = selected?.title === item.title;
              return (
                <motion.div
                  key={i}
                  onClick={() => setSelected(isSelected ? null : item)}
                  whileHover={{ x: 4 }}
                  style={{
                    padding: '10px 12px', borderRadius: 10, cursor: 'pointer', flexShrink: 0,
                    background: isSelected ? `${item.color}18` : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isSelected ? item.color + '50' : 'rgba(255,255,255,0.05)'}`,
                    borderLeft: `3px solid ${item.color}`,
                    transition: 'all 0.15s',
                  }}
                >
                  <div style={{
                    fontSize: 12, fontWeight: 600, lineHeight: 1.4,
                    color: '#e2e8f0', marginBottom: 5,
                    display: '-webkit-box', WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical', overflow: 'hidden',
                  }}>
                    {item.title}
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 10, color: '#475569' }}>
                    <span style={{
                      display: 'inline-flex', alignItems: 'center', gap: 3,
                      padding: '1px 5px', borderRadius: 4,
                      background: `${item.color}22`, color: item.color, fontWeight: 700,
                    }}>
                      <MapPin size={8} /> {item.location}
                    </span>
                    {item.source && (
                      <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.source}
                      </span>
                    )}
                  </div>
                </motion.div>
              );
            })
          }
        </div>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
        @keyframes pulse { 0%,100%{opacity:0.25} 50%{opacity:0.6} }
      `}</style>
    </div>
  );
}
