import React from 'react';
import { useAuth } from '../../hooks/useAuth';

const DebugAuth = () => {
  const { user, loading, isInitialized, isAuthenticated } = useAuth();

  // Only show in development
  if (process.env.NODE_ENV !== 'development') return null;

  return (
    <div className="fixed bottom-4 right-4 bg-black bg-opacity-75 text-white p-4 rounded-lg text-xs max-w-xs">
      <h4 className="font-bold mb-2">Auth Debug</h4>
      <div className="space-y-1">
        <p>Initialized: {isInitialized ? '✅' : '❌'}</p>
        <p>Loading: {loading ? '⏳' : '✅'}</p>
        <p>Authenticated: {isAuthenticated ? '✅' : '❌'}</p>
        <p>User: {user ? user.email : 'None'}</p>
        <p>Role: {user?.role || 'N/A'}</p>
        <p>Cookies: {document.cookie || 'None'}</p>
      </div>
    </div>
  );
};

export default DebugAuth;
