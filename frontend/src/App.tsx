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
import PlaybookPendientesPage from "./pages/PlaybookPendientesPage";
import ClassesBoardPage from "./pages/ClassesBoardPage";

import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import BulkStudentsPage from "./pages/admin/BulkStudentsPage";

export default function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/p/:token" element={<ParentSharePage />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/forbidden" element={<ForbiddenPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />

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

        {/* Pendientes de Playbook (solo platform_admin) */}
        <Route
          path="/playbook-pendientes"
          element={
            <ProtectedRoute roles={['platform_admin']}>
              <PlaybookPendientesPage />
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
        {/* Classes Board */}
        <Route
          path="/admin/classes-board"
          element={
            <ProtectedRoute
              roles={['platform_admin', 'school_admin', 'teacher']}
            >
              <ClassesBoardPage />
            </ProtectedRoute>
          }
        />
          {/* Bulk Students (solo platform_admin y school_admin) */} 
          <Route path="/admin/bulk-students" 
                 element={
            <ProtectedRoute roles={['platform_admin', 'school_admin']}>
                 <BulkStudentsPage />
            </ProtectedRoute>
          } />
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
