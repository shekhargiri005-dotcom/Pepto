import { useState, useEffect, useCallback } from 'react';

const useGeolocation = () => {
  const [location, setLocation] = useState({ lat: null, lng: null });
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const getLocation = useCallback(() => {
    setLoading(true);
    setError(null);

    if (!navigator.geolocation) {
      setError('Geolocation is not supported by your browser.');
      fallbackToIP();
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setLocation({
          lat: position.coords.latitude,
          lng: position.coords.longitude,
        });
        setLoading(false);
      },
      (err) => {
        console.warn('[Geolocation] Error:', err.message);
        setError(err.message);
        fallbackToIP();
      },
      {
        enableHighAccuracy: true,
        timeout: 8000,
        maximumAge: 300000, // 5 minutes cache
      }
    );
  }, []);

  const fallbackToIP = async () => {
    try {
      const res = await fetch('https://ipapi.co/json/');
      const data = await res.json();
      if (data.latitude && data.longitude) {
        setLocation({ lat: data.latitude, lng: data.longitude });
        setError(null);
      }
    } catch (ipErr) {
      console.warn('[Geolocation] IP fallback failed:', ipErr);
      // Default to Mumbai, India
      setLocation({ lat: 19.076, lng: 72.8777 });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    getLocation();
  }, []);

  return { ...location, error, loading, refresh: getLocation };
};

export default useGeolocation;
