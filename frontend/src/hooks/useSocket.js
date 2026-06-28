import { useState, useEffect, useRef, useCallback } from 'react';
import { io } from 'socket.io-client';
import { SOCKET_URL } from '../utils/constants.js';
import { useAuth } from './useAuth.js';

const useSocket = () => {
  const { token, user, isAuthenticated } = useAuth();
  const [connected, setConnected] = useState(false);
  const socketRef = useRef(null);
  const listenersRef = useRef({});

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
        setConnected(false);
      }
      return;
    }

    if (socketRef.current?.connected) return;

    const socket = io(SOCKET_URL, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnectionAttempts: 5,
      reconnectionDelay: 1000,
    });

    socket.on('connect', () => {
      setConnected(true);
      if (user?._id) {
        socket.emit('join_room', user._id);
      }
      // Re-attach stored listeners after reconnect
      Object.entries(listenersRef.current).forEach(([event, handler]) => {
        socket.on(event, handler);
      });
    });

    socket.on('disconnect', () => {
      setConnected(false);
    });

    socketRef.current = socket;

    return () => {
      socket.disconnect();
      socketRef.current = null;
      setConnected(false);
    };
  }, [isAuthenticated, token, user?._id]);

  const on = useCallback((event, handler) => {
    listenersRef.current[event] = handler;
    if (socketRef.current) {
      socketRef.current.on(event, handler);
    }
    return () => {
      delete listenersRef.current[event];
      if (socketRef.current) {
        socketRef.current.off(event, handler);
      }
    };
  }, []);

  const emit = useCallback((event, data) => {
    if (socketRef.current?.connected) {
      socketRef.current.emit(event, data);
    }
  }, []);

  return {
    socket: socketRef.current,
    connected,
    on,
    emit,
  };
};

export default useSocket;
