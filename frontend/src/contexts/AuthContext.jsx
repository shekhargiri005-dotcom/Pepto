import React, { createContext, useState, useEffect } from 'react';
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
