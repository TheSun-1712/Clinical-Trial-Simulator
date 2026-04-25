import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FlaskConical, BarChart2, Terminal, Sliders,
  Activity, Wifi, WifiOff, ChevronRight, Play, Pause, Globe
} from 'lucide-react';
import { useTrialStore } from './store';
import InteractiveTrial from './views/InteractiveTrial';
import PolicyBenchmarks from './views/PolicyBenchmarks';
import SystemLogs from './views/SystemLogs';
import PatientCohort from './views/PatientCohort';
import MedicalEvidence from './views/MedicalEvidence';
import DrugComposition from './views/DrugComposition';
import HindsightReplay from './views/HindsightReplay';
import AgentAnalysis from './views/AgentAnalysis';
import WorldMedicalNews from './views/WorldMedicalNews';
import ConfigModal from './components/ConfigModal';
import LandingPage from './LandingPage';
import { Users, BookOpen, Beaker, History, ShieldCheck } from 'lucide-react';

const NAV_ITEMS = [
  { id: 'trial', label: 'Interactive Trial', icon: FlaskConical, desc: 'Control Room' },
  { id: 'patients', label: 'Patient Cohort', icon: Users, desc: 'Subject Data' },
  { id: 'evidence', label: 'Medical Evidence', icon: BookOpen, desc: 'PubMed / FDA' },
  { id: 'composition', label: 'Drug Composition', icon: Beaker, desc: 'Ratios A/B/C' },
  { id: 'benchmarks', label: 'Policy Benchmarks', icon: BarChart2, desc: 'Analytics' },
  { id: 'agents', label: 'Agent Analysis', icon: ShieldCheck, desc: 'Logic & Reasoning' },
  { id: 'worldnews', label: 'Global Med News', icon: Globe, desc: 'Live World Map' },
  { id: 'hindsight', label: 'Hindsight Replay', icon: History, desc: 'Counterfactuals' },
  { id: 'logs', label: 'System Logs', icon: Terminal, desc: 'Audit Trail' },
];

function Sidebar({ active, setActive, onConfig, connected, isAutoRunning, setIsAutoRunning }) {
  return (
    <div style={{
      width: 240, flexShrink: 0, display: 'flex', flexDirection: 'column',
      background: 'rgba(10,12,20,0.7)', backdropFilter: 'blur(20px)',
      borderRight: '1px solid rgba(255,255,255,0.06)', padding: '24px 16px',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '0 8px', marginBottom: 32 }}>
        <div style={{
          width: 34, height: 34, borderRadius: 10,
          background: 'linear-gradient(135deg, #3b82f6, #8b5cf6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          boxShadow: '0 0 16px rgba(59,130,246,0.4)',
        }}>
          <Activity size={16} color="#fff" />
        </div>
        <div>
          <div style={{ fontWeight: 800, fontSize: 14, lineHeight: 1.2 }}>ClinicalSim</div>
          <div style={{ fontSize: 10, color: '#475569', letterSpacing: 1 }}>v2.0 · RL Environment</div>
        </div>
      </div>

      {/* Nav */}
      <nav style={{ flex: 1 }}>
        <div style={{ fontSize: 10, textTransform: 'uppercase', letterSpacing: 1.5, color: '#334155', padding: '0 8px', marginBottom: 8 }}>Navigation</div>
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = active === item.id;
          return (
            <motion.button
              key={item.id}
              id={`nav-${item.id}`}
              onClick={() => setActive(item.id)}
              whileHover={{ x: 2 }}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 12, padding: '10px 12px',
                borderRadius: 10, marginBottom: 4, border: 'none', cursor: 'pointer', textAlign: 'left',
                background: isActive ? 'rgba(59,130,246,0.15)' : 'transparent',
                transition: 'background 0.2s',
              }}
            >
              <Icon size={16} style={{ color: isActive ? '#3b82f6' : '#475569', flexShrink: 0 }} />
              <div>
                <div style={{ fontSize: 13, fontWeight: isActive ? 700 : 500, color: isActive ? '#f8fafc' : '#64748b' }}>{item.label}</div>
                <div style={{ fontSize: 10, color: '#334155' }}>{item.desc}</div>
              </div>
              {isActive && <ChevronRight size={12} style={{ marginLeft: 'auto', color: '#3b82f6' }} />}
            </motion.button>
          );
        })}
      </nav>

      {/* Config button */}
      <div style={{ borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: 16 }}>
        <motion.button
          id="btn-config"
          onClick={onConfig}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', gap: 10, padding: '10px 12px',
            borderRadius: 10, border: '1px solid rgba(255,255,255,0.07)',
            background: 'rgba(255,255,255,0.03)', cursor: 'pointer', color: '#64748b', fontSize: 13, fontWeight: 600, marginBottom: 8,
          }}
        >
          <Sliders size={14} />
          Configuration
        </motion.button>

        <motion.button
          onClick={() => setIsAutoRunning(!isAutoRunning)}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          style={{
            width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, padding: '10px 12px',
            borderRadius: 10, border: 'none',
            background: isAutoRunning ? '#ef4444' : '#10b981', cursor: 'pointer', color: '#ffffff', fontSize: 13, fontWeight: 800,
          }}
        >
          {isAutoRunning ? <><Pause size={14} /> STOP AGENT</> : <><Play size={14} /> START AGENT</>}
        </motion.button>

        {/* Connection Status */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 12px 0', fontSize: 11, color: '#334155' }}>
          {connected
            ? <><Wifi size={11} style={{ color: '#10b981' }} /><span style={{ color: '#10b981' }}>Backend Connected</span></>
            : <><WifiOff size={11} style={{ color: '#f59e0b' }} /><span style={{ color: '#f59e0b' }}>Offline / Mock Mode</span></>
          }
        </div>
      </div>
    </div>
  );
}

const VIEW_MAP = {
  trial: InteractiveTrial,
  patients: PatientCohort,
  evidence: MedicalEvidence,
  composition: DrugComposition,
  benchmarks: PolicyBenchmarks,
  agents: AgentAnalysis,
  worldnews: WorldMedicalNews,
  hindsight: HindsightReplay,
  logs: SystemLogs,
};

import axios from 'axios';
const API_BASE = 'http://localhost:8000';

export default function App() {
  const [showLanding, setShowLanding] = useState(true);
  const [activeView, setActiveView] = useState('trial');
  const [showConfig, setShowConfig] = useState(false);
  const { initialize, loading, error, sessionId, takeAction } = useTrialStore();
  const [isAutoRunning, setIsAutoRunning] = useState(false);
  const autoRunTimer = React.useRef(null);

  useEffect(() => { initialize(); }, []);

  const runAutoStep = React.useCallback(async () => {
    if (!sessionId || sessionId === 'offline-demo' || !isAutoRunning) return;
    try {
      const actionRes = await axios.post(`${API_BASE}/policy/action`, { session_id: sessionId });
      const { action_type, magnitude } = actionRes.data;
      await takeAction({ action_type, magnitude });
    } catch (err) {
      setIsAutoRunning(false);
    }
  }, [sessionId, isAutoRunning, takeAction]);

  useEffect(() => {
    if (isAutoRunning) {
      autoRunTimer.current = setInterval(runAutoStep, 2000);
    } else {
      clearInterval(autoRunTimer.current);
    }
    return () => clearInterval(autoRunTimer.current);
  }, [isAutoRunning, runAutoStep]);

  const ActiveView = VIEW_MAP[activeView];
  const connected = !!sessionId && sessionId !== 'offline-demo';

  if (showLanding) {
    return <LandingPage onStart={() => setShowLanding(false)} />;
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 20 }}>
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1.5, repeat: Infinity, ease: 'linear' }}>
          <Activity size={40} style={{ color: '#3b82f6' }} />
        </motion.div>
        <motion.p animate={{ opacity: [0.4, 1, 0.4] }} transition={{ duration: 1.5, repeat: Infinity }} style={{ color: '#475569', fontFamily: 'monospace' }}>
          Initializing Neural Environment...
        </motion.p>
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', position: 'relative', overflow: 'hidden' }}>
      {/* Background glows */}
      <div style={{ position: 'fixed', top: '-20%', left: '-10%', width: 500, height: 500, background: '#3b82f6', filter: 'blur(140px)', opacity: 0.07, borderRadius: '50%', pointerEvents: 'none' }} />
      <div style={{ position: 'fixed', bottom: '-20%', right: '-5%', width: 600, height: 600, background: '#8b5cf6', filter: 'blur(160px)', opacity: 0.06, borderRadius: '50%', pointerEvents: 'none' }} />

      <Sidebar active={activeView} setActive={setActiveView} onConfig={() => setShowConfig(true)} connected={connected} isAutoRunning={isAutoRunning} setIsAutoRunning={setIsAutoRunning} />

      {/* Main Content */}
      <main style={{ flex: 1, padding: '28px 32px', overflow: 'auto', display: 'flex', flexDirection: 'column' }}>
        <AnimatePresence mode="wait">
          <motion.div
            key={activeView}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -8 }}
            transition={{ duration: 0.25 }}
            style={{ flex: 1, display: 'flex', flexDirection: 'column' }}
          >
            {error && (
              <div style={{
                marginBottom: 16, padding: '12px 16px', borderRadius: 12,
                background: 'rgba(245,158,11,0.1)', border: '1px solid rgba(245,158,11,0.3)',
                color: '#f59e0b', fontSize: 13,
              }}>
                ⚠️ Backend unreachable — running in mock/demo mode. Start the API server on port 8000 for live data.
              </div>
            )}
            <ActiveView />
          </motion.div>
        </AnimatePresence>
      </main>

      {showConfig && <ConfigModal onClose={() => setShowConfig(false)} />}
    </div>
  );
}
