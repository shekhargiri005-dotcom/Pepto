import api from './api.js';

/**
 * Create a new booking
 */
export const createBooking = async (data) => {
  const response = await api.post('/bookings', data);
  return response.data;
};

/**
 * Get user's bookings with filters
 */
export const getMyBookings = async (params = {}) => {
  const response = await api.get('/bookings/my', { params });
  return response.data;
};

/**
 * Get a single booking by ID
 */
export const getBooking = async (id) => {
  const response = await api.get(`/bookings/${id}`);
  return response.data;
};

/**
 * Update booking status (provider action)
 */
export const updateStatus = async (id, status, note = '') => {
  const response = await api.patch(`/bookings/${id}/status`, { status, note });
  return response.data;
};

/**
 * Cancel a booking
 */
export const cancelBooking = async (id, reason = '') => {
  const response = await api.patch(`/bookings/${id}/cancel`, { reason });
  return response.data;
};

/**
 * Check provider availability for a date
 */
export const checkAvailability = async (providerId, date, serviceId) => {
  const response = await api.get(`/bookings/availability/${providerId}`, {
    params: { date, service_id: serviceId },
  });
  return response.data;
};

/**
 * Create Stripe payment intent for booking
 */
export const createPaymentIntent = async (bookingId) => {
  const response = await api.post(`/bookings/${bookingId}/payment-intent`);
  return response.data;
};

/**
 * Confirm payment after Stripe success
 */
export const confirmPayment = async (bookingId, paymentIntentId) => {
  const response = await api.post(`/bookings/${bookingId}/confirm-payment`, {
    payment_intent_id: paymentIntentId,
  });
  return response.data;
};

/**
 * Submit a review for a completed booking
 */
export const submitReview = async (bookingId, data) => {
  const response = await api.post(`/bookings/${bookingId}/review`, data);
  return response.data;
};

/**
 * Get provider's incoming booking requests
 */
export const getProviderBookings = async (params = {}) => {
  const response = await api.get('/bookings/provider', { params });
  return response.data;
};

/**
 * Get today's schedule for provider
 */
export const getTodaySchedule = async () => {
  const response = await api.get('/bookings/provider/today');
  return response.data;
};

const bookingService = {
  createBooking,
  getMyBookings,
  getBooking,
  updateStatus,
  cancelBooking,
  checkAvailability,
  createPaymentIntent,
  confirmPayment,
  submitReview,
  getProviderBookings,
  getTodaySchedule,
};

export default bookingService;
