import React from 'react';
import { Navigate } from 'react-router-dom';
import { authService } from '../services/authService';

const ProtectedRoute = ({ children }) => {
  // Allow when a backend JWT token exists (new flow) or when the legacy
  // local authService has a current user.
  const hasToken = Boolean(authService.getToken());
  const user = authService.getCurrentUser();
  if (!hasToken && !user) return <Navigate to="/login" replace />;
  return children;
};

export default ProtectedRoute;
