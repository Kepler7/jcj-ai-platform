import { useEffect, useMemo, useState } from 'react';
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
  Select,
} from '@chakra-ui/react';
import { api } from '../lib/apiClient';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

type School = {
  id: string;
  name: string;
  is_active: boolean;
};

type Student = {
  id: string;
  school_id: string;
  full_name: string;
  age: number;
  group: string;
  notes?: string | null;
  is_active: boolean;
};

export default function StudentsPage() {
  const { me } = useAuth();

  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('');
  const navigate = useNavigate();

  const effectiveSchoolId = useMemo(() => {
    if (!me) return '';
    if (me.role === 'platform_admin') return selectedSchoolId;
    return me.school_id ?? '';
  }, [me, selectedSchoolId]);

  const [students, setStudents] = useState<Student[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // create form
  const [fullName, setFullName] = useState('');
  const [age, setAge] = useState<number>(7);
  const [group, setGroup] = useState('A');
  const [notes, setNotes] = useState('');
  const [creating, setCreating] = useState(false);

  async function loadSchoolsIfNeeded() {
    if (!me) return;
    if (me.role !== 'platform_admin') return;

    const data = await api<School[]>('/v1/schools', { auth: true });
    const active = data.filter((s) => s.is_active);
    setSchools(active);

    // set default if empty
    if (!selectedSchoolId && active.length > 0) {
      setSelectedSchoolId(active[0].id);
    }
  }

  async function loadStudents() {
    setError(null);
    setLoading(true);
    try {
      if (!effectiveSchoolId) {
        setStudents([]);
        return;
      }
      const data = await api<Student[]>(
        `/v1/students?school_id=${encodeURIComponent(effectiveSchoolId)}`,
        { auth: true }
      );
      setStudents(data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load students');
    } finally {
      setLoading(false);
    }
  }

  async function createStudent() {
    setError(null);
    setCreating(true);
    try {
      if (!effectiveSchoolId) throw new Error('Missing school_id');
      const created = await api<Student>('/v1/students', {
        method: 'POST',
        auth: true,
        body: {
          school_id: effectiveSchoolId,
          full_name: fullName.trim(),
          age,
          group: group.trim(),
          notes: notes.trim() || null,
        },
      });
      setStudents((prev) => [created, ...prev]);
      setFullName('');
      setNotes('');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to create student');
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    loadSchoolsIfNeeded().catch((e) => setError(String(e)));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  useEffect(() => {
    // cuando ya haya school efectiva
    loadStudents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveSchoolId]);

  return (
    <Box>
      <Heading size="md" mb="4">
        Students
      </Heading>

      {/* Selector de escuela solo para platform_admin */}
      {me?.role === 'platform_admin' && (
        <Box borderWidth="1px" borderRadius="lg" p="4" mb="4">
          <Text fontWeight="semibold" mb="2">
            Select school
          </Text>
          <Select
            value={selectedSchoolId}
            onChange={(e) => setSelectedSchoolId(e.target.value)}
          >
            {schools.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </Select>
        </Box>
      )}

      <Box borderWidth="1px" borderRadius="lg" p="4" mb="6">
        <Text fontWeight="semibold" mb="3">
          Create student
        </Text>

        <Stack direction={{ base: 'column', md: 'row' }} gap="3">
          <Input
            placeholder="Full name"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
          />
          <Input
            placeholder="Age"
            type="number"
            value={age}
            onChange={(e) => setAge(Number(e.target.value))}
            min={0}
            max={16}
            width={{ base: '100%', md: '120px' }}
          />
          <Input
            placeholder="Group"
            value={group}
            onChange={(e) => setGroup(e.target.value)}
            width={{ base: '100%', md: '120px' }}
          />
          <Input
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <Button
            onClick={createStudent}
            isLoading={creating}
            isDisabled={!fullName.trim() || !effectiveSchoolId}
          >
            Create
          </Button>

          <Button variant="outline" onClick={loadStudents} isLoading={loading}>
            Refresh
          </Button>
        </Stack>

        {error && (
          <Text mt="3" color="red.500" fontSize="sm">
            {error}
          </Text>
        )}

        {!effectiveSchoolId && (
          <Text mt="3" fontSize="sm" color="orange.500">
            Select a school first.
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
                <Th>Full name</Th>
                <Th>Age</Th>
                <Th>Group</Th>
                <Th>Active</Th>
                <Th>ID</Th>
                <Th>Actions</Th>
              </Tr>
            </Thead>
            <Tbody>
              {students.map((s) => (
                <Tr key={s.id}>
                  <Td>{s.full_name}</Td>
                  <Td>{s.age}</Td>
                  <Td>{s.group}</Td>
                  <Td>{s.is_active ? 'Yes' : 'No'}</Td>
                  <Td fontFamily="mono" fontSize="xs">
                    {s.id}
                  </Td>
                  <Td>
                    <Button
                      size="xs"
                      onClick={() => navigate(`/students/${s.id}/reports`)}
                    >
                      Reports
                    </Button>
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
