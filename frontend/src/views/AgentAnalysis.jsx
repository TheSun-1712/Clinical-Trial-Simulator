import React, { useEffect, useState, useRef } from 'react';
import { BarChart2, ShieldCheck, Activity, BookOpen, RefreshCw, TrendingUp, TrendingDown } from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  BarChart, Bar, Legend, RadarChart, PolarGrid, PolarAngleAxis, Radar
} from 'recharts';
import { motion } from 'framer-motion';
import { useTrialStore } from '../store';

const API_BASE = 'http://localhost:8000';

export default function AgentAnalysis() {
  const { sessionId, history } = useTrialStore();
  const [analysisData, setAnalysisData] = useState({ recent_rewards: [], reward_breakdown: [] });
  const [efficiencyData, setEfficiencyData] = useState([]);
  const [loading, setLoading] = useState(true);
  const timerRef = useRef(null);

  const fetchAnalytics = async () => {
    // Fetch agent analysis from live session
    if (sessionId && sessionId !== 'offline-demo') {
      try {
        const res = await fetch(`${API_BASE}/simulation/agent_analysis/${sessionId}`);
        if (res.ok) {
          const json = await res.json();
          setAnalysisData(json);
        }
      } catch (e) { /* pass */ }
    }

    // Fetch efficiency metrics
    try {
      const res = await fetch(`${API_BASE}/analytics/efficiency-by-disease`);
      const data = await res.json();
      if (data.disease_metrics) {
        const formatted = Object.entries(data.disease_metrics).map(([k, v]) => ({
          name: k.replace('_', ' '), value: +(v.mean_reward || 0).toFixed(2)
        }));
        setEfficiencyData(formatted);
      }
    } catch (e) { /* pass */ }
    setLoading(false);
  };

  useEffect(() => {
    fetchAnalytics();
    timerRef.current = setInterval(fetchAnalytics, 5000);
    return () => clearInterval(timerRef.current);
  }, [sessionId]);

  // Build reward timeline from store history
  const rewardTimeline = history.map((h, i) => ({
    week: h.week ?? i,
    reward: +(h.reward ?? 0).toFixed(3),
    efficacy: +(h.efficacy_signal_estimate ?? 0).toFixed(3),
    toxicity: +(h.cumulative_toxicity ?? 0).toFixed(3),
  }));

  // Build breakdown radar from last breakdown entry
  const lastBreakdown = analysisData.reward_breakdown?.[analysisData.reward_breakdown.length - 1] || {};
  const radarData = Object.entries(lastBreakdown).map(([k, v]) => ({
    metric: k.replace('_', ' '),
    value: Math.max(0, +((v ?? 0) + 1).toFixed(2)), // shift to positive for radar
  }));

  const agents = [
    { name: 'Safety Agent', icon: <ShieldCheck size={18} />, color: '#ef4444', desc: 'Monitors AE clusters and toxicity. Triggers dose reduction when cumulative toxicity > 0.6.' },
    { name: 'Efficacy Agent', icon: <Activity size={18} />, color: '#3b82f6', desc: 'Tracks biomarker signals vs baseline SoC. Endorses cohort scaling when efficacy > 0.7.' },
    { name: 'Regulatory Agent', icon: <BookOpen size={18} />, color: '#f59e0b', desc: 'Evaluates FDA sentiment and protocol compliance. Triggers interim filings on positive Phase II transitions.' },
  ];

  const latestReward = rewardTimeline[rewardTimeline.length - 1];
  const prevReward = rewardTimeline[rewardTimeline.length - 2];
  const rewardDelta = latestReward && prevReward ? (latestReward.reward - prevReward.reward) : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: 20 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ padding: 12, background: 'rgba(16,185,129,0.15)', color: '#10b981', borderRadius: 14 }}>
            <BarChart2 size={22} />
          </div>
          <div>
            <h2 style={{ fontSize: 26, fontWeight: 900, margin: 0 }}>Agent Analysis</h2>
            <p style={{ fontSize: 12, color: '#475569', margin: 0 }}>Live policy reasoning · Reward breakdown · Session history</p>
          </div>
        </div>
        <motion.button
          onClick={fetchAnalytics}
          whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}
          style={{
            padding: '8px 14px', borderRadius: 10, border: '1px solid rgba(16,185,129,0.3)',
            background: 'rgba(16,185,129,0.1)', color: '#10b981',
            display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', fontSize: 12, fontWeight: 700,
          }}
        >
          <RefreshCw size={12} /> Refresh
        </motion.button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20, flex: 1, minHeight: 0 }}>
        {/* Left col */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden' }}>
          {/* Reward Timeline */}
          <div className="liquid-glass" style={{ padding: 24, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ fontSize: 15, fontWeight: 800, margin: 0 }}>Reward Timeline</h3>
              {latestReward && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12 }}>
                  {rewardDelta >= 0
                    ? <TrendingUp size={14} style={{ color: '#10b981' }} />
                    : <TrendingDown size={14} style={{ color: '#ef4444' }} />}
                  <span style={{ color: rewardDelta >= 0 ? '#10b981' : '#ef4444', fontWeight: 700 }}>
                    {rewardDelta >= 0 ? '+' : ''}{rewardDelta.toFixed(3)}
                  </span>
                  <span style={{ color: '#475569' }}>vs prev step</span>
                </div>
              )}
            </div>
            {rewardTimeline.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
                Start the simulation to see reward trends
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%" minHeight={180}>
                <LineChart data={rewardTimeline} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="week" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                  <YAxis stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                  <Tooltip
                    contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }}
                  />
                  <Legend iconType="circle" iconSize={7} />
                  <Line type="monotone" dataKey="reward" stroke="#10b981" strokeWidth={2} dot={false} name="Total Reward" />
                  <Line type="monotone" dataKey="efficacy" stroke="#3b82f6" strokeWidth={1.5} dot={false} name="Efficacy" strokeDasharray="4 2" />
                  <Line type="monotone" dataKey="toxicity" stroke="#ef4444" strokeWidth={1.5} dot={false} name="Toxicity" strokeDasharray="2 3" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Agent Cards */}
          {agents.map((agent, i) => (
            <motion.div key={i} whileHover={{ x: 4 }} className="liquid-glass" style={{ padding: 16, borderLeft: `3px solid ${agent.color}` }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                <div style={{ color: agent.color }}>{agent.icon}</div>
                <h4 style={{ fontSize: 14, fontWeight: 800, margin: 0, color: agent.color }}>{agent.name}</h4>
              </div>
              <p style={{ color: '#64748b', fontSize: 12, lineHeight: 1.5, margin: 0 }}>{agent.desc}</p>
            </motion.div>
          ))}
        </div>

        {/* Right col */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16, overflow: 'hidden' }}>
          {/* Disease Efficiency Bar Chart */}
          <div className="liquid-glass" style={{ padding: 24, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h3 style={{ fontSize: 15, fontWeight: 800, margin: '0 0 16px 0' }}>Policy Efficiency by Disease</h3>
            {efficiencyData.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
                No benchmark data yet — run a benchmark first
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%" minHeight={180}>
                <BarChart data={efficiencyData} margin={{ top: 4, right: 8, left: -20, bottom: 0 }} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" horizontal={false} />
                  <XAxis type="number" stroke="#334155" tick={{ fontSize: 10, fill: '#475569' }} />
                  <YAxis dataKey="name" type="category" width={90} stroke="#334155" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                  <Bar dataKey="value" fill="#3b82f6" radius={[0, 4, 4, 0]} name="Mean Reward" />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>

          {/* Reward Breakdown Radar */}
          <div className="liquid-glass" style={{ padding: 24, flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
            <h3 style={{ fontSize: 15, fontWeight: 800, margin: '0 0 16px 0' }}>Reward Breakdown (Last Step)</h3>
            {radarData.length === 0 ? (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#334155', fontSize: 13 }}>
                No reward breakdown data yet
              </div>
            ) : (
              <ResponsiveContainer width="100%" height="100%" minHeight={160}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="rgba(255,255,255,0.06)" />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 10, fill: '#64748b' }} />
                  <Radar name="Reward" dataKey="value" stroke="#8b5cf6" fill="#8b5cf6" fillOpacity={0.3} />
                  <Tooltip contentStyle={{ background: '#0a0a14', border: '1px solid rgba(255,255,255,0.1)', borderRadius: 10, fontSize: 11 }} />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
