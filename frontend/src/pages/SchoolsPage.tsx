import { useEffect, useState } from 'react';
import {
  Box,
  Button,
  Heading,
  Input,
  Stack,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
} from '@chakra-ui/react';
import { api } from '../lib/apiClient';

type School = {
  id: string;
  name: string;
  legal_name?: string | null;
  city?: string | null;
  state?: string | null;
  is_active: boolean;
};

export default function SchoolsPage() {
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [creating, setCreating] = useState(false);

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const data = await api<School[]>('/v1/schools', { auth: true });
      setSchools(data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load schools');
    } finally {
      setLoading(false);
    }
  }

  async function createSchool() {
    setError(null);
    setCreating(true);
    try {
      const created = await api<School>('/v1/schools', {
        method: 'POST',
        auth: true,
        body: {
          name: name.trim(),
          city: city.trim() || null,
          state: state.trim() || null,
        },
      });
      setSchools((prev) => [created, ...prev]);
      setName('');
      setCity('');
      setState('');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to create school');
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Box>
      <Heading size="md" mb="4">
        Schools
      </Heading>

      <Box borderWidth="1px" borderRadius="lg" p="4" mb="6">
        <Text fontWeight="semibold" mb="3">
          Create school
        </Text>

        <Stack direction={{ base: 'column', md: 'row' }} gap="3">
          <Input
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <Input
            placeholder="City"
            value={city}
            onChange={(e) => setCity(e.target.value)}
          />
          <Input
            placeholder="State"
            value={state}
            onChange={(e) => setState(e.target.value)}
          />

          <Button
            onClick={createSchool}
            isLoading={creating}
            isDisabled={!name.trim()}
          >
            Create
          </Button>

          <Button variant="outline" onClick={load} isLoading={loading}>
            Refresh
          </Button>
        </Stack>

        {error && (
          <Text mt="3" color="red.500" fontSize="sm">
            {error}
          </Text>
        )}
      </Box>

      {loading ? (
        <Text>Loading...</Text>
      ) : (
        <Box borderWidth="1px" borderRadius="lg" overflowX="auto">
          <Table size="sm">
            <Thead>
              <Tr>
                <Th>Name</Th>
                <Th>City</Th>
                <Th>State</Th>
                <Th>Active</Th>
                <Th>ID</Th>
              </Tr>
            </Thead>
            <Tbody>
              {schools.map((s) => (
                <Tr key={s.id}>
                  <Td>{s.name}</Td>
                  <Td>{s.city ?? '-'}</Td>
                  <Td>{s.state ?? '-'}</Td>
                  <Td>{s.is_active ? 'Yes' : 'No'}</Td>
                  <Td fontFamily="mono" fontSize="xs">
                    {s.id}
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
    </Box>
  );
}
