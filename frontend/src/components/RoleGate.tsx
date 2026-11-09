import React from 'react';
import { SecurityAuth } from '../services/securityApi';

interface RoleGateProps {
  roles: string[];
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const RoleGate: React.FC<RoleGateProps> = ({
  roles,
  fallback = null,
  children,
}) => {
  const allowed = roles.some((role) => SecurityAuth.hasRole(role));
  if (!allowed) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
};
