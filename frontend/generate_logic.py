import os

FRONTEND_SRC = r"c:\PROJECT\PEPto\frontend\src"

files = {
    "contexts/AuthContext.jsx": """import React, { createContext, useState, useEffect } from 'react';
import api from '../services/api';

export const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('access_token');
        if (token) {
            api.get('/api/auth/me')
               .then(res => setUser(res.data.data))
               .catch(() => localStorage.removeItem('access_token'))
               .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    }, []);

    const login = async (email, password) => {
        const res = await api.post('/api/auth/login', { email, password });
        localStorage.setItem('access_token', res.data.data.access_token);
        localStorage.setItem('refresh_token', res.data.data.refresh_token);
        setUser(res.data.data.user);
    };

    const logout = () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, loading, login, logout, isAuthenticated: !!user, isProvider: user?.role === 'provider' }}>
            {children}
        </AuthContext.Provider>
    );
};
""",
    "hooks/useAuth.js": """import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

export const useAuth = () => {
    return useContext(AuthContext);
};
""",
    "services/api.js": """import axios from 'react';

const api = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000',
    headers: {
        'Content-Type': 'application/json'
    }
});

api.interceptors.request.use(config => {
    const token = localStorage.getItem('access_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

export default api;
""",
    "utils/constants.js": """export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000';

export const SERVICE_CATEGORIES = [
    { value: 'grooming', label: 'Grooming', icon: '✂️', color: '#FF6584' },
    { value: 'vet', label: 'Vet Consultation', icon: '🩺', color: '#6C63FF' },
    { value: 'walking', label: 'Dog Walking', icon: '🦮', color: '#43D9AD' },
    { value: 'boarding', label: 'Pet Boarding', icon: '🏠', color: '#F6C90E' },
    { value: 'training', label: 'Training', icon: '🎾', color: '#3F72AF' },
];

export const BOOKING_STATUS_COLORS = {
    pending: 'bg-yellow-500/20 text-yellow-500',
    confirmed: 'bg-blue-500/20 text-blue-500',
    in_progress: 'bg-indigo-500/20 text-indigo-500',
    completed: 'bg-green-500/20 text-green-500',
    cancelled: 'bg-red-500/20 text-red-500',
    refunded: 'bg-slate-500/20 text-slate-500'
};

export const PET_SPECIES = ['dog', 'cat', 'bird', 'rabbit', 'fish', 'hamster', 'other'];
""",
    "utils/helpers.js": """export const formatCurrency = (amount, currency = 'INR') => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency }).format(amount);
};

export const getInitials = (name) => {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2);
};

export const getStatusColor = (status) => {
    const colors = {
        pending: 'yellow',
        confirmed: 'blue',
        completed: 'green',
        cancelled: 'red'
    };
    return colors[status] || 'slate';
};
"""
}

for filepath, content in files.items():
    full_path = os.path.join(FRONTEND_SRC, filepath)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)

print("Frontend hooks, contexts, services, and utils generated.")
