import React, { useEffect, useState, useCallback } from 'react';
import { useTrialStore } from '../store';
import { Building2, MapPin, Activity, AlertTriangle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API = 'http://localhost:8000';

function lngLatToXY(lng, lat) {
  const x = (lng + 180) * (1000 / 360);
  const y = (90 - lat) * (500 / 180);
  return [x, y];
}

const GEO_URL = 'https://raw.githubusercontent.com/holtzy/D3-graph-gallery/master/DATA/world.geojson';
const MAP_VIEWBOX = '0 22 1000 398';
const TIER_COLORS = { academic: '#3b82f6', community: '#8b5cf6' };
const STATUS_COLORS = { active: '#10b981', pending: '#f59e0b', on_hold: '#ef4444', closed: '#475569' };

function geojsonToSvgPaths(geojson) {
  const paths = [];
  for (const f of geojson.features || []) {
    const g = f.geometry;
    if (!g) continue;
    const polys = g.type === 'Polygon' ? [g.coordinates] : g.type === 'MultiPolygon' ? g.coordinates : [];
    for (const poly of polys) {
      for (const ring of poly) {
        let d = '';
        for (let i = 0; i < ring.length; i++) {
          const [x, y] = lngLatToXY(ring[i][0], ring[i][1]);
          d += i === 0 ? `M${x.toFixed(1)},${y.toFixed(1)}` : `L${x.toFixed(1)},${y.toFixed(1)}`;
        }
        paths.push({ d: d + 'Z', id: paths.length });
      }
    }
  }
  return paths;
}

export default function SiteOperations() {
  const { sessionId } = useTrialStore();
  const [siteData, setSiteData] = useState(null);
  const [mapPaths, setMapPaths] = useState([]);
  const [selected, setSelected] = useState(null);

  useEffect(() => {
    fetch(GEO_URL).then(r => r.json()).then(d => setMapPaths(geojsonToSvgPaths(d))).catch(() => {});
  }, []);

  const fetchSites = useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo') return;
    try {
      const res = await window.fetch(`${API}/simulation/sites/${sessionId}`);
      const d = await res.json();
      setSiteData(d);
    } catch {}
  }, [sessionId]);

  useEffect(() => { fetchSites(); const id = setInterval(fetchSites, 6000); return () => clearInterval(id); }, [fetchSites]);

  const sites = siteData?.sites || [];
  const active = sites.filter(s => s.status === 'active').length;
  const onHold = sites.filter(s => s.status === 'on_hold').length;
  const totalEnrolled = siteData?.total_enrolled || 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 18, height: '100%' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
        <div style={{ padding: 12, background: 'rgba(16,185,129,0.15)', color: '#10b981', borderRadius: 14 }}>
          <Building2 size={24} />
        </div>
        <div>
          <h2 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>Site Operations</h2>
          <p style={{ color: '#64748b', fontSize: 12, margin: 0 }}>
            {sites.length} sites · {active} active · {onHold} on hold · {totalEnrolled} enrolled total
          </p>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 18, flex: 1, minHeight: 0 }}>
        {/* Map */}
        <div style={{
          flex: 1, background: 'rgba(4,8,20,0.95)', borderRadius: 20,
          border: '1px solid rgba(255,255,255,0.07)', overflow: 'hidden', position: 'relative',
        }}>
          <svg viewBox={MAP_VIEWBOX} style={{ width: '100%', height: '100%', display: 'block' }} preserveAspectRatio="xMidYMid meet">
            <defs>
              <radialGradient id="bgS" cx="50%" cy="50%" r="70%">
                <stop offset="0%" stopColor="#0c1a30" /><stop offset="100%" stopColor="#040810" />
              </radialGradient>
            </defs>
            <rect width={1000} height={500} fill="url(#bgS)" />
            {mapPaths.map(p => p.d && <path key={p.id} d={p.d} fill="#0d2040" stroke="#1a3a60" strokeWidth={0.4} />)}
            {sites.map((site, i) => {
              const [px, py] = lngLatToXY(site.coords[0], site.coords[1]);
              const color = STATUS_COLORS[site.status] || '#475569';
              const isSel = selected?.site_id === site.site_id;
              return (
                <g key={site.site_id} style={{ cursor: 'pointer' }} onClick={() => setSelected(isSel ? null : site)}>
                  <circle cx={px} cy={py} fill="none" stroke={color} strokeWidth={1} opacity={0.4}>
                    <animate attributeName="r" values="6;12;6" dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />
                    <animate attributeName="opacity" values="0.5;0;0.5" dur={`${2 + i * 0.2}s`} repeatCount="indefinite" />
                  </circle>
                  <circle cx={px} cy={py} r={isSel ? 7 : 5} fill={color} stroke={isSel ? '#fff' : 'rgba(255,255,255,0.4)'} strokeWidth={isSel ? 1.5 : 0.8} />
                  {isSel && (
                    <text x={px + 9} y={py + 4} fontSize={8} fill={color} fontWeight={700} style={{ pointerEvents: 'none' }}>
                      {site.city}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>

          {/* Legend */}
          <div style={{ position: 'absolute', top: 12, left: 12, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {Object.entries(STATUS_COLORS).map(([k, c]) => (
              <span key={k} style={{ fontSize: 10, color: c, background: 'rgba(0,0,0,0.6)', padding: '3px 8px', borderRadius: 6 }}>
                ● {k}
              </span>
            ))}
          </div>

          {/* Selected site popup */}
          <AnimatePresence>
            {selected && (
              <motion.div
                initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                style={{
                  position: 'absolute', bottom: 14, left: 14, right: 14,
                  background: 'rgba(6,10,24,0.97)', backdropFilter: 'blur(20px)',
                  border: `1px solid ${STATUS_COLORS[selected.status] || '#475569'}40`,
                  borderLeft: `4px solid ${STATUS_COLORS[selected.status] || '#475569'}`,
                  borderRadius: 14, padding: '14px 18px',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ fontWeight: 800, fontSize: 14, marginBottom: 4 }}>{selected.site_id} — {selected.city}, {selected.country}</div>
                    <div style={{ fontSize: 11, color: '#64748b', display: 'flex', gap: 12 }}>
                      <span>Tier: <b style={{ color: TIER_COLORS[selected.tier] }}>{selected.tier}</b></span>
                      <span>Enrolled: <b style={{ color: '#10b981' }}>{selected.enrolled_count}</b></span>
                      <span>Deviations: <b style={{ color: selected.protocol_deviations >= 3 ? '#ef4444' : '#94a3b8' }}>{selected.protocol_deviations}</b></span>
                      <span>Perf: <b style={{ color: selected.performance_score >= 0.8 ? '#10b981' : '#f59e0b' }}>{(selected.performance_score * 100).toFixed(0)}%</b></span>
                      <span>Rate: <b>{selected.recruitment_rate?.toFixed(1)}</b>/wk</span>
                    </div>
                  </div>
                  <button onClick={() => setSelected(null)} style={{ background: 'none', border: 'none', color: '#475569', cursor: 'pointer', fontSize: 16 }}>✕</button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Site list */}
        <div style={{ width: 280, flexShrink: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8 }}>
          <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5, color: '#334155', flexShrink: 0 }}>
            Site Registry
          </div>
          {sites.length === 0
            ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} style={{ height: 72, borderRadius: 10, background: 'rgba(255,255,255,0.03)', animation: 'pulse 1.5s infinite' }} />
            ))
            : sites.map(site => {
              const color = STATUS_COLORS[site.status] || '#475569';
              const isSel = selected?.site_id === site.site_id;
              return (
                <motion.div
                  key={site.site_id}
                  whileHover={{ x: 3 }}
                  onClick={() => setSelected(isSel ? null : site)}
                  style={{
                    padding: '10px 12px', borderRadius: 10, cursor: 'pointer', flexShrink: 0,
                    background: isSel ? `${color}15` : 'rgba(255,255,255,0.03)',
                    border: `1px solid ${isSel ? color + '40' : 'rgba(255,255,255,0.05)'}`,
                    borderLeft: `3px solid ${color}`,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ fontWeight: 700, fontSize: 12 }}>{site.city}</span>
                    <span style={{ fontSize: 10, color, fontWeight: 700 }}>{site.status}</span>
                  </div>
                  <div style={{ fontSize: 10, color: '#475569', display: 'flex', gap: 8 }}>
                    <span>{site.enrolled_count} enrolled</span>
                    <span>•</span>
                    <span style={{ color: site.protocol_deviations >= 3 ? '#ef4444' : '#475569' }}>
                      {site.protocol_deviations} devs
                    </span>
                    <span>•</span>
                    <span style={{ color: TIER_COLORS[site.tier] }}>{site.tier}</span>
                  </div>
                  <div style={{ marginTop: 6, height: 3, background: 'rgba(255,255,255,0.05)', borderRadius: 99 }}>
                    <div style={{ height: '100%', background: color, borderRadius: 99, width: `${Math.min(100, site.performance_score * 100)}%` }} />
                  </div>
                </motion.div>
              );
            })
          }
        </div>
      </div>
      <style>{`@keyframes pulse{0%,100%{opacity:.25}50%{opacity:.6}}`}</style>
    </div>
  );
}
