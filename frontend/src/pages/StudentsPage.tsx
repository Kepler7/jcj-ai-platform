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
  Flex,
  Grid,
  GridItem,
  Avatar,
  Badge,
  InputGroup,
  InputLeftElement,
  HStack,
  IconButton,
  Textarea,
  useColorModeValue,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { api } from '../lib/apiClient';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  GraduationCap,
  UserPlus,
  ArrowRight,
  Search,
  ListFilter,
  Download,
  FileText
} from 'lucide-react';

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
  const { t } = useTranslation();
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

  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const pageBg = useColorModeValue("#f8f9fa", "gray.900");
  const inputBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.500");
  const textLabel = useColorModeValue("#434654", "gray.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryBg = useColorModeValue("#e8edff", "blue.900");
  const highlightColor = useColorModeValue("#006c4a", "green.300");
  const highlightBg = useColorModeValue("#e1fedc", "green.900");
  const errorText = useColorModeValue("#ba1a1a", "red.300");
  const errorBg = useColorModeValue("#ffeceb", "red.900");
  const borderColor = useColorModeValue("#f3f4f5", "whiteAlpha.100");

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
      setAge('');
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
    <Box px={{ base: 4, md: 8 }} py={{ base: 6, md: 8 }} maxW="100%" overflowX="hidden">
      {/* Header */}
      <Box mb="8">
        <Text fontSize="xs" fontWeight="bold" color={textMuted} letterSpacing="widest" textTransform="uppercase" mb="2">
          {t("students_page.platform_path").split(' › ')[0]} <Text as="span" color={textMuted} mx="2">›</Text> <Text as="span" color={primaryColor}>{t("students_page.title")}</Text>
        </Text>
        <Heading as="h1" fontSize={{ base: "3xl", md: "5xl" }} fontWeight="extrabold" color={textColor} fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" mb="4">
          {t("students_page.title")}
        </Heading>
        <Flex align="center" gap="2" color={textLabel}>
          <Users size={20} color={primaryColor} />
          <Text fontWeight="medium" fontSize="sm">
            <Text as="span" fontWeight="bold" color={textColor}>{students.length.toLocaleString()}</Text> {t("students_page.active_students")}
          </Text>
        </Flex>
      </Box>

      {/* Main Layout Grid */}
      <Grid templateColumns={{ base: '1fr', lg: '350px 1fr' }} gap={{ base: 6, md: 8 }}>

        {/* Left Column */}
        <GridItem>
          {me?.role === 'platform_admin' && (
            <Box bg={pageBg} borderRadius="2rem" p={{ base: 6, lg: 8 }} mb="6">
              <Text fontSize="xs" fontWeight="bold" color={textLabel} textTransform="uppercase" letterSpacing="wider" mb="4">
                {t("students_page.current_campus")}
              </Text>
              <Box bg={cardBg} p="2" borderRadius="xl" boxShadow="0px 4px 12px rgba(25, 28, 29, 0.04)" mb="4">
                <Flex align="center">
                  <Flex align="center" justify="center" w="10" h="10" bg={primaryColor} color="white" borderRadius="lg" mr="3">
                    <GraduationCap size={20} />
                  </Flex>
                  <Select
                    variant="unstyled"
                    fontWeight="bold"
                    fontSize="sm"
                    color={textColor}
                    value={selectedSchoolId}
                    onChange={(e) => setSelectedSchoolId(e.target.value)}
                    iconColor={primaryColor}
                    cursor="pointer"
                  >
                    {schools.map((s) => (
                      <option key={s.id} value={s.id} style={{ color: "black" }}>
                        {s.name}
                      </option>
                    ))}
                  </Select>
                </Flex>
              </Box>
              <Text color={textMuted} fontSize="sm" lineHeight="tall">
                {t("students_page.campus_desc")}
              </Text>
            </Box>
          )}

          <Box bg={cardBg} borderRadius="2rem" p={{ base: 6, lg: 8 }} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)">
            <Flex align="center" justify="space-between" mb="8">
              <Text fontSize="xl" fontWeight="extrabold" color={textColor} fontFamily="'Plus Jakarta Sans', sans-serif">
                {t("students_page.add_new")}
              </Text>
              <Flex align="center" justify="center" w="10" h="10" bg={primaryBg} color={primaryColor} borderRadius="full">
                <UserPlus size={18} />
              </Flex>
            </Flex>

            <Stack gap="5">
              <Box>
                <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="2" textTransform="uppercase" letterSpacing="wider">
                  {t("students_page.full_name")}
                </Text>
                <Input
                  placeholder={t("students_page.placeholder_name")}
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  bg={inputBg}
                  border="none"
                  borderRadius="xl"
                  py="6"
                  fontSize="sm"
                  color={textColor}
                  _placeholder={{ color: textMuted }}
                  _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: cardBg, outline: "none" }}
                />
              </Box>

              <Flex gap="4" direction={{ base: "column", md: "row" }}>
                <Box flex="1">
                  <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="2" textTransform="uppercase" letterSpacing="wider">
                    {t("students_page.age")}
                  </Text>
                  <Input
                    placeholder="14"
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
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    py="6"
                    fontSize="sm"
                    color={textColor}
                    _placeholder={{ color: textMuted }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: cardBg, outline: "none" }}
                  />
                </Box>
                <Box flex="1">
                  <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="2" textTransform="uppercase" letterSpacing="wider">
                    {t("students_page.class")}
                  </Text>
                  <Select
                    placeholder={classes.length ? t("students_page.select_class") : t("students_page.no_classes")}
                    value={selectedClass}
                    onChange={(e) => setSelectedClass(e.target.value)}
                    isDisabled={!effectiveSchoolId || classes.length === 0}
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    h="auto"
                    py="3"
                    fontSize="sm"
                    color={textColor}
                    _placeholder={{ color: textMuted }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: cardBg, outline: "none" }}
                  >
                    {classes.map((c) => (
                      <option key={c.id} value={c.name} style={{ color: "black" }}>
                        {c.name}
                      </option>
                    ))}
                  </Select>
                </Box>
              </Flex>

              <Box>
                <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="2" textTransform="uppercase" letterSpacing="wider">
                  {t("students_page.internal_notes")}
                </Text>
                <Textarea
                  placeholder={t("students_page.placeholder_notes")}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  bg={inputBg}
                  border="none"
                  borderRadius="xl"
                  py="4"
                  fontSize="sm"
                  color={textColor}
                  resize="none"
                  rows={4}
                  _placeholder={{ color: textMuted }}
                  _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: cardBg, outline: "none" }}
                />
              </Box>

              <Button
                mt="2"
                onClick={createStudent}
                isLoading={creating}
                isDisabled={!fullName.trim() || !effectiveSchoolId || (!selectedClass && classes.length > 0)}
                w="full"
                py="6"
                bgGradient="linear(to-r, #003597, #0049ca)"
                color="white"
                borderRadius="xl"
                fontWeight="bold"
                fontSize="md"
                boxShadow="0px 10px 15px -3px rgba(0, 53, 151, 0.2)"
                _hover={{ transform: "scale(1.02)", bgGradient: "linear(to-r, #003597, #0049ca)" }}
                _active={{ transform: "scale(0.98)" }}
                transition="all 0.2s"
                rightIcon={<ArrowRight size={18} />}
              >
                {t("students_page.add_btn")}
              </Button>

              {error && (
                <Text mt="1" color={errorText} fontSize="sm" textAlign="center">
                  {error}
                </Text>
              )}

              {!effectiveSchoolId && (
                <Text mt="1" fontSize="sm" color={errorText} textAlign="center">
                  {t("students_page.select_school_first")}
                </Text>
              )}
            </Stack>
          </Box>
        </GridItem>

        <GridItem minW="0">
          {/* Controls Bar */}
          <Flex gap="4" mb="6" direction={{ base: "column", md: "row" }}>
            <InputGroup size="lg" flex="1">
              <InputLeftElement pointerEvents="none" color={textMuted}>
                <Search size={20} />
              </InputLeftElement>
              <Input
                placeholder={t("students_page.search_placeholder")}
                bg={cardBg}
                border="none"
                borderRadius="full"
                fontSize="sm"
                color={textColor}
                boxShadow="0px 4px 12px rgba(25,28,29,0.03)"
                _placeholder={{ color: textMuted }}
                _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", outline: "none" }}
              />
            </InputGroup>

            <HStack spacing="3">
              <IconButton aria-label="Filter" icon={<ListFilter size={18} />} bg={cardBg} border="none" borderRadius="xl" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" w="12" h="12" color={textColor} _hover={{ bg: inputBg }} />
              <IconButton aria-label="Download" icon={<Download size={18} />} bg={cardBg} border="none" borderRadius="xl" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" w="12" h="12" color={textColor} _hover={{ bg: inputBg }} />
            </HStack>
          </Flex>

          {/* Table Box */}
          <Box bg={cardBg} borderRadius="2rem" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" overflow="hidden" position="relative">
            {loading ? (
              <Box p="10" textAlign="center">
                <Text color={textMuted} fontWeight="medium">{t("students_page.loading")}</Text>
              </Box>
            ) : (
              <>
                <Box w="full" overflowX="auto" pb="4">
                  <Table variant="unstyled" sx={{
                    "tbody tr": { transition: "background 0.2s" },
                    "tbody tr:hover": { bg: inputBg }
                  }}>
                    <Thead>
                      <Tr borderBottom="1px solid" borderColor={borderColor}>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" pl={{ base: 4, md: 8 }} py="6">{t("students_page.table.actions")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" py="6">{t("students_page.table.full_name")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" py="6" display={{ base: "none", md: "table-cell" }}>{t("students_page.table.age")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" py="6" display={{ base: "none", md: "table-cell" }}>{t("students_page.table.classes")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" pr={{ base: 4, md: 8 }} py="6" display={{ base: "none", md: "table-cell" }}>{t("students_page.table.status")}</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {students.map((student, idx) => {
                        const colors = [
                          { bg: primaryBg, text: primaryColor },
                          { bg: highlightBg, text: highlightColor },
                          { bg: errorBg, text: errorText }
                        ];
                        const color = colors[idx % 3];
                        const isYes = student.is_active;

                        return (
                          <Tr key={student.id} position="relative" role="group" cursor="pointer" onClick={() => navigate(`/students/${student.id}/reports`)}>
                            <Td pl={{ base: 4, md: 8 }} py="4">
                              <HStack spacing="2">
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  color={(student.reports_count ?? 0) > 0 ? primaryColor : textMuted}
                                  bg={(student.reports_count ?? 0) > 0 ? primaryBg : "transparent"}
                                  onClick={() => navigate(`/students/${student.id}/reports`)}
                                  borderRadius="xl"
                                  leftIcon={<FileText size={16} />}
                                >
                                  {t("students_page.table.report_btn")} {(student.reports_count ?? 0) > 0 ? `(${student.reports_count})` : ''}
                                </Button>
                              </HStack>
                            </Td>
                            <Td py="4">
                              <Flex align="center" gap="4">
                                <Avatar
                                  size="md"
                                  name={student.full_name}
                                  bg={color.bg}
                                  color={color.text}
                                  fontWeight="bold"
                                />
                                <Box>
                                  <Text fontWeight="bold" color={textColor} fontSize="sm">{student.full_name}</Text>
                                  <Text fontSize="xs" color={textMuted}>ID: {(student.id || '').substring(0, 36)}</Text>
                                </Box>
                              </Flex>
                            </Td>
                            <Td py="4" display={{ base: "none", md: "table-cell" }}>
                              <Text fontWeight="semibold" color={textLabel} fontSize="sm">{student.age ?? '-'}</Text>
                            </Td>
                            <Td py="4" display={{ base: "none", md: "table-cell" }}>
                              {student.classes?.length > 0 ? (
                                <>
                                  <Badge bg={inputBg} color={textLabel} fontFamily="'Manrope', sans-serif" fontSize="xs" px="3" py="1.5" borderRadius="full" textTransform="none" fontWeight="bold">
                                    {student.classes[0].name}
                                  </Badge>
                                  {student.classes.length > 1 && (
                                    <Badge ml="2" bg={primaryBg} color={primaryColor} fontFamily="'Manrope', sans-serif" fontSize="xs" px="2" py="1.5" borderRadius="full" textTransform="none">
                                      +{student.classes.length - 1}
                                    </Badge>
                                  )}
                                </>
                              ) : (
                                <Text color={textMuted} fontSize="sm">—</Text>
                              )}
                            </Td>
                            <Td pr={{ base: 4, md: 8 }} py="4" display={{ base: "none", md: "table-cell" }}>
                              <Badge
                                bg={isYes ? highlightBg : errorBg}
                                color={isYes ? highlightColor : errorText}
                                borderRadius="full"
                                px="3"
                                py="1"
                                textTransform="none"
                                fontWeight="bold"
                                fontSize="xs"
                                display="inline-flex"
                                alignItems="center"
                                gap="1.5"
                              >
                                <Box w="1.5" h="1.5" borderRadius="full" bg={isYes ? highlightColor : errorText} />
                                {isYes ? t("students_page.table.yes") : t("students_page.table.no")}
                              </Badge>
                            </Td>
                          </Tr>
                        )
                      })}
                      {students.length === 0 && !loading && (
                        <Tr>
                          <Td colSpan={5} textAlign="center" py="10" color={textMuted} fontSize="sm">
                            {t("students_page.table.empty")}
                          </Td>
                        </Tr>
                      )}
                    </Tbody>
                  </Table>
                </Box>

                {/* Pagination Footer */}
                {students.length > 0 && (
                  <Flex borderTop="1px solid" borderColor={borderColor} px={{ base: 4, md: 8 }} py="4" justify="space-between" align="center">
                    <Text fontSize="xs" color={textMuted} fontWeight="medium">
                      {t("students_page.pagination.showing")} {students.length > 0 ? '1' : '0'}-{Math.min(10, students.length)} {t("students_page.pagination.of")} {students.length} {t("students_page.pagination.students")}
                    </Text>
                    <HStack spacing="2">
                      <Button size="sm" bg={cardBg} color={textColor} border="1px solid" borderColor={borderColor} borderRadius="md" fontSize="xs">{t("students_page.pagination.prev")}</Button>
                      <Button size="sm" bg={primaryColor} color="white" borderRadius="md" _hover={{ bg: "#0049ca" }} fontSize="xs">{t("students_page.pagination.next")}</Button>
                    </HStack>
                  </Flex>
                )}
              </>
            )}
          </Box>
        </GridItem>
      </Grid>

    </Box>
  );
}
