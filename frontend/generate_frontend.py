import os

FRONTEND_SRC = r"c:\PROJECT\PEPto\frontend\src"

files = {
    "pages/Home.jsx": """import React from 'react';
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
""",
    "pages/Search.jsx": """import React from 'react';
const Search = () => {
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Search Services</h1><p>Map and list view coming here.</p></div>;
};
export default Search;
""",
    "pages/ProviderProfile.jsx": """import React from 'react';
import { useParams } from 'react-router-dom';
const ProviderProfile = () => {
    const { id } = useParams();
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Provider Profile {id}</h1></div>;
};
export default ProviderProfile;
""",
    "pages/BookingFlow.jsx": """import React from 'react';
import { useParams } from 'react-router-dom';
const BookingFlow = () => {
    const { providerId, serviceId } = useParams();
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Book Service</h1><p>Booking {serviceId} from {providerId}</p></div>;
};
export default BookingFlow;
""",
    "pages/Auth/Login.jsx": """import React, from 'react';
import { useAuth } from '../../hooks/useAuth';
const Login = () => {
    return <div className="flex min-h-screen items-center justify-center p-8 mt-20"><div className="glass p-10 rounded-2xl w-full max-w-md"><h1 className="text-3xl font-bold mb-6">Login</h1><p>Login form here</p></div></div>;
};
export default Login;
""",
    "pages/Auth/Register.jsx": """import React from 'react';
const Register = () => {
    return <div className="flex min-h-screen items-center justify-center p-8 mt-20"><div className="glass p-10 rounded-2xl w-full max-w-md"><h1 className="text-3xl font-bold mb-6">Create Account</h1><p>Register form here</p></div></div>;
};
export default Register;
""",
    "pages/Dashboard/CustomerDashboard.jsx": """import React from 'react';
const CustomerDashboard = () => {
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">My Dashboard</h1></div>;
};
export default CustomerDashboard;
""",
    "pages/Dashboard/ProviderDashboard.jsx": """import React from 'react';
const ProviderDashboard = () => {
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">Provider Dashboard</h1></div>;
};
export default ProviderDashboard;
""",
    "pages/PetManager.jsx": """import React from 'react';
const PetManager = () => {
    return <div className="p-8 mt-20"><h1 className="text-3xl font-bold">My Pets</h1></div>;
};
export default PetManager;
""",
    "components/layout/Navbar.jsx": """import React from 'react';
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
""",
    "components/layout/Footer.jsx": """import React from 'react';
const Footer = () => {
    return <footer className="bg-[#0F0F1A] border-t border-slate-800 py-12 text-center text-slate-500"><p>© 2026 Pepto. All rights reserved.</p></footer>;
};
export default Footer;
""",
    "components/ui/PrivateRoute.jsx": """import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

const PrivateRoute = ({ children }) => {
    const { isAuthenticated, loading } = useAuth();
    if (loading) return <div>Loading...</div>;
    return isAuthenticated ? children : <Navigate to="/login" />;
};
export default PrivateRoute;
"""
}

for filepath, content in files.items():
    full_path = os.path.join(FRONTEND_SRC, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Frontend base pages and layout components generated successfully.")
