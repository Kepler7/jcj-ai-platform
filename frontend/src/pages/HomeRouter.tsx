import { Box, Button, Spinner, Text } from '@chakra-ui/react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function HomeRouter() {
  const { me, loading, signOut } = useAuth();

  if (loading) {
    return (
      <Box p="6">
        <Spinner />
      </Box>
    );
  }

  if (!me) return <Navigate to="/login" replace />;

  // Por ahora solo mostramos quién eres.
  // Luego aquí haremos redirects por rol a /schools /students etc.
  return (
    <Box p="6">
      <Text>Logged in as: {me.email}</Text>
      <Text>Role: {me.role}</Text>
      <Text>School ID: {me.school_id ?? 'null'}</Text>

      <Button mt="4" onClick={signOut}>
        Sign out
      </Button>
    </Box>
  );
}
