import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext.jsx';
import { NotificationProvider } from './contexts/NotificationContext.jsx';
import Navbar from './components/layout/Navbar.jsx';
import Footer from './components/layout/Footer.jsx';
import PrivateRoute from './components/ui/PrivateRoute.jsx';
import ErrorBoundary from './components/ui/ErrorBoundary.jsx';
import LoadingSkeleton from './components/ui/LoadingSkeleton.jsx';

// Lazy loaded pages
const Home = lazy(() => import('./pages/Home.jsx'));
const Search = lazy(() => import('./pages/Search.jsx'));
const ProviderProfile = lazy(() => import('./pages/ProviderProfile.jsx'));
const BookingFlow = lazy(() => import('./pages/BookingFlow.jsx'));
const Login = lazy(() => import('./pages/Auth/Login.jsx'));
const Register = lazy(() => import('./pages/Auth/Register.jsx'));
const CustomerDashboard = lazy(() => import('./pages/Dashboard/CustomerDashboard.jsx'));
const ProviderDashboard = lazy(() => import('./pages/Dashboard/ProviderDashboard.jsx'));
const PetManager = lazy(() => import('./pages/PetManager.jsx'));

const PageLoader = () => (
  <div className="min-h-screen bg-dark-bg flex items-center justify-center">
    <div className="flex flex-col items-center gap-4">
      <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-secondary flex items-center justify-center animate-pulse-glow">
        <span className="text-3xl">🐾</span>
      </div>
      <div className="flex gap-1">
        <span className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{ animationDelay: '0ms' }}></span>
        <span className="w-2 h-2 rounded-full bg-secondary animate-bounce" style={{ animationDelay: '150ms' }}></span>
        <span className="w-2 h-2 rounded-full bg-accent animate-bounce" style={{ animationDelay: '300ms' }}></span>
      </div>
    </div>
  </div>
);

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <NotificationProvider>
          <div className="min-h-screen bg-dark-bg text-text-primary font-sans">
            <Navbar />
            <main className="flex-1">
              <Suspense fallback={<PageLoader />}>
                <Routes>
                  <Route path="/" element={<Home />} />
                  <Route path="/search" element={<Search />} />
                  <Route path="/provider/:id" element={<ProviderProfile />} />
                  <Route path="/book/:providerId/:serviceId" element={
                    <PrivateRoute>
                      <BookingFlow />
                    </PrivateRoute>
                  } />
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />
                  <Route path="/dashboard" element={
                    <PrivateRoute>
                      <CustomerDashboard />
                    </PrivateRoute>
                  } />
                  <Route path="/provider/dashboard" element={
                    <PrivateRoute requireProvider>
                      <ProviderDashboard />
                    </PrivateRoute>
                  } />
                  <Route path="/pets" element={
                    <PrivateRoute>
                      <PetManager />
                    </PrivateRoute>
                  } />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Suspense>
            </main>
            <Footer />
          </div>
        </NotificationProvider>
      </AuthProvider>
    </ErrorBoundary>
  );
}

export default App;
