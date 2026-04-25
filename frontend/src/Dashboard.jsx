import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Activity, Beaker, Users, AlertTriangle, TrendingUp, ChevronLeft } from 'lucide-react';

const API_BASE = 'http://localhost:8000';

const Dashboard = ({ onBack }) => {
  const [session, setSession] = useState(null);
  const [observation, setObservation] = useState(null);
  const [history, setHistory] = useState([]);
  const [diseases, setDiseases] = useState({});
  const [selectedDisease, setSelectedDisease] = useState('type2_diabetes');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const init = async () => {
      try {
        const [profilesRes, resetRes] = await Promise.all([
          axios.get(`${API_BASE}/simulation/disease-profiles`),
          axios.post(`${API_BASE}/openenv/reset`, {})
        ]);
        setDiseases(profilesRes.data.profiles);
        setSession(resetRes.data.session_id);
        setObservation(resetRes.data.observation);
        setHistory([resetRes.data.observation]);
        setLoading(false);
      } catch (err) {
        console.error("Initialization failed", err);
        setError("Could not connect to simulation server. Please ensure the backend is running on port 8000.");
        setLoading(false);
      }
    };
    init();
  }, []);

  const handleDiseaseChange = async (disease) => {
    if (!session) return;
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/simulation/select-disease`, {
        session_id: session,
        disease
      });
      setSelectedDisease(disease);
      setObservation(res.data.observation);
      setHistory([res.data.observation]);
    } catch (err) {
      console.error("Disease change failed", err);
    }
    setLoading(false);
  };

  const handleStep = async (actionType, magnitude = 1.0) => {
    if (!session) return;
    try {
      const res = await axios.post(`${API_BASE}/openenv/step`, {
        session_id: session,
        action_type: actionType,
        magnitude
      });
      setObservation(res.data.observation);
      setHistory([...history, res.data.observation]);
    } catch (err) {
      console.error("Step failed", err);
    }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-2xl font-bold gradient-text animate-pulse">Initializing Neural Environment...</div>;

  if (error) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center p-4 text-center">
        <AlertTriangle size={64} className="text-error mb-6" />
        <h2 className="text-3xl font-bold mb-4">Connection Failed</h2>
        <p className="text-text-muted mb-8 max-w-md">{error}</p>
        <button 
          onClick={() => window.location.reload()}
          className="px-8 py-3 bg-white text-black font-bold rounded-full hover:scale-105 transition-transform"
        >
          Retry Connection
        </button>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-[1600px] mx-auto min-h-screen">
      <header className="flex justify-between items-center mb-10">
        <div className="flex items-center gap-4">
          <button onClick={onBack} className="p-2 hover:bg-white/5 rounded-full transition-colors">
            <ChevronLeft size={24} />
          </button>
          <div>
            <h2 className="text-3xl font-bold">Simulator <span className="text-accent-primary">Dashboard</span></h2>
            <p className="text-text-muted">Interactive Session: {session?.slice(0, 8)}</p>
          </div>
        </div>
        
        <div className="flex gap-2">
          {Object.keys(diseases).map(d => (
            <button
              key={d}
              onClick={() => handleDiseaseChange(d)}
              className={`px-4 py-2 rounded-xl transition-all ${selectedDisease === d ? 'bg-accent-primary text-white shadow-lg shadow-accent-primary/20' : 'bg-white/5 hover:bg-white/10'}`}
            >
              {diseases[d].name}
            </button>
          ))}
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard icon={<Users />} label="Active Subjects" value={observation.active} color="var(--accent-primary)" />
        <StatCard icon={<Beaker />} label="Drug Concentration" value={observation.drug_concentration.toFixed(3)} color="var(--accent-secondary)" />
        <StatCard icon={<TrendingUp />} label="Efficacy Signal" value={(observation.efficacy_signal_estimate * 100).toFixed(1) + '%'} color="var(--success)" />
        <StatCard icon={<AlertTriangle />} label="Cum. Toxicity" value={observation.cumulative_toxicity.toFixed(3)} color="var(--error)" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2 liquid-glass p-8 min-h-[500px]">
          <h3 className="text-xl font-bold mb-6">Trial Trajectory</h3>
          <ResponsiveContainer width="100%" height={400}>
            <AreaChart data={history}>
              <defs>
                <linearGradient id="colorEff" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="var(--accent-primary)" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="var(--accent-primary)" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
              <XAxis dataKey="week" stroke="var(--text-muted)" />
              <YAxis stroke="var(--text-muted)" />
              <Tooltip 
                contentStyle={{ background: 'var(--bg-dark)', border: '1px solid var(--glass-border)', borderRadius: '12px' }}
              />
              <Area type="monotone" dataKey="efficacy_signal_estimate" name="Efficacy" stroke="var(--accent-primary)" fillOpacity={1} fill="url(#colorEff)" />
              <Area type="monotone" dataKey="cumulative_toxicity" name="Toxicity" stroke="var(--error)" fillOpacity={0.1} fill="var(--error)" />
              <Line type="monotone" dataKey="drug_concentration" name="Concentration" stroke="var(--accent-secondary)" dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="liquid-glass p-8 flex flex-col justify-between">
          <div>
            <h3 className="text-xl font-bold mb-6">Action Control</h3>
            <div className="grid grid-cols-1 gap-4">
              <ActionButton onClick={() => handleStep('recruit', 5)} label="Recruit +5 Patients" />
              <ActionButton onClick={() => handleStep('adjust_dose', 0.1)} label="Increase Dose (+0.1)" color="var(--accent-secondary)" />
              <ActionButton onClick={() => handleStep('adjust_dose', -0.1)} label="Decrease Dose (-0.1)" color="var(--warning)" />
              <ActionButton onClick={() => handleStep('file_interim_report')} label="File Interim Report" color="var(--success)" />
              <ActionButton onClick={() => handleStep('noop')} label="Wait 1 Week" color="var(--text-muted)" />
            </div>
          </div>
          
          <div className="mt-8 pt-8 border-t border-white/5">
            <h4 className="font-bold mb-2">FDA Sentiment</h4>
            <div className="flex items-center gap-4">
              <div className={`w-3 h-3 rounded-full ${observation.fda_flag === 'monitoring' ? 'bg-success' : observation.fda_flag === 'warning' ? 'bg-warning' : 'bg-error'}`} />
              <span className="capitalize">{observation.fda_flag}</span>
              <span className="text-text-muted ml-auto">{(observation.fda_sentiment * 100).toFixed(0)}% Approval</span>
            </div>
          </div>
        </div>
      </div>
      
      <div className="mt-8 liquid-glass p-8">
        <h3 className="text-xl font-bold mb-6">Disease Progression Metric: <span className="gradient-text">{diseases[selectedDisease]?.metric_name}</span></h3>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis dataKey="week" hide />
            <YAxis domain={['auto', 'auto']} stroke="var(--text-muted)" />
            <Tooltip contentStyle={{ background: 'var(--bg-dark)', border: '1px solid var(--glass-border)', borderRadius: '12px' }} />
            <Line type="step" dataKey="disease_progression" name="Progression" stroke="var(--accent-secondary)" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};

const StatCard = ({ icon, label, value, color }) => (
  <motion.div 
    whileHover={{ scale: 1.02 }}
    className="liquid-glass p-6 flex items-center gap-6"
  >
    <div className="p-4 rounded-2xl" style={{ backgroundColor: color + '20', color }}>
      {icon}
    </div>
    <div>
      <p className="text-text-muted text-sm">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  </motion.div>
);

const ActionButton = ({ label, onClick, color = 'var(--accent-primary)' }) => (
  <button
    onClick={onClick}
    className="w-full py-3 rounded-xl font-bold transition-all hover:brightness-110 active:scale-95"
    style={{ border: `1px solid ${color}`, color }}
  >
    {label}
  </button>
);

export default Dashboard;
