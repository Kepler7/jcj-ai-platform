import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { Box, Spinner } from '@chakra-ui/react';

type Role = 'platform_admin' | 'school_admin' | 'teacher';

export default function ProtectedRoute({
  children,
  roles,
}: {
  children: React.ReactNode;
  roles?: Role[];
}) {
  const { me, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return (
      <Box p="6">
        <Spinner />
      </Box>
    );
  }

  if (!me) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (roles && !roles.includes(me.role)) {
    return <Navigate to="/forbidden" replace />;
  }

  return <>{children}</>;
}
