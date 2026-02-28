import { useEffect, useRef } from 'react';
import { useAuth } from './useAuth';
import { useNavigate } from 'react-router-dom';

export const useSessionCheck = (intervalMinutes = 5) => {
  const { checkAuth, isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const intervalRef = useRef(null);

  useEffect(() => {
    if (!isAuthenticated) return;

    // Check session every X minutes
    intervalRef.current = setInterval(async () => {
      try {
        await checkAuth();
      } catch (error) {
        // Session expired, redirect to login
        navigate('/login');
      }
    }, intervalMinutes * 60 * 1000);

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, [isAuthenticated, checkAuth, navigate, intervalMinutes]);
};
