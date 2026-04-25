import React, { useRef } from 'react';
import { motion, useInView } from 'framer-motion';
import {
  ArrowRight, FlaskConical, BarChart2, GitBranch,
  CheckCircle2, AlertTriangle, Clock, Cpu
} from 'lucide-react';

/* ─── Design tokens (inline — no external deps) ─────────────────────────── */
const T = {
  blue:   '#3b82f6',
  violet: '#7c3aed',
  teal:   '#0d9488',
  slate:  '#0f172a',
  muted:  '#64748b',
  border: 'rgba(255,255,255,0.07)',
  glass:  'rgba(15,23,42,0.7)',
};

/* ─── Reusable fade-in-on-scroll ─────────────────────────────────────────── */
function FadeIn({ children, delay = 0, y = 16 }) {
  const ref = useRef(null);
  const visible = useInView(ref, { once: true, margin: '-60px' });
  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y }}
      animate={visible ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.55, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}

/* ─── Section wrapper ────────────────────────────────────────────────────── */
function Section({ children, style = {} }) {
  return (
    <section style={{ maxWidth: 1080, margin: '0 auto', padding: '96px 24px', ...style }}>
      {children}
    </section>
  );
}

/* ─── Pill label ─────────────────────────────────────────────────────────── */
function Eyebrow({ children, color = T.blue }) {
  return (
    <div style={{
      display: 'inline-flex', alignItems: 'center', gap: 6,
      padding: '4px 12px', borderRadius: 99,
      background: color + '18', border: `1px solid ${color}30`,
      fontSize: 12, fontWeight: 700, letterSpacing: '0.08em',
      textTransform: 'uppercase', color, marginBottom: 20,
    }}>
      {children}
    </div>
  );
}

/* ─── Main component ─────────────────────────────────────────────────────── */
export default function LandingPage({ onStart }) {
  return (
    <div style={{ background: T.slate, color: '#e2e8f0', fontFamily: "'Inter', system-ui, sans-serif", lineHeight: 1.6, overflowX: 'hidden' }}>

      {/* ── Ambient glows ── */}
      <div aria-hidden style={{ position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0 }}>
        <div style={{ position: 'absolute', top: '-20vh', left: '-15vw', width: '60vw', height: '60vw', maxWidth: 700, background: T.blue, filter: 'blur(160px)', opacity: 0.06, borderRadius: '50%' }} />
        <div style={{ position: 'absolute', bottom: '-20vh', right: '-10vw', width: '50vw', height: '50vw', maxWidth: 600, background: T.violet, filter: 'blur(180px)', opacity: 0.05, borderRadius: '50%' }} />
      </div>

      <div style={{ position: 'relative', zIndex: 1 }}>

        {/* ════════════════════════════════════════════
            NAV
        ════════════════════════════════════════════ */}
        <nav style={{
          position: 'sticky', top: 0, zIndex: 50,
          background: 'rgba(15,23,42,0.85)', backdropFilter: 'blur(16px)',
          borderBottom: `1px solid ${T.border}`,
          padding: '0 24px',
        }}>
          <div style={{ maxWidth: 1080, margin: '0 auto', height: 56, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{ width: 28, height: 28, borderRadius: 8, background: `linear-gradient(135deg, ${T.blue}, ${T.violet})`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <FlaskConical size={14} color="#fff" />
              </div>
              <span style={{ fontWeight: 800, fontSize: 15 }}>ClinicalSim</span>
            </div>
            <motion.button
              id="nav-cta"
              onClick={onStart}
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '8px 16px', background: T.blue, border: 'none', borderRadius: 8, color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
            >
              Open Simulator <ArrowRight size={13} />
            </motion.button>
          </div>
        </nav>

        {/* ════════════════════════════════════════════
            HERO — value prop in one sentence
        ════════════════════════════════════════════ */}
        <Section style={{ paddingTop: 140, paddingBottom: 100, textAlign: 'center' }}>
          <FadeIn>
            <Eyebrow color={T.teal}><Cpu size={11} /> Deterministic RL Environment</Eyebrow>
          </FadeIn>

          <FadeIn delay={0.08}>
            <h1 style={{ fontSize: 'clamp(36px, 6vw, 72px)', fontWeight: 900, letterSpacing: '-0.03em', lineHeight: 1.08, marginBottom: 24, color: '#f8fafc' }}>
              Train AI policies on<br />
              <span style={{ background: `linear-gradient(135deg, ${T.blue}, ${T.violet})`, WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                clinical trial dynamics
              </span>
              <br />— without a single patient.
            </h1>
          </FadeIn>

          <FadeIn delay={0.14}>
            <p style={{ fontSize: 18, color: '#94a3b8', maxWidth: 560, margin: '0 auto 40px', lineHeight: 1.75 }}>
              A seeded, deterministic simulator for clinical trial coordination.
              Benchmark random, heuristic, and trained GRPO policies against the same
              reproducible environment. Every reward is logged and verifiable.
            </p>
          </FadeIn>

          <FadeIn delay={0.2}>
            <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
              <motion.button
                id="hero-cta-primary"
                onClick={onStart}
                whileHover={{ scale: 1.04, boxShadow: `0 0 32px ${T.blue}60` }}
                whileTap={{ scale: 0.97 }}
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: T.blue, border: 'none', borderRadius: 10, color: '#fff', fontSize: 15, fontWeight: 800, cursor: 'pointer', boxShadow: `0 0 20px ${T.blue}40` }}
              >
                Launch the Simulator <ArrowRight size={16} />
              </motion.button>
              <a
                href="#how-it-works"
                style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '14px 28px', background: 'transparent', border: `1px solid ${T.border}`, borderRadius: 10, color: '#94a3b8', fontSize: 15, fontWeight: 600, cursor: 'pointer', textDecoration: 'none', transition: 'border-color 0.2s, color 0.2s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = '#475569'; e.currentTarget.style.color = '#f1f5f9'; }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = T.border; e.currentTarget.style.color = '#94a3b8'; }}
              >
                How it works
              </a>
            </div>
          </FadeIn>

          {/* Live metric strip */}
          <FadeIn delay={0.28}>
            <div style={{ display: 'flex', justifyContent: 'center', gap: 48, flexWrap: 'wrap', marginTop: 72, paddingTop: 40, borderTop: `1px solid ${T.border}` }}>
              {[
                { value: '3', label: 'Disease models (T2D, HTN, NSCLC)' },
                { value: '5', label: 'Reward components, independently logged' },
                { value: '100%', label: 'Deterministic — same seed, same outcome' },
                { value: 'GRPO', label: 'Training backend supported' },
              ].map((m) => (
                <div key={m.label} style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: 28, fontWeight: 900, color: '#f8fafc', letterSpacing: '-0.02em' }}>{m.value}</div>
                  <div style={{ fontSize: 12, color: T.muted, marginTop: 4, maxWidth: 140 }}>{m.label}</div>
                </div>
              ))}
            </div>
          </FadeIn>
        </Section>

        {/* ════════════════════════════════════════════
            PROBLEM — why this exists
        ════════════════════════════════════════════ */}
        <div style={{ background: 'rgba(255,255,255,0.02)', borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
          <Section>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 40, alignItems: 'center' }}>
              <FadeIn>
                <Eyebrow color="#ef4444"><AlertTriangle size={11} /> The Problem</Eyebrow>
                <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.15, marginBottom: 20, color: '#f8fafc' }}>
                  Evaluating trial policies is expensive, slow, and irreversible.
                </h2>
                <p style={{ color: '#94a3b8', fontSize: 16, lineHeight: 1.8 }}>
                  Clinical trial design decisions — dosing, recruitment rate, reporting cadence — have massive downstream consequences. Simulating the wrong policy in a real trial costs months and patient safety. But most "simulators" are either too simple to be useful, or too stochastic to benchmark against reliably.
                </p>
              </FadeIn>
              <FadeIn delay={0.1}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                  {[
                    { icon: <Clock size={18} />, text: 'Phase II trials take 2–5 years. A bad policy discovered at year 3 is catastrophic.' },
                    { icon: <GitBranch size={18} />, text: 'Stochastic environments can\'t be reliably benchmarked — you don\'t know if improvement is signal or noise.' },
                    { icon: <BarChart2 size={18} />, text: 'Most RL research uses toy environments that don\'t reflect real pharmacokinetic dynamics.' },
                  ].map((item, i) => (
                    <div key={i} style={{ display: 'flex', gap: 14, padding: '16px 20px', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)', borderRadius: 12 }}>
                      <span style={{ color: '#ef4444', flexShrink: 0, marginTop: 1 }}>{item.icon}</span>
                      <p style={{ color: '#94a3b8', fontSize: 14, lineHeight: 1.7, margin: 0 }}>{item.text}</p>
                    </div>
                  ))}
                </div>
              </FadeIn>
            </div>
          </Section>
        </div>

        {/* ════════════════════════════════════════════
            SOLUTION — what it does
        ════════════════════════════════════════════ */}
        <Section>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 40, alignItems: 'center' }}>
            <FadeIn delay={0.05}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                {[
                  { title: 'Seeded determinism', body: 'Set a seed, get the exact same environment every run. Compare policies fairly — apples to apples.' },
                  { title: 'Verified reward components', body: 'Each reward signal (efficacy, toxicity, FDA compliance, cost) is logged independently. You can see exactly why a policy scored what it did.' },
                  { title: 'PK/PD-grounded dynamics', body: 'Drug concentration, Emax dose-response, and disease progression are modeled from published pharmacological priors — not arbitrary numbers.' },
                  { title: 'API-first, policy-agnostic', body: 'OpenEnv-compatible REST API. Bring any policy: random baselines, hand-coded heuristics, or a GRPO-trained LLM.' },
                ].map((item, i) => (
                  <FadeIn key={i} delay={i * 0.06}>
                    <div style={{ display: 'flex', gap: 14, padding: '18px 20px', background: 'rgba(59,130,246,0.05)', border: `1px solid ${T.border}`, borderRadius: 12, transition: 'border-color 0.2s' }}
                      onMouseEnter={e => e.currentTarget.style.borderColor = T.blue + '40'}
                      onMouseLeave={e => e.currentTarget.style.borderColor = T.border}
                    >
                      <CheckCircle2 size={18} color={T.teal} style={{ flexShrink: 0, marginTop: 2 }} />
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 14, color: '#f1f5f9', marginBottom: 4 }}>{item.title}</div>
                        <div style={{ fontSize: 13, color: '#64748b', lineHeight: 1.7 }}>{item.body}</div>
                      </div>
                    </div>
                  </FadeIn>
                ))}
              </div>
            </FadeIn>
            <FadeIn delay={0.1}>
              <Eyebrow color={T.teal}><CheckCircle2 size={11} /> The Solution</Eyebrow>
              <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, letterSpacing: '-0.02em', lineHeight: 1.15, marginBottom: 20, color: '#f8fafc' }}>
                A reproducible environment built for policy research, not demos.
              </h2>
              <p style={{ color: '#94a3b8', fontSize: 16, lineHeight: 1.8 }}>
                ClinicalSim gives clinical AI researchers a deterministic, PK/PD-grounded environment where every policy decision has a measurable, reproducible consequence. It's not a toy. It's a benchmark infrastructure.
              </p>
            </FadeIn>
          </div>
        </Section>

        {/* ════════════════════════════════════════════
            HOW IT WORKS
        ════════════════════════════════════════════ */}
        <div id="how-it-works" style={{ background: 'rgba(255,255,255,0.02)', borderTop: `1px solid ${T.border}`, borderBottom: `1px solid ${T.border}` }}>
          <Section style={{ textAlign: 'center' }}>
            <FadeIn>
              <Eyebrow color={T.violet}><GitBranch size={11} /> How It Works</Eyebrow>
              <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 16, color: '#f8fafc' }}>
                Three steps from policy idea to benchmark result.
              </h2>
              <p style={{ color: '#64748b', fontSize: 16, maxWidth: 520, margin: '0 auto 64px' }}>
                No data pipeline. No patient recruitment. No waiting.
              </p>
            </FadeIn>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: 24, textAlign: 'left' }}>
              {[
                {
                  step: '01',
                  title: 'Configure the environment',
                  body: 'Choose a disease model (Type 2 Diabetes, NSCLC, Hypertension), set a seed, and select your reward mode. The environment state is fully reproducible from these parameters.',
                  color: T.blue,
                },
                {
                  step: '02',
                  title: 'Submit actions via API',
                  body: 'Your policy calls POST /openenv/step with an action (recruit patients, adjust dose, file a report, or wait). The environment evolves according to PK/PD dynamics and returns the new state plus a decomposed reward.',
                  color: T.violet,
                },
                {
                  step: '03',
                  title: 'Benchmark and iterate',
                  body: 'Compare your policy against random and heuristic baselines across total reward, trial success rate, and cost — all on the exact same seed. Train with GRPO or any RL framework and see verifiable improvement.',
                  color: T.teal,
                },
              ].map((item, i) => (
                <FadeIn key={i} delay={i * 0.1}>
                  <div style={{ padding: '28px', background: T.glass, border: `1px solid ${T.border}`, borderRadius: 16, height: '100%', backdropFilter: 'blur(12px)' }}>
                    <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.1em', color: item.color, marginBottom: 16 }}>STEP {item.step}</div>
                    <h3 style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9', marginBottom: 12, lineHeight: 1.3 }}>{item.title}</h3>
                    <p style={{ fontSize: 14, color: '#64748b', lineHeight: 1.8, margin: 0 }}>{item.body}</p>
                  </div>
                </FadeIn>
              ))}
            </div>
          </Section>
        </div>

        {/* ════════════════════════════════════════════
            USE CASES — real scenarios
        ════════════════════════════════════════════ */}
        <Section>
          <FadeIn>
            <Eyebrow><FlaskConical size={11} /> Use Cases</Eyebrow>
            <h2 style={{ fontSize: 'clamp(28px, 4vw, 42px)', fontWeight: 800, letterSpacing: '-0.02em', marginBottom: 16, color: '#f8fafc' }}>
              Who uses this, and for what.
            </h2>
            <p style={{ color: '#64748b', fontSize: 16, marginBottom: 56, maxWidth: 600 }}>
              Concrete scenarios where a deterministic clinical RL environment makes the work faster and more credible.
            </p>
          </FadeIn>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: 20 }}>
            {[
              {
                audience: 'ML Researchers',
                scenario: 'You\'re publishing a clinical decision-making paper. You need a reproducible baseline environment so reviewers can run your benchmark independently.',
                outcome: 'Use seed=42, share the config. Anyone can reproduce your results exactly.',
                color: T.blue,
              },
              {
                audience: 'Clinical AI Teams',
                scenario: 'You\'ve trained a GRPO-based trial coordinator. You need to prove it outperforms a heuristic without running a real trial.',
                outcome: 'Run the benchmark table. Policy scores on identical environment conditions — no cherry-picking.',
                color: T.violet,
              },
              {
                audience: 'Safety Researchers',
                scenario: 'You want to stress-test a dosing policy to see when it triggers FDA warning flags or causes toxicity accumulation.',
                outcome: 'Each reward component (toxicity, FDA sentiment) is logged separately. Failure modes are traceable.',
                color: T.teal,
              },
            ].map((uc, i) => (
              <FadeIn key={i} delay={i * 0.08}>
                <div style={{ padding: '28px', background: T.glass, border: `1px solid ${T.border}`, borderRadius: 16, backdropFilter: 'blur(12px)', display: 'flex', flexDirection: 'column', gap: 16 }}>
                  <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: '0.1em', color: uc.color }}>{uc.audience.toUpperCase()}</div>
                  <p style={{ fontSize: 14, color: '#94a3b8', lineHeight: 1.75, margin: 0 }}>
                    <em>"{uc.scenario}"</em>
                  </p>
                  <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: `1px solid ${T.border}`, fontSize: 13, color: '#f1f5f9', display: 'flex', gap: 8, alignItems: 'flex-start' }}>
                    <CheckCircle2 size={14} color={uc.color} style={{ flexShrink: 0, marginTop: 2 }} />
                    {uc.outcome}
                  </div>
                </div>
              </FadeIn>
            ))}
          </div>
        </Section>

        {/* ════════════════════════════════════════════
            FINAL CTA
        ════════════════════════════════════════════ */}
        <div style={{ borderTop: `1px solid ${T.border}` }}>
          <Section style={{ textAlign: 'center', paddingBottom: 120 }}>
            <FadeIn>
              <h2 style={{ fontSize: 'clamp(32px, 5vw, 56px)', fontWeight: 900, letterSpacing: '-0.03em', color: '#f8fafc', marginBottom: 20, lineHeight: 1.1 }}>
                Start benchmarking your policy today.
              </h2>
              <p style={{ color: '#64748b', fontSize: 16, maxWidth: 480, margin: '0 auto 40px', lineHeight: 1.75 }}>
                No signup. No server setup required. The environment runs locally and falls back to demo mode if no backend is available.
              </p>
              <motion.button
                id="footer-cta"
                onClick={onStart}
                whileHover={{ scale: 1.04, boxShadow: `0 0 40px ${T.blue}50` }}
                whileTap={{ scale: 0.97 }}
                style={{ display: 'inline-flex', alignItems: 'center', gap: 10, padding: '16px 36px', background: T.blue, border: 'none', borderRadius: 12, color: '#fff', fontSize: 16, fontWeight: 800, cursor: 'pointer', boxShadow: `0 0 24px ${T.blue}30` }}
              >
                Open the Simulator <ArrowRight size={18} />
              </motion.button>
              <div style={{ marginTop: 20, fontSize: 12, color: '#334155' }}>
                Works in demo mode without a backend · Apache 2.0 open source
              </div>
            </FadeIn>
          </Section>
        </div>

        {/* Footer */}
        <footer style={{ borderTop: `1px solid ${T.border}`, padding: '24px', textAlign: 'center', fontSize: 12, color: '#334155' }}>
          ClinicalSim · Research-use only · Not for clinical deployment
        </footer>

      </div>
    </div>
  );
}
