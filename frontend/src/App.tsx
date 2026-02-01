import { Routes, Route, Navigate } from 'react-router-dom';

import LoginPage from './pages/LoginPage';
import ForbiddenPage from './pages/ForbiddenPage';
import HomeRedirect from './pages/HomeRedirect';
import SchoolsPage from './pages/SchoolsPage';
import StudentsPage from './pages/StudentsPage';
import ReportsPage from './pages/ReportsPage';

import ProtectedRoute from './auth/ProtectedRoute';
import AppShell from './components/AppShell';

// NUEVO
import ParentSharePage from "./pages/ParentSharePage";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/p/:token" element={<ParentSharePage />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/forbidden" element={<ForbiddenPage />} />

      {/* Private + Layout */}
      <Route
        element={
          <ProtectedRoute>
            <AppShell />
          </ProtectedRoute>
        }
      >
        {/* Home */}
        <Route path="/" element={<HomeRedirect />} />

        {/* Schools (solo platform_admin) */}
        <Route
          path="/schools"
          element={
            <ProtectedRoute roles={['platform_admin']}>
              <SchoolsPage />
            </ProtectedRoute>
          }
        />

        {/* Students */}
        <Route
          path="/students"
          element={
            <ProtectedRoute
              roles={['platform_admin', 'school_admin', 'teacher']}
            >
              <StudentsPage />
            </ProtectedRoute>
          }
        />

        {/* Reports (dentro del layout) */}
        <Route
          path="/students/:studentId/reports"
          element={
            <ProtectedRoute
              roles={['platform_admin', 'school_admin', 'teacher']}
            >
              <ReportsPage />
            </ProtectedRoute>
          }
        />
      </Route>

      {/* Fallback */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
