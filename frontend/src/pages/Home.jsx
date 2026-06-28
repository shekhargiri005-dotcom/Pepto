import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import { SERVICE_CATEGORIES } from '../utils/constants';

const Home = () => {
  const navigate = useNavigate();
  return (
    <div className="min-h-screen text-slate-200">
      {/* Hero Section */}
      <section className="relative pt-32 pb-20 px-6 flex flex-col items-center text-center overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-[#0F0F1A] via-[#1A1A2E] to-[#6C63FF]/20 -z-10" />
        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-5xl md:text-7xl font-bold mb-6 tracking-tight"
        >
          Every Pet Deserves <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#6C63FF] to-[#FF6584]">the Best Care</span>
        </motion.h1>
        <p className="text-xl text-slate-400 mb-10 max-w-2xl">Find trusted groomers, vets, walkers & more near you. Fast, reliable, and paw-fect.</p>
        
        <div className="glass p-4 rounded-full max-w-2xl w-full flex items-center shadow-2xl">
          <input type="text" placeholder="City or zip code" className="bg-transparent border-none outline-none px-6 py-3 w-1/2" />
          <div className="w-[1px] h-10 bg-slate-700 mx-2" />
          <select className="bg-transparent border-none outline-none px-4 py-3 w-1/3 text-slate-300">
            <option value="">All Services</option>
            {SERVICE_CATEGORIES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
          <button onClick={() => navigate('/search')} className="gradient-btn px-8 py-3 rounded-full text-white font-medium hover:opacity-90 transition-opacity ml-auto">Search</button>
        </div>
      </section>
    </div>
  );
};
export default Home;
