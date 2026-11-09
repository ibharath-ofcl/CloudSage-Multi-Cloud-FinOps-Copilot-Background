import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { SecurityAuth } from '../services/securityApi';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
  requiredPermission?: string;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredRole,
  requiredPermission,
}) => {
  const location = useLocation();
  const token = SecurityAuth.getStoredToken();

  // If in development or demo mode without token, allow navigation or redirect to /login
  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (requiredRole && !SecurityAuth.hasRole(requiredRole)) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-red-600 mb-2">Access Denied (403 Forbidden)</h2>
        <p className="text-sm text-slate-600">
          Your assigned role does not grant permission to view this resource. Required role: {requiredRole}
        </p>
      </div>
    );
  }

  if (requiredPermission && !SecurityAuth.hasPermission(requiredPermission)) {
    return (
      <div className="p-8 text-center">
        <h2 className="text-xl font-bold text-red-600 mb-2">Access Denied (403 Forbidden)</h2>
        <p className="text-sm text-slate-600">
          Your account lacks the fine-grained permission: <code className="bg-slate-100 px-1 py-0.5 rounded">{requiredPermission}</code>
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
