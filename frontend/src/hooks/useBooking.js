import { useState, useCallback } from 'react';
import bookingService from '../services/bookingService.js';
import toast from 'react-hot-toast';

const useBooking = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const createBooking = useCallback(async (data) => {
    setLoading(true);
    setError(null);
    try {
      const result = await bookingService.createBooking(data);
      toast.success('Booking created successfully! 🎉');
      return result;
    } catch (err) {
      setError(err.message);
      toast.error(err.message || 'Failed to create booking');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const cancelBooking = useCallback(async (id, reason) => {
    setLoading(true);
    setError(null);
    try {
      const result = await bookingService.cancelBooking(id, reason);
      toast.success('Booking cancelled successfully');
      return result;
    } catch (err) {
      setError(err.message);
      toast.error(err.message || 'Failed to cancel booking');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const updateStatus = useCallback(async (id, status, note) => {
    setLoading(true);
    setError(null);
    try {
      const result = await bookingService.updateStatus(id, status, note);
      const messages = {
        confirmed: 'Booking confirmed! ✅',
        rejected: 'Booking rejected',
        completed: 'Booking marked as completed 🎉',
      };
      toast.success(messages[status] || 'Status updated');
      return result;
    } catch (err) {
      setError(err.message);
      toast.error(err.message || 'Failed to update status');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const checkAvailability = useCallback(async (providerId, date, serviceId) => {
    setLoading(true);
    setError(null);
    try {
      const result = await bookingService.checkAvailability(providerId, date, serviceId);
      return result;
    } catch (err) {
      setError(err.message);
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  const submitReview = useCallback(async (bookingId, data) => {
    setLoading(true);
    setError(null);
    try {
      const result = await bookingService.submitReview(bookingId, data);
      toast.success('Review submitted! Thank you 🌟');
      return result;
    } catch (err) {
      setError(err.message);
      toast.error(err.message || 'Failed to submit review');
      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    createBooking,
    cancelBooking,
    updateStatus,
    checkAvailability,
    submitReview,
    loading,
    error,
  };
};

export default useBooking;
