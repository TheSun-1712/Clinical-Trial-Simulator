import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, AlertTriangle, ExternalLink, FlaskConical, RefreshCw } from 'lucide-react';
import { useTrialStore } from '../store';

const API_BASE = 'http://localhost:8000';

export default function MedicalEvidence() {
  const { disease } = useTrialStore();
  const [data, setData] = useState({ trials: [], literature: [], adverse_events: [] });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchEvidence = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/simulation/evidence/${disease || 'type2_diabetes'}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEvidence();
  }, [disease]);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ padding: 12, background: 'rgba(59,130,246,0.15)', color: '#3b82f6', borderRadius: 14 }}>
            <BookOpen size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>Medical Evidence</h2>
            <p style={{ fontSize: 12, color: '#475569', margin: 0 }}>
              ClinicalTrials.gov · Europe PMC · OpenFDA — live data
            </p>
          </div>
        </div>
        <motion.button
          onClick={fetchEvidence}
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          style={{
            padding: '8px 16px', borderRadius: 10, border: '1px solid rgba(59,130,246,0.3)',
            background: 'rgba(59,130,246,0.1)', color: '#3b82f6',
            display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}
        >
          <RefreshCw size={12} /> Refresh
        </motion.button>
      </div>

      {loading && (
        <div style={{ color: '#475569', fontSize: 14, padding: 20, textAlign: 'center' }}>
          Fetching live medical data from ClinicalTrials.gov and Europe PMC…
        </div>
      )}

      {error && (
        <div style={{ padding: 16, background: 'rgba(239,68,68,0.1)', borderRadius: 12, color: '#ef4444', fontSize: 13 }}>
          ⚠️ Could not reach backend: {error}
        </div>
      )}

      {!loading && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 20, flex: 1, overflowY: 'auto', minHeight: 0 }}>
          {/* Clinical Trials */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: '#3b82f6', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
              <FlaskConical size={13} /> ClinicalTrials.gov ({data.trials?.length || 0})
            </h3>
            {(data.trials || []).length === 0 && <div style={{ color: '#334155', fontSize: 12 }}>No trials found</div>}
            {(data.trials || []).map((t, i) => (
              <motion.div key={i} whileHover={{ y: -2 }} style={{
                padding: '14px 16px', borderRadius: 12,
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(59,130,246,0.15)',
                borderLeft: '3px solid #3b82f6',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1.4, marginBottom: 8, color: '#e2e8f0' }}>
                  {t.title || 'Untitled Study'}
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, fontSize: 10 }}>
                  {t.phase && <Tag color="#3b82f6" label={`Phase: ${t.phase}`} />}
                  {t.status && <Tag color={t.status === 'Recruiting' ? '#10b981' : '#64748b'} label={t.status} />}
                  {t.country && <Tag color="#8b5cf6" label={t.country} />}
                  {t.enrollment && <Tag color="#f59e0b" label={`N=${t.enrollment}`} />}
                </div>
                {t.nct_id && (
                  <a
                    href={`https://clinicaltrials.gov/ct2/show/${t.nct_id}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 10, color: '#3b82f6', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3, marginTop: 8 }}
                  >
                    <ExternalLink size={9} /> {t.nct_id}
                  </a>
                )}
              </motion.div>
            ))}
          </div>

          {/* Literature */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: '#8b5cf6', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
              <BookOpen size={13} /> Europe PMC ({data.literature?.length || 0})
            </h3>
            {(data.literature || []).length === 0 && <div style={{ color: '#334155', fontSize: 12 }}>No literature found</div>}
            {(data.literature || []).map((l, i) => (
              <motion.div key={i} whileHover={{ y: -2 }} style={{
                padding: '14px 16px', borderRadius: 12,
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(139,92,246,0.15)',
                borderLeft: '3px solid #8b5cf6',
              }}>
                <div style={{ fontSize: 12, fontWeight: 700, lineHeight: 1.4, marginBottom: 6, color: '#e2e8f0' }}>
                  {l.title || 'Untitled'}
                </div>
                <div style={{ fontSize: 10, color: '#475569', marginBottom: 6 }}>
                  {l.first_author} · {l.journal} · {l.pub_year}
                </div>
                {l.doi && (
                  <a
                    href={`https://doi.org/${l.doi}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{ fontSize: 10, color: '#8b5cf6', textDecoration: 'none', display: 'flex', alignItems: 'center', gap: 3 }}
                  >
                    <ExternalLink size={9} /> DOI: {l.doi}
                  </a>
                )}
              </motion.div>
            ))}
          </div>

          {/* Adverse Events */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <h3 style={{ fontSize: 13, textTransform: 'uppercase', letterSpacing: 1.5, color: '#ef4444', margin: 0, display: 'flex', alignItems: 'center', gap: 6 }}>
              <AlertTriangle size={13} /> FDA Adverse Events ({data.adverse_events?.length || 0})
            </h3>
            {(data.adverse_events || []).length === 0 && <div style={{ color: '#334155', fontSize: 12 }}>No adverse events found</div>}
            {(data.adverse_events || []).map((ev, i) => (
              <motion.div key={i} whileHover={{ y: -2 }} style={{
                padding: '14px 16px', borderRadius: 12,
                background: 'rgba(239,68,68,0.04)', border: '1px solid rgba(239,68,68,0.15)',
                borderLeft: '3px solid #ef4444',
              }}>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 8 }}>
                  {(ev.outcome || []).slice(0, 4).map((r, j) => (
                    <span key={j} style={{
                      padding: '2px 6px', background: 'rgba(239,68,68,0.1)',
                      color: '#ef4444', borderRadius: 4, fontSize: 9, fontWeight: 800, textTransform: 'uppercase',
                    }}>
                      {r?.reactionmeddrapt || r}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: 10, color: '#64748b', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div style={{ width: 6, height: 6, borderRadius: '50%', background: ev.serious === '1' ? '#ef4444' : '#f59e0b' }} />
                  {ev.serious === '1' ? 'Serious Event' : 'Non-Serious'} · Report {ev.safety_report_id || i + 1}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function Tag({ color, label }) {
  return (
    <span style={{
      padding: '2px 7px', borderRadius: 4, fontSize: 9, fontWeight: 700,
      background: `${color}20`, color, border: `1px solid ${color}30`,
    }}>{label}</span>
  );
}
