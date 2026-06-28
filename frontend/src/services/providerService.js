import api from './api.js';

/**
 * Search providers with filters
 */
export const searchProviders = async (params = {}) => {
  const response = await api.get('/providers/search', { params });
  return response.data;
};

/**
 * Get single provider by ID
 */
export const getProvider = async (id) => {
  const response = await api.get(`/providers/${id}`);
  return response.data;
};

/**
 * Get provider reviews with pagination
 */
export const getProviderReviews = async (id, page = 1, limit = 10) => {
  const response = await api.get(`/providers/${id}/reviews`, {
    params: { page, limit },
  });
  return response.data;
};

/**
 * Create provider profile (for new providers)
 */
export const createProfile = async (data) => {
  const response = await api.post('/providers/profile', data);
  return response.data;
};

/**
 * Update provider profile
 */
export const updateProfile = async (data) => {
  const response = await api.put('/providers/profile', data);
  return response.data;
};

/**
 * Upload provider cover image
 */
export const uploadCoverImage = async (file) => {
  const formData = new FormData();
  formData.append('cover_image', file);
  const response = await api.post('/providers/profile/cover', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

/**
 * Create a service for the provider
 */
export const createService = async (data) => {
  const response = await api.post('/providers/services', data);
  return response.data;
};

/**
 * Update a service
 */
export const updateService = async (serviceId, data) => {
  const response = await api.put(`/providers/services/${serviceId}`, data);
  return response.data;
};

/**
 * Delete a service
 */
export const deleteService = async (serviceId) => {
  const response = await api.delete(`/providers/services/${serviceId}`);
  return response.data;
};

/**
 * Set provider availability (weekly slots)
 */
export const setAvailability = async (slots) => {
  const response = await api.put('/providers/availability', { slots });
  return response.data;
};

/**
 * Get provider availability for a given date range
 */
export const getAvailability = async (providerId, startDate, endDate) => {
  const response = await api.get(`/providers/${providerId}/availability`, {
    params: { start_date: startDate, end_date: endDate },
  });
  return response.data;
};

/**
 * Get provider dashboard statistics
 */
export const getDashboardStats = async () => {
  const response = await api.get('/providers/dashboard/stats');
  return response.data;
};

/**
 * Get earnings data for chart
 */
export const getEarningsData = async (period = '30d') => {
  const response = await api.get('/providers/dashboard/earnings', { params: { period } });
  return response.data;
};

/**
 * Get featured/top providers (for homepage)
 */
export const getFeaturedProviders = async (limit = 6) => {
  const response = await api.get('/providers/featured', { params: { limit } });
  return response.data;
};

const providerService = {
  searchProviders,
  getProvider,
  getProviderReviews,
  createProfile,
  updateProfile,
  uploadCoverImage,
  createService,
  updateService,
  deleteService,
  setAvailability,
  getAvailability,
  getDashboardStats,
  getEarningsData,
  getFeaturedProviders,
};

export default providerService;
