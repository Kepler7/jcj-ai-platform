import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function HomeRedirect() {
  const { me } = useAuth();
  if (!me) return <Navigate to="/login" replace />;

  if (me.role === 'platform_admin') return <Navigate to="/schools" replace />;
  if (me.role === 'school_admin') return <Navigate to="/students" replace />;
  if (me.role === 'teacher') return <Navigate to="/students" replace />;

  return <Navigate to="/forbidden" replace />;
}
