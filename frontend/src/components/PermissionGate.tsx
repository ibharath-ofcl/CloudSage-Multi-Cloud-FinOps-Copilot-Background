import React from 'react';
import { SecurityAuth } from '../services/securityApi';

interface PermissionGateProps {
  permission: string;
  fallback?: React.ReactNode;
  children: React.ReactNode;
}

export const PermissionGate: React.FC<PermissionGateProps> = ({
  permission,
  fallback = null,
  children,
}) => {
  const allowed = SecurityAuth.hasPermission(permission);
  if (!allowed) {
    return <>{fallback}</>;
  }
  return <>{children}</>;
};

