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

type Class = {
  id: string;
  name: string;
};

type School = {
  id: string;
  name: string;
  is_active: boolean;
};

type ClassMini = {
  id: string;
  name: string;
};

type Student = {
  id: string;
  school_id: string;
  full_name: string;
  age: number;
  classes: ClassMini[];
  notes?: string | null;
  is_active: boolean;
  reports_count?: number;
};

export default function StudentsPage() {
  const { me } = useAuth();
  const navigate = useNavigate();

  const [schools, setSchools] = useState<School[]>([]);
  const [selectedSchoolId, setSelectedSchoolId] = useState<string>('');

  const effectiveSchoolId = useMemo(() => {
    if (!me) return '';
    if (me.role === 'platform_admin') return selectedSchoolId;
    return me.school_id ?? '';
  }, [me, selectedSchoolId]);

  const [students, setStudents] = useState<Student[]>([]);
  const [classes, setClasses] = useState<Class[]>([]);

  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [fullName, setFullName] = useState('');
  const [age, setAge] = useState<number | ''>('');
  const [selectedClass, setSelectedClass] = useState('');
  const [notes, setNotes] = useState('');

  async function loadSchoolsIfNeeded() {
    if (!me || me.role !== 'platform_admin') return;

    const data = await api<School[]>('/v1/schools', { auth: true });
    const active = data.filter((s) => s.is_active);
    setSchools(active);

    if (!selectedSchoolId && active.length > 0) {
      setSelectedSchoolId(active[0].id);
    }
  }

  async function loadClasses() {
    try {
      if (!effectiveSchoolId) {
        setClasses([]);
        return;
      }

      const data = await api<Class[]>(
        `/v1/classes/by-school/${encodeURIComponent(effectiveSchoolId)}`,
        { auth: true }
      );

      const sorted = [...data].sort((a, b) => a.name.localeCompare(b.name));
      setClasses(sorted);
    } catch (e) {
      console.error('Error loading classes', e);
      setClasses([]);
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
          age: age === '' ? null : age,
          classes: selectedClass ? [selectedClass] : [],
          notes: notes.trim() || null,
        },
      });

      setStudents((prev) =>
        [created, ...prev].sort((a, b) => a.full_name.localeCompare(b.full_name))
      );

      setFullName('');
      setAge(7);
      setSelectedClass('');
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
    loadStudents();
    loadClasses();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [effectiveSchoolId]);

  return (
    <Box>
      <Heading size="md" mb="4">
        Students
      </Heading>

      {me?.role === 'platform_admin' && (
        <Box borderWidth="1px" borderRadius="lg" p="4" mb="4">
          <Text fontWeight="semibold" mb="2">
            Select school
          </Text>
          <Select
            placeholder={
              !effectiveSchoolId
                ? 'Select school first'
                : classes.length
                  ? 'Select class'
                  : 'No classes available'
            }
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            width={{ base: '100%', md: '220px' }}
            isDisabled={!effectiveSchoolId || classes.length === 0}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
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
            onChange={(e) => {
              const val = e.target.value;
              if (/^\d*$/.test(val)) {
                setAge(val === '' ? '' : Number(val));
              }
            }}
            min={1}
            max={16}
            width={{ base: '100%', md: '120px' }}
          />

          <Select
            placeholder={classes.length ? 'Select class' : 'No classes available'}
            value={selectedClass}
            onChange={(e) => setSelectedClass(e.target.value)}
            width={{ base: '100%', md: '220px' }}
            isDisabled={!effectiveSchoolId || classes.length === 0}
          >
            {classes.map((c) => (
              <option key={c.id} value={c.name}>
                {c.name}
              </option>
            ))}
          </Select>

          <Input
            placeholder="Notes (optional)"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <Button
            onClick={createStudent}
            isLoading={creating}
            isDisabled={!fullName.trim() || !effectiveSchoolId || !selectedClass}
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
                <Th>Actions</Th>
                <Th>Full name</Th>
                <Th>Age</Th>
                <Th>Classes</Th>
                <Th>Active</Th>
                <Th>ID</Th>
              </Tr>
            </Thead>
            <Tbody>
              {students.map((student) => (
                <Tr key={student.id}>
                  <Td>
                    <Button
                      size="xs"
                      colorScheme={(student.reports_count ?? 0) > 0 ? 'green' : 'gray'}
                      variant={(student.reports_count ?? 0) > 0 ? 'solid' : 'outline'}
                      onClick={() => navigate(`/students/${student.id}/reports`)}
                    >
                      Reports{' '}
                      {(student.reports_count ?? 0) > 0
                        ? `(${student.reports_count})`
                        : ''}
                    </Button>
                  </Td>

                  <Td>{student.full_name}</Td>
                  <Td>{student.age}</Td>
                  <Td>
                    {student.classes?.length
                      ? student.classes.map((c) => c.name).join(', ')
                      : '—'}
                  </Td>
                  <Td>{student.is_active ? 'Yes' : 'No'}</Td>
                  <Td>{student.id}</Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
    </Box>
  );
}
