import React from 'react';
import { useAuth } from '../../context/AuthContext';

const AuthDebug = () => {
  const { user, isAuthenticated, loading, error } = useAuth();

  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="fixed bottom-4 right-4 bg-black bg-opacity-75 text-white p-4 rounded-lg text-xs max-w-sm">
      <h4 className="font-bold mb-2">Auth Debug</h4>
      <div className="space-y-1">
        <p>Loading: {loading ? 'Yes' : 'No'}</p>
        <p>Authenticated: {isAuthenticated ? 'Yes' : 'No'}</p>
        <p>User Role: {user?.role || 'None'}</p>
        <p>User Name: {user?.name || 'None'}</p>
        <p>Error: {error || 'None'}</p>
        <p>Token: {localStorage.getItem('authToken') ? 'Exists' : 'None'}</p>
      </div>
    </div>
  );
};

export default AuthDebug;
