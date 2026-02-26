import { useState } from 'react';
import { Box, Button, Heading, Input, Stack, Text, Link } from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatusMsg(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      // aunque falle, tu backend puede devolver siempre neutro,
      // pero si hay error real (500, etc.) lo mostramos.
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? 'Request failed');
      }

      setStatusMsg('If the email exists, you will receive instructions.');
    } catch (err: any) {
      setError(err?.message ?? 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box maxW="420px" mx="auto" mt="80px" p="6" borderWidth="1px" borderRadius="lg">
      <Heading size="md" mb="4">Forgot password</Heading>

      <form onSubmit={onSubmit}>
        <Stack gap="3">
          <Input
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />

          {statusMsg && <Text color="green.600" fontSize="sm">{statusMsg}</Text>}
          {error && <Text color="red.500" fontSize="sm">{error}</Text>}

          <Button type="submit" isLoading={loading}>
            Send reset link
          </Button>

          <Link as={RouterLink} to="/login" fontSize="sm" textAlign="center" color="blue.500">
            Back to login
          </Link>
        </Stack>
      </form>
    </Box>
  );
}