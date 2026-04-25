import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Shield, Zap, ChevronRight, BarChart3, Database, Globe, ArrowDown } from 'lucide-react';

const LandingPage = ({ onStart }) => {
  return (
    <div className="min-h-screen relative flex flex-col items-center bg-dark overflow-hidden">
      {/* Background Decor */}
      <div className="glow top-[-10%] left-[-10%] w-[500px] h-[500px]" />
      <div className="glow bottom-[-10%] right-[-10%] w-[600px] h-[600px]" style={{ background: 'var(--accent-secondary)' }} />
      
      {/* Hero Section */}
      <section className="min-h-screen flex flex-col items-center justify-center px-4 relative z-10 text-center max-w-6xl">
        <motion.div 
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 1 }}
        >
          <span className="inline-block px-4 py-1.5 mb-6 text-sm font-semibold tracking-wider uppercase border border-glass-border rounded-full bg-white/5">
            Next-Gen Research Platform
          </span>
          <h1 className="text-7xl md:text-9xl font-extrabold mb-8 tracking-tighter leading-none">
            Clinical <br /><span className="gradient-text">Simulator 2.0</span>
          </h1>
          <p className="text-xl md:text-2xl text-text-muted mb-12 leading-relaxed max-w-3xl mx-auto">
            High-fidelity deterministic RL environment for clinical research. 
            Bridging the gap between computational models and real-world patient outcomes.
          </p>
          
          <div className="flex flex-wrap gap-6 justify-center mb-16">
            <button 
              onClick={onStart}
              className="px-10 py-5 bg-white text-black font-black text-lg rounded-full hover:scale-105 transition-transform flex items-center gap-3 shadow-[0_0_40px_rgba(255,255,255,0.2)]"
            >
              Launch Simulation <ChevronRight size={22} />
            </button>
            <button className="px-10 py-5 border-2 border-glass-border text-lg font-bold rounded-full hover:bg-white/5 transition-colors">
              Read Methodology
            </button>
          </div>
        </motion.div>

        <motion.div 
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
          className="absolute bottom-10"
        >
          <ArrowDown className="text-text-muted" size={32} />
        </motion.div>
      </section>

      {/* Features Grid - Centered Spaced */}
      <section className="py-32 px-4 w-full max-w-7xl relative z-10">
        <div className="text-center mb-20">
          <h2 className="text-4xl md:text-5xl font-bold mb-4">Core Capabilities</h2>
          <div className="h-1 w-20 bg-accent-primary mx-auto rounded-full" />
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          <FeatureCard 
            icon={<Zap className="text-accent-primary" size={40} />}
            title="PK/PD Fidelity"
            description="Complex Pharmacokinetic and Pharmacodynamic modeling simulating drug absorption, distribution, and effect curves."
          />
          <FeatureCard 
            icon={<Activity className="text-success" size={40} />}
            title="Disease Drift"
            description="Dynamic disease progression logic for NSCLC, Hypertension, and T2D that reacts to therapeutic interventions."
          />
          <FeatureCard 
            icon={<Shield className="text-accent-secondary" size={40} />}
            title="Policy Validation"
            description="Deterministic environment designed for training and stress-testing GRPO and neural-based trial policies."
          />
        </div>
      </section>

      {/* Scientific Foundation Section */}
      <section className="py-32 px-4 w-full bg-white/5 border-y border-glass-border">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center gap-16">
          <div className="flex-1">
            <h2 className="text-4xl md:text-5xl font-bold mb-8">Scientific <br /><span className="text-accent-primary">Grounding</span></h2>
            <p className="text-lg text-text-muted mb-8 leading-relaxed">
              Our simulator uses state-of-the-art biological modeling to create synthetic patient cohorts that respond to dose-level adjustments and therapy compositions with statistical accuracy.
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
              <div className="flex items-start gap-4">
                <BarChart3 className="text-accent-primary mt-1" />
                <div>
                  <h4 className="font-bold">Emax Models</h4>
                  <p className="text-sm text-text-muted">Non-linear drug response curves.</p>
                </div>
              </div>
              <div className="flex items-start gap-4">
                <Database className="text-accent-secondary mt-1" />
                <div>
                  <h4 className="font-bold">Prior Grounding</h4>
                  <p className="text-sm text-text-muted">Uses PubMed and FDA snapshots.</p>
                </div>
              </div>
            </div>
          </div>
          <div className="flex-1 w-full">
            <div className="liquid-glass aspect-video p-1 flex items-center justify-center overflow-hidden">
               <div className="w-full h-full bg-black/40 rounded-[22px] flex items-center justify-center">
                  <div className="text-accent-primary animate-pulse flex flex-col items-center">
                    <Globe size={80} />
                    <span className="mt-4 font-mono text-sm uppercase tracking-widest">System Visualization Active</span>
                  </div>
               </div>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-40 px-4 text-center">
        <h2 className="text-5xl md:text-7xl font-bold mb-10">Ready to simulate?</h2>
        <button 
          onClick={onStart}
          className="px-12 py-6 bg-white text-black font-black text-xl rounded-full hover:scale-105 transition-transform shadow-[0_0_60px_rgba(255,255,255,0.3)]"
        >
          Get Started Now
        </button>
      </section>

      <footer className="py-10 px-4 border-t border-glass-border w-full text-center text-text-muted text-sm">
        &copy; 2026 Clinical Trial Simulator 2.0. Research-Use Only.
      </footer>
    </div>
  );
};

const FeatureCard = ({ icon, title, description }) => (
  <motion.div 
    initial={{ opacity: 0, y: 20 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true }}
    whileHover={{ y: -12 }}
    className="liquid-glass p-10 glass-card h-full flex flex-col"
  >
    <div className="mb-8 p-4 bg-white/5 w-fit rounded-2xl">{icon}</div>
    <h3 className="text-2xl font-bold mb-4">{title}</h3>
    <p className="text-text-muted leading-relaxed flex-grow">{description}</p>
  </motion.div>
);

export default LandingPage;
