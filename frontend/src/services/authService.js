import api from './api.js';

/**
 * Login with email and password
 */
export const login = async (email, password) => {
  const response = await api.post('/auth/login', { email, password });
  const { access_token, refresh_token, user } = response.data;
  localStorage.setItem('pepto_token', access_token);
  if (refresh_token) localStorage.setItem('pepto_refresh_token', refresh_token);
  localStorage.setItem('pepto_user', JSON.stringify(user));
  return { token: access_token, user };
};

/**
 * Register new user
 */
export const register = async (data) => {
  const response = await api.post('/auth/register', data);
  return response.data;
};

/**
 * Logout current user
 */
export const logout = async () => {
  try {
    await api.post('/auth/logout');
  } catch {
    // Ignore logout errors
  } finally {
    localStorage.removeItem('pepto_token');
    localStorage.removeItem('pepto_refresh_token');
    localStorage.removeItem('pepto_user');
  }
};

/**
 * Refresh access token
 */
export const refreshToken = async () => {
  const refreshTk = localStorage.getItem('pepto_refresh_token');
  if (!refreshTk) throw new Error('No refresh token');
  const response = await api.post('/auth/refresh', { refresh_token: refreshTk });
  const { access_token } = response.data;
  localStorage.setItem('pepto_token', access_token);
  return access_token;
};

/**
 * Get current user profile
 */
export const getCurrentUser = async () => {
  const response = await api.get('/auth/me');
  const user = response.data;
  localStorage.setItem('pepto_user', JSON.stringify(user));
  return user;
};

/**
 * Update user profile
 */
export const updateProfile = async (data) => {
  const response = await api.put('/auth/profile', data);
  const user = response.data;
  localStorage.setItem('pepto_user', JSON.stringify(user));
  return user;
};

/**
 * Request password reset
 */
export const requestPasswordReset = async (email) => {
  const response = await api.post('/auth/forgot-password', { email });
  return response.data;
};

/**
 * Reset password with token
 */
export const resetPassword = async (token, password) => {
  const response = await api.post('/auth/reset-password', { token, password });
  return response.data;
};

/**
 * Verify email with token
 */
export const verifyEmail = async (token) => {
  const response = await api.post('/auth/verify-email', { token });
  return response.data;
};

/**
 * Google OAuth sign in
 */
export const googleSignIn = async (credential) => {
  const response = await api.post('/auth/google', { credential });
  const { access_token, refresh_token, user } = response.data;
  localStorage.setItem('pepto_token', access_token);
  if (refresh_token) localStorage.setItem('pepto_refresh_token', refresh_token);
  localStorage.setItem('pepto_user', JSON.stringify(user));
  return { token: access_token, user };
};

const authService = {
  login,
  register,
  logout,
  refreshToken,
  getCurrentUser,
  updateProfile,
  requestPasswordReset,
  resetPassword,
  verifyEmail,
  googleSignIn,
};

export default authService;
