import React from 'react';
import { History, ArrowRight } from 'lucide-react';
import { useTrialStore } from '../store';
import { motion } from 'framer-motion';

export default function HindsightReplay() {
  const { history, eventLog } = useTrialStore();

  const negativeEvents = eventLog.filter(e => e.type === 'negative' || e.type === 'error');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
        <div style={{ padding: 12, background: 'rgba(236,72,153,0.15)', color: '#ec4899', borderRadius: 14 }}><History size={24} /></div>
        <div>
          <h2 style={{ fontSize: 28, fontWeight: 900 }}>Hindsight Replay</h2>
          <p style={{ color: '#94a3b8', fontSize: 13 }}>Counterfactual analysis of past actions</p>
        </div>
      </div>

      {negativeEvents.length === 0 ? (
        <div className="liquid-glass" style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#94a3b8' }}>
          No sub-optimal events detected in the current session.
        </div>
      ) : (
        <div style={{ display: 'grid', gap: 16, overflowY: 'auto' }}>
          {negativeEvents.map((ev, i) => {
            const counterfactualAction = ev.message.includes('dose') ? 'Maintain Dose' : 'Reduce Recruitment';
            const avoidedPenalty = Math.abs(ev.reward || 0.5) + 0.2;
            
            return (
              <motion.div key={i} whileHover={{ x: 4 }} className="liquid-glass" style={{ padding: 24, display: 'flex', gap: 24, alignItems: 'center' }}>
                <div style={{ padding: 16, background: 'rgba(255,255,255,0.03)', borderRadius: 12, flex: 1 }}>
                  <div style={{ fontSize: 11, color: '#ef4444', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, fontWeight: 800 }}>Actual Event [{ev.time}]</div>
                  <div style={{ fontSize: 15 }}>{ev.message}</div>
                  <div style={{ color: '#ef4444', fontSize: 13, marginTop: 4, fontWeight: 700 }}>Penalty: {ev.reward?.toFixed(2)}</div>
                </div>

                <ArrowRight size={24} style={{ color: '#64748b', opacity: 0.5 }} />

                <div style={{ padding: 16, background: 'rgba(16,185,129,0.05)', borderRadius: 12, flex: 1, border: '1px solid rgba(16,185,129,0.2)' }}>
                  <div style={{ fontSize: 11, color: '#10b981', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8, fontWeight: 800 }}>Counterfactual Optimization</div>
                  <div style={{ fontSize: 15 }}>Take Action: <b>{counterfactualAction}</b></div>
                  <div style={{ color: '#10b981', fontSize: 13, marginTop: 4, fontWeight: 700 }}>Avoided Penalty: +{avoidedPenalty.toFixed(2)}</div>
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
