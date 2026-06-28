import React from 'react';
import { Link } from 'react-router-dom';
const Navbar = () => {
    return (
        <nav className="fixed top-0 w-full z-50 glass border-b border-slate-800">
            <div className="max-w-7xl mx-auto px-6 h-20 flex items-center justify-between">
                <Link to="/" className="text-2xl font-bold flex items-center gap-2">
                    🐾 <span className="bg-clip-text text-transparent bg-gradient-to-r from-[#6C63FF] to-[#FF6584]">Pepto</span>
                </Link>
                <div className="flex gap-6 items-center">
                    <Link to="/search" className="hover:text-white text-slate-300">Find Services</Link>
                    <Link to="/login" className="hover:text-white text-slate-300">Login</Link>
                    <Link to="/register" className="gradient-btn px-6 py-2 rounded-full text-white">Sign Up</Link>
                </div>
            </div>
        </nav>
    );
};
export default Navbar;
