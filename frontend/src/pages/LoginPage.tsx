import { useState } from 'react';
import { Box, Button, Heading, Input, Stack, Text } from '@chakra-ui/react';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function LoginPage() {
  const { signIn, refreshMe } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const t = await signIn(email.trim(), password);
      await refreshMe(t);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err?.message ?? 'Login failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      maxW="420px"
      mx="auto"
      mt="80px"
      p="6"
      borderWidth="1px"
      borderRadius="lg"
    >
      <Heading size="md" mb="4">
        IHUI ai
      </Heading>

      <form onSubmit={onSubmit}>
        <Stack gap="3">
          <Input
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            autoComplete="email"
          />
          <Input
            placeholder="Password"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
          />

          {error && (
            <Text color="red.500" fontSize="sm">
              {error}
            </Text>
          )}

          <Button type="submit" isLoading={loading}>
            Sign in
          </Button>
        </Stack>
      </form>
    </Box>
  );
}
