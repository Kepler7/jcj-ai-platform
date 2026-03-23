import { useMemo, useState } from 'react';
import { Box, Button, Heading, Input, Stack, Text, Link } from '@chakra-ui/react';
import { Link as RouterLink, useSearchParams, useNavigate } from 'react-router-dom';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

console.log('API_BASE:', API_BASE);

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const token = useMemo(() => params.get('token') ?? '', [params]);

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const tokenMissing = !token;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatusMsg(null);

    if (tokenMissing) {
      setError('Missing token. Please use the link from your email.');
      return;
    }

    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters.');
      return;
    }

    if (newPassword !== confirm) {
      setError('Passwords do not match.');
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? 'Reset failed');
      }

      setStatusMsg('Password updated. You can sign in now.');
      setTimeout(() => navigate('/login', { replace: true }), 800);
    } catch (err: any) {
      setError(err?.message ?? 'Reset failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box maxW="420px" mx="auto" mt="80px" p="6" borderWidth="1px" borderRadius="lg">
      <Heading size="md" mb="4">Reset password</Heading>

      {tokenMissing && (
        <Text color="red.500" fontSize="sm" mb="3">
          Missing token. Please open the link from your email.
        </Text>
      )}

      <form onSubmit={onSubmit}>
        <Stack gap="3">
          <Input
            placeholder="New password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
          />
          <Input
            placeholder="Confirm new password"
            type="password"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            autoComplete="new-password"
          />

          {statusMsg && <Text color="green.600" fontSize="sm">{statusMsg}</Text>}
          {error && <Text color="red.500" fontSize="sm">{error}</Text>}

          <Button type="submit" isLoading={loading} isDisabled={tokenMissing}>
            Update password
          </Button>

          <Link as={RouterLink} to="/login" fontSize="sm" textAlign="center" color="blue.500">
            Back to login
          </Link>
        </Stack>
      </form>
    </Box>
  );
}