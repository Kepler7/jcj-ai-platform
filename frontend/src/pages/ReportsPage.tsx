import React, { useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  FormControl,
  FormLabel,
  Grid,
  GridItem,
  Heading,
  HStack,
  Input,
  Spinner,
  Stack,
  Table,
  Tbody,
  Td,
  Text,
  Textarea,
  Th,
  Thead,
  Tr,
  useToast,
  Badge,
  IconButton,
  Collapse,
  Alert,
  AlertIcon,
  VStack,
  Select,
  Checkbox,
} from '@chakra-ui/react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { api } from '../lib/apiClient';
import type { Guardian } from "../types/guardian";

type Role = 'platform_admin' | 'school_admin' | 'teacher';

type Student = {
  id: string;
  full_name: string;
  age: number;
  group: string | null;
  school_id: string;
  is_active: boolean;
  created_at: string;
};

type StudentReport = {
  id: string;
  student_id: string;
  school_id: string;
  strengths: string;
  challenges: string;
  notes: string | null;
  created_by_user_id: string;
  created_at: string;
};

type Recommendation = {
  title: string;
  steps: string[];
  when_to_use?: string | null;
};

type PlanDay = {
  day: number;
  focus: string;
  activity: string;
  success_criteria: string;
};

type AIVersion = {
  summary: string;
  signals_detected: string[];
  recommendations: Recommendation[];
  classroom_plan_7_days?: PlanDay[];
  home_plan_7_days?: PlanDay[];
};

type AIReport = {
  id: string;
  report_id: string;
  student_id: string;
  school_id: string;
  model_name: string;
  teacher_version: AIVersion;
  parent_version: AIVersion;
  guardrails_passed: boolean;
  guardrails_notes: string | null;
  created_at: string;
};

function GuardiansFormCard({ children }: { children: React.ReactNode }) {
  return (
    <Box borderWidth="1px" borderRadius="md" p={4} bg="white">
      <Heading size="sm" mb={3}>
        Tutores
      </Heading>
      <Text fontSize="sm" color="gray.600" mb={4}>
        Agrega y define quién recibe primero.
      </Text>
      {children}
    </Box>
  );
}

function GuardiansListCard({ children }: { children: React.ReactNode }) {
  return (
    <Box borderWidth="1px" borderRadius="md" p={4} bg="white">
      <Heading size="sm" mb={3}>
        Lista de tutores
      </Heading>
      {children}
    </Box>
  );
}


export default function ReportsPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const toast = useToast();

  const [student, setStudent] = useState<Student | null>(null);

  const [reports, setReports] = useState<StudentReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadingStudent, setLoadingStudent] = useState(true);

  const [error, setError] = useState<string | null>(null);

  // Create report form
  const [strengths, setStrengths] = useState('');
  const [challenges, setChallenges] = useState('');
  const [notes, setNotes] = useState('');
  const [creating, setCreating] = useState(false);

  // Selected report + AI
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [aiReport, setAiReport] = useState<AIReport | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiJobStatus, setAiJobStatus] = useState<string | null>(null);

  // ✅ Map to know if AI exists per report (for showing Regenerar only when exists)
  const [aiExistsByReportId, setAiExistsByReportId] = useState<
    Record<string, boolean>
  >({});

  // UI expansions for AI cards
  const [expandTeacherRecs, setExpandTeacherRecs] = useState(true);
  const [expandTeacherPlan, setExpandTeacherPlan] = useState(false);
  const [expandParentRecs, setExpandParentRecs] = useState(true);
  const [expandParentPlan, setExpandParentPlan] = useState(false);

  const studentName = useMemo(() => student?.full_name ?? 'alumno', [student]);

  const [guardians, setGuardians] = useState<Guardian[]>([]);
  const [guardiansLoading, setGuardiansLoading] = useState(false);
  const [guardiansError, setGuardiansError] = useState<string | null>(null);

  const [gFullName, setGFullName] = useState("");
  const [gPhone, setGPhone] = useState("");
  const [gRelationship, setGRelationship] = useState("madre");
  const [gNotes, setGNotes] = useState("");
  const [gIsPrimary, setGIsPrimary] = useState(true);
  const [gReceiveWhatsapp, setGReceiveWhatsapp] = useState(true);
  const [gConsent, setGConsent] = useState(true);
  const [creatingGuardian, setCreatingGuardian] = useState(false);
  const [guardianError, setGuardianError] = useState<string | null>(null);

  const [showPrimaryWarning, setShowPrimaryWarning] = useState(false);

  async function createGuardian() {
    if (!studentId) return;
    setGuardianError(null);
    setCreatingGuardian(true);

    try {
      await api(`/v1/students/${studentId}/guardians`, {
        method: "POST",
        auth: true,
        body: {
          full_name: gFullName.trim(),
          whatsapp_phone: gPhone.trim(),
          relationship: gRelationship.trim(),
          is_primary: gIsPrimary,
          notes: gNotes.trim() || null,
          receive_whatsapp: gReceiveWhatsapp,
          consent_to_contact: gConsent,
        },
      });

      // reset form
      setGFullName("");
      setGPhone("");
      setGRelationship("madre");
      setGNotes("");
      setGIsPrimary(true);
      setGReceiveWhatsapp(true);
      setGConsent(true);

      // refresh list
      await loadGuardians(studentId);
    } catch (e: any) {
      setGuardianError(e?.message ?? "Error creando tutor");
    } finally {
      setCreatingGuardian(false);
    }
  }

  async function loadGuardians(studentId: string) {
    setGuardiansLoading(true);
    setGuardiansError(null);
    try {
      const data = await api<Guardian[]>(`/v1/students/${studentId}/guardians`, {
        auth: true,
      });
      setGuardians(data);
    } catch (e: any) {
      setGuardiansError(e?.message ?? "Failed to load guardians");
    } finally {
      setGuardiansLoading(false);
    }
  }


  async function loadStudent() {
    if (!studentId) return;
    setLoadingStudent(true);
    try {
      // Assumes you have GET /v1/students/{id}
      const data = await api<Student>(`/v1/students/${studentId}`, {
        auth: true,
      });
      setStudent(data);
    } catch (e: any) {
      // Not fatal for reports list, but affects title
      setStudent(null);
    } finally {
      setLoadingStudent(false);
    }
  }

  async function aiExists(reportId: string): Promise<boolean> {
    try {
      const data = await api<any>(
        `/v1/ai-reports?report_id=${encodeURIComponent(reportId)}`,
        {
          auth: true,
        }
      );

      if (Array.isArray(data)) return data.length > 0;
      return !!data?.id;
    } catch (e: any) {
      const status = e?.status ?? e?.response?.status;
      if (status === 404) return false;

      const msg = String(e?.message ?? '');
      if (msg.includes('404')) return false;

      throw e;
    }
  }

  async function loadReports() {
    if (!studentId) return;
    setError(null);
    setLoading(true);

    try {
      const data = await api<StudentReport[]>(
        `/v1/reports?student_id=${encodeURIComponent(studentId)}`,
        { auth: true }
      );

      // newest first
      const sorted = [...data].sort((a, b) =>
        a.created_at < b.created_at ? 1 : -1
      );
      setReports(sorted);

      // ✅ fill AI-exists map
      const entries = await Promise.all(
        sorted.map(async (r) => {
          try {
            const exists = await aiExists(r.id);
            return [r.id, exists] as const;
          } catch {
            return [r.id, false] as const;
          }
        })
      );
      setAiExistsByReportId(Object.fromEntries(entries));

      // Keep selection if still exists
      if (selectedReportId) {
        const still = sorted.find((r) => r.id === selectedReportId);
        if (!still) {
          setSelectedReportId(null);
          setAiReport(null);
        }
      }
    } catch (e: any) {
      setError(e?.message ?? 'Error loading reports');
    } finally {
      setLoading(false);
    }
  }

  async function createReport() {
    if (!studentId) return;
    setError(null);
    setCreating(true);

    try {
      const created = await api<StudentReport>('/v1/reports', {
        method: 'POST',
        auth: true,
        body: {
          student_id: studentId,
          strengths: strengths.trim(),
          challenges: challenges.trim(),
          notes: notes.trim() || null,
        },
      });

      toast({
        title: 'Reporte creado',
        status: 'success',
        duration: 1500,
        isClosable: true,
      });

      // reset
      setStrengths('');
      setChallenges('');
      setNotes('');

      // refresh
      await loadReports();

      // select the created report
      setSelectedReportId(created.id);
      setAiReport(null);
      setAiExistsByReportId((prev) => ({ ...prev, [created.id]: false }));
    } catch (e: any) {
      setError(e?.message ?? 'Error creating report');
    } finally {
      setCreating(false);
    }
  }

  async function fetchAIReport(reportId: string) {
    setAiLoading(true);
    setError(null);

    try {
      const data = await api<any>(
        `/v1/ai-reports?report_id=${encodeURIComponent(reportId)}`,
        {
          auth: true,
        }
      );

      const latest: AIReport | null = Array.isArray(data)
        ? data?.[0] ?? null
        : data ?? null;

      if (!latest) {
        setAiReport(null);
        setAiExistsByReportId((prev) => ({ ...prev, [reportId]: false }));
        return;
      }

      setAiReport(latest);
      setAiExistsByReportId((prev) => ({ ...prev, [reportId]: true }));
    } catch (e: any) {
      const status = e?.status ?? e?.response?.status;
      if (status === 404) {
        setAiReport(null);
        setAiExistsByReportId((prev) => ({ ...prev, [reportId]: false }));
        return;
      }
      setError(e?.message ?? 'Error fetching AI report');
    } finally {
      setAiLoading(false);
    }
  }

  async function generateAI(reportId: string) {
    setAiLoading(true);
    setError(null);

    try {
      // async path
      const created = await api<{ job_id: string; status: string }>(
        '/v1/ai-jobs',
        {
          method: 'POST',
          auth: true,
          body: {
            report_id: reportId,
            contexts: ['aula', 'casa'], // puedes cambiarlo luego
          },
        }
      );

      const jobId = created.job_id;

      // poll status until done/failed
      const maxTries = 40;
      const delayMs = 1200;

      let done = false;
      let lastStatus = 'queued';
      setAiJobStatus('queued');

      for (let i = 0; i < maxTries; i++) {
        const st = await api<any>(`/v1/ai-jobs/${encodeURIComponent(jobId)}`, {
          auth: true,
        });
        lastStatus = st.status;
        setAiJobStatus(st.status);

        if (st.status === 'done') {
          done = true;
          break;
        }
        if (st.status === 'failed') {
          throw new Error(st.last_error || 'AI job failed');
        }
        await new Promise((r) => setTimeout(r, delayMs));
      }

      if (!done) {
        toast({
          title: 'La IA sigue trabajando…',
          description: `Estado: ${lastStatus}. Intenta “Recargar” en unos segundos.`,
          status: 'info',
          duration: 2500,
          isClosable: true,
        });
        return;
      }

      toast({
        title: 'Apoyo generado',
        status: 'success',
        duration: 1600,
        isClosable: true,
      });

      // fetch latest AI report
      setAiJobStatus(null);
      await fetchAIReport(reportId);
    } catch (e: any) {
      setError(e?.message ?? 'Error generating AI report');
      setAiJobStatus(null);
    } finally {
      setAiLoading(false);
    }
  }

  async function viewOrGenerateAI(reportId: string) {
    const exists = !!aiExistsByReportId[reportId];
    setSelectedReportId(reportId);
    setAiReport(null);

    if (exists) {
      await fetchAIReport(reportId);
    } else {
      await generateAI(reportId);
    }
  }

  useEffect(() => {
    if (!studentId) return;
    loadStudent();
    loadGuardians(studentId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  useEffect(() => {
    if (!studentId) return;
    loadReports();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studentId]);

  // When selected report changes, auto-fetch AI if it exists
  useEffect(() => {
    if (!selectedReportId) return;
    const exists = !!aiExistsByReportId[selectedReportId];
    if (exists) {
      fetchAIReport(selectedReportId);
    } else {
      setAiReport(null);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedReportId]);

  const title = loadingStudent
    ? 'Reportes del alumno'
    : `Reportes de ${studentName}`;

  return (
    <Box p={6}>
      <HStack justify="space-between" align="flex-start" mb={4}>
        <Box>
          <Heading size="lg">{title}</Heading>
          <Text color="gray.600" mt={1}>
            Student ID: {studentId}
          </Text>
        </Box>
        <Box mt={4} p={4} borderWidth="1px" borderRadius="lg">
          <Heading size="sm" mb={3}>
            Tutores
          </Heading>

          <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap={6} alignItems="start">
            {/* IZQUIERDA: FORM */}
            <GridItem>
              <Box p={4} borderWidth="1px" borderRadius="md">
                <Heading size="sm" mb={3}>
                  Agregar tutor
                </Heading>

                {guardianError && (
                  <Alert status="error" mb={3}>
                    <AlertIcon />
                    {guardianError}
                  </Alert>
                )}

                <Stack spacing={3}>
                  <Input
                    placeholder="Nombre completo"
                    value={gFullName}
                    onChange={(e) => setGFullName(e.target.value)}
                  />

                  <Input
                    placeholder="WhatsApp (ej. +5213312345678)"
                    value={gPhone}
                    onChange={(e) => setGPhone(e.target.value)}
                  />

                  <Select value={gRelationship} onChange={(e) => setGRelationship(e.target.value)}>
                    <option value="madre">Madre</option>
                    <option value="padre">Padre</option>
                    <option value="tutor">Tutor</option>
                    <option value="abuela">Abuela</option>
                    <option value="abuelo">Abuelo</option>
                    <option value="otro">Otro</option>
                  </Select>

                  <Textarea
                    placeholder="Notas (opcional)"
                    value={gNotes}
                    onChange={(e) => setGNotes(e.target.value)}
                  />

                  <HStack spacing={6} flexWrap="wrap">
                    <Checkbox
                      isChecked={gIsPrimary}
                      onChange={(e) => {
                        const next = e.target.checked;

                        // Si lo está activando y ya existe un primario (distinto al que estás creando),
                        // mostramos warning.
                        if (next) {
                          const existingPrimary = guardians.some((x) => x.is_active && x.is_primary);
                          setShowPrimaryWarning(existingPrimary);
                        } else {
                          setShowPrimaryWarning(false);
                        }

                          setGIsPrimary(next);
                        }}
                      >
                      Principal
                    </Checkbox>


                    <Checkbox
                      isChecked={gReceiveWhatsapp}
                      onChange={(e) => setGReceiveWhatsapp(e.target.checked)}
                    >
                      Recibir WhatsApp
                    </Checkbox>

                    <Checkbox isChecked={gConsent} onChange={(e) => setGConsent(e.target.checked)}>
                      Consentimiento contacto
                    </Checkbox>
                  </HStack>
                  {showPrimaryWarning && gIsPrimary && (
                    <Alert status="warning" borderRadius="md">
                      <AlertIcon />
                      Ya existe un tutor marcado como <strong>Principal</strong>. Si guardas este tutor como principal,
                      el anterior dejará de ser principal.
                    </Alert>
                  )}


                  <Button
                    onClick={createGuardian}
                    isLoading={creatingGuardian}
                    isDisabled={!gFullName.trim() || !gPhone.trim() || !gConsent}
                    colorScheme="blue"
                    alignSelf="flex-start"
                  >
                    Guardar tutor
                  </Button>
                </Stack>
              </Box>
            </GridItem>

            {/* DERECHA: LISTA */}
            <GridItem>
              <Box p={4} borderWidth="1px" borderRadius="md">
                <Heading size="sm" mb={3}>
                  Lista de tutores
                </Heading>

                {guardiansLoading && (
                  <HStack>
                    <Spinner size="sm" />
                    <Text fontSize="sm">Cargando tutores…</Text>
                  </HStack>
                )}

                {guardiansError && (
                  <Text fontSize="sm" color="red.500">
                    {guardiansError}
                  </Text>
                )}

                {!guardiansLoading && !guardiansError && guardians.length === 0 && (
                  <Text fontSize="sm" color="gray.500">
                    Este alumno aún no tiene tutores registrados.
                  </Text>
                )}

                {!guardiansLoading && guardians.length > 0 && (
                  <VStack align="stretch" spacing={3} mt={2}>
                    {guardians
                      .filter((g) => g.is_active)
                      .map((g) => (
                        <Box key={g.id} p={3} borderWidth="1px" borderRadius="md">
                          <HStack justify="space-between" align="start">
                            <Box>
                              <HStack>
                                <Text fontWeight="semibold">{g.full_name}</Text>
                                {g.is_primary && <Badge colorScheme="green">Primario</Badge>}
                              </HStack>

                              <Text fontSize="sm" color="gray.600">
                                {g.relationship ?? "Sin relación"} · {g.whatsapp_phone ?? "Sin WhatsApp"}
                              </Text>

                              {g.notes && (
                                <>
                                  <Divider my={2} />
                                  <Text fontSize="sm">{g.notes}</Text>
                                </>
                              )}
                            </Box>
                          </HStack>
                        </Box>
                      ))}
                  </VStack>
                )}
              </Box>
            </GridItem>
          </Grid>
        </Box>

        <Button onClick={() => loadReports()} variant="outline">
          Recargar
        </Button>
      </HStack>

      {error && (
        <Alert status="error" mb={4}>
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      {/* Create Report */}
      <Card mb={6}>
        <CardHeader>
          <Heading size="md">Crear nuevo reporte</Heading>
          <Text color="gray.600" mt={1}>
            Fortalezas, retos y notas educativas (sin lenguaje clínico).
          </Text>
        </CardHeader>
        <CardBody>
          <Grid templateColumns={{ base: '1fr', md: '1fr 1fr' }} gap={4}>
            <GridItem>
              <FormControl>
                <FormLabel>Fortalezas</FormLabel>
                <Textarea
                  value={strengths}
                  onChange={(e) => setStrengths(e.target.value)}
                  placeholder="Ej: Sigue indicaciones con apoyo visual, participa cuando se anticipa…"
                  rows={4}
                />
              </FormControl>
            </GridItem>

            <GridItem>
              <FormControl>
                <FormLabel>Retos</FormLabel>
                <Textarea
                  value={challenges}
                  onChange={(e) => setChallenges(e.target.value)}
                  placeholder="Ej: Se frustra al esperar turnos, requiere recordatorios…"
                  rows={4}
                />
              </FormControl>
            </GridItem>

            <GridItem colSpan={{ base: 1, md: 2 }}>
              <FormControl>
                <FormLabel>Notas (opcional)</FormLabel>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder="Contexto adicional (opcional)…"
                  rows={3}
                />
              </FormControl>
            </GridItem>

            <GridItem colSpan={{ base: 1, md: 2 }}>
              <Button
                onClick={createReport}
                isLoading={creating}
                isDisabled={!strengths.trim() || !challenges.trim()}
                colorScheme="blue"
              >
                Crear reporte
              </Button>
            </GridItem>
          </Grid>
        </CardBody>
      </Card>

      {/* Reports list */}
      <Card>
        <CardHeader>
          <HStack justify="space-between">
            <Heading size="md">Reportes</Heading>
            {loading && (
              <HStack>
                <Spinner size="sm" />
                <Text color="gray.600">Cargando…</Text>
              </HStack>
            )}
          </HStack>
        </CardHeader>
        <CardBody>
          {reports.length === 0 ? (
            <Text color="gray.600">Aún no hay reportes para este alumno.</Text>
          ) : (
            <Box overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>CREATED</Th>
                    <Th>STRENGTHS</Th>
                    <Th>CHALLENGES</Th>
                    <Th>NOTES</Th>
                    <Th>ID</Th>
                    <Th>AI</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {reports.map((r) => {
                    const isSelected = selectedReportId === r.id;
                    const exists = !!aiExistsByReportId[r.id];

                    return (
                      <Tr
                        key={r.id}
                        bg={isSelected ? 'blue.50' : 'transparent'}
                        _hover={{ bg: isSelected ? 'blue.50' : 'gray.50' }}
                      >
                        <Td whiteSpace="nowrap">
                          {new Date(r.created_at).toLocaleString()}
                        </Td>
                        <Td maxW="260px">
                          <Text noOfLines={2}>{r.strengths}</Text>
                        </Td>
                        <Td maxW="260px">
                          <Text noOfLines={2}>{r.challenges}</Text>
                        </Td>
                        <Td maxW="260px">
                          <Text noOfLines={2}>{r.notes || '-'}</Text>
                        </Td>
                        <Td whiteSpace="nowrap">
                          <Text fontSize="xs" color="gray.600">
                            {r.id}
                          </Text>
                        </Td>
                        <Td>
                          <HStack>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => viewOrGenerateAI(r.id)}
                              isLoading={aiLoading && selectedReportId === r.id}
                            >
                              {exists ? 'Ver apoyo' : 'Generar'}
                            </Button>

                            {/* ✅ Regenerar SOLO si ya existe */}
                            {exists && (
                              <Button
                                size="sm"
                                onClick={() => {
                                  setSelectedReportId(r.id);
                                  generateAI(r.id);
                                }}
                                isLoading={
                                  aiLoading && selectedReportId === r.id
                                }
                              >
                                Regenerar
                              </Button>
                            )}
                          </HStack>
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            </Box>
          )}
        </CardBody>
      </Card>

      {/* AI section */}
      <Box mt={6}>
        <Heading size="md" mb={2}>
          Apoyo generado por IA
        </Heading>

        {!selectedReportId ? (
          <Text color="gray.600">
            Selecciona un reporte para ver o generar el apoyo.
          </Text>
        ) : aiLoading ? (
          <Alert status="info" borderRadius="md">
            <AlertIcon />
            <HStack>
              <Spinner size="sm" />
              <Text fontSize="sm">
                Generando apoyo con IA...
                {aiJobStatus && (
                  <Badge ml={2} colorScheme="blue">
                    {aiJobStatus}
                  </Badge>
                )}
              </Text>
            </HStack>
          </Alert>
        ) : !aiReport ? (
          <Text color="gray.600">No hay AI report aún para este reporte.</Text>
        ) : (
          <Grid templateColumns={{ base: '1fr', lg: '1fr 1fr' }} gap={4}>
            {/* Teacher */}
            <Card>
              <CardHeader>
                <HStack justify="space-between">
                  <Heading size="sm">Versión Maestro</Heading>
                  <Badge
                    colorScheme={aiReport.guardrails_passed ? 'green' : 'red'}
                  >
                    {aiReport.guardrails_passed ? 'Guardrails OK' : 'Revisar'}
                  </Badge>
                </HStack>
                <Text fontSize="sm" color="gray.600" mt={1}>
                  {aiReport.model_name} •{' '}
                  {new Date(aiReport.created_at).toLocaleString()}
                </Text>
              </CardHeader>
              <CardBody>
                <Text fontWeight="semibold" mb={2}>
                  Resumen
                </Text>
                <Text mb={4}>{aiReport.teacher_version.summary}</Text>

                <Divider my={3} />

                <Text fontWeight="semibold" mb={2}>
                  Señales detectadas
                </Text>
                <Stack spacing={1} mb={4}>
                  {aiReport.teacher_version.signals_detected?.map((s, idx) => (
                    <Text key={idx}>• {s}</Text>
                  ))}
                </Stack>

                <Divider my={3} />

                {/* Recomendaciones collapsible */}
                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">Recomendaciones</Text>
                  <IconButton
                    aria-label="toggle teacher recs"
                    size="sm"
                    variant="ghost"
                    icon={expandTeacherRecs ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandTeacherRecs((v) => !v)}
                  />
                </HStack>
                <Collapse in={expandTeacherRecs} animateOpacity>
                  <Stack spacing={3} mb={4}>
                    {aiReport.teacher_version.recommendations?.map(
                      (rec, idx) => (
                        <Box
                          key={idx}
                          borderWidth="1px"
                          borderRadius="md"
                          p={3}
                        >
                          <HStack justify="space-between" mb={1}>
                            <Text fontWeight="semibold">{rec.title}</Text>
                            {rec.when_to_use ? (
                              <Badge variant="subtle" colorScheme="blue">
                                {rec.when_to_use}
                              </Badge>
                            ) : null}
                          </HStack>
                          <Stack spacing={1} mt={2}>
                            {rec.steps?.map((st, i) => (
                              <Text key={i} fontSize="sm">
                                • {st}
                              </Text>
                            ))}
                          </Stack>
                        </Box>
                      )
                    )}
                  </Stack>
                </Collapse>

                <Divider my={3} />

                {/* Plan 7 days collapsible */}
                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">Plan 7 días (aula)</Text>
                  <IconButton
                    aria-label="toggle teacher plan"
                    size="sm"
                    variant="ghost"
                    icon={expandTeacherPlan ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandTeacherPlan((v) => !v)}
                  />
                </HStack>
                <Collapse in={expandTeacherPlan} animateOpacity>
                  <Stack spacing={2}>
                    {(aiReport.teacher_version.classroom_plan_7_days ?? []).map(
                      (d) => (
                        <Box
                          key={d.day}
                          borderWidth="1px"
                          borderRadius="md"
                          p={3}
                        >
                          <Text fontWeight="semibold">
                            Día {d.day}: {d.focus}
                          </Text>
                          <Text fontSize="sm" mt={1}>
                            <b>Actividad:</b> {d.activity}
                          </Text>
                          <Text fontSize="sm" mt={1}>
                            <b>Criterio de éxito:</b> {d.success_criteria}
                          </Text>
                        </Box>
                      )
                    )}
                  </Stack>
                </Collapse>
              </CardBody>
            </Card>

            {/* Parent */}
            <Card>
              <CardHeader>
                <Heading size="sm">Versión Familia</Heading>
                <Text fontSize="sm" color="gray.600" mt={1}>
                  Recomendaciones prácticas para casa.
                </Text>
              </CardHeader>
              <CardBody>
                <Text fontWeight="semibold" mb={2}>
                  Resumen
                </Text>
                <Text mb={4}>{aiReport.parent_version.summary}</Text>

                <Divider my={3} />

                <Text fontWeight="semibold" mb={2}>
                  Señales detectadas
                </Text>
                <Stack spacing={1} mb={4}>
                  {aiReport.parent_version.signals_detected?.map((s, idx) => (
                    <Text key={idx}>• {s}</Text>
                  ))}
                </Stack>

                <Divider my={3} />

                {/* Recomendaciones collapsible */}
                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">Recomendaciones</Text>
                  <IconButton
                    aria-label="toggle parent recs"
                    size="sm"
                    variant="ghost"
                    icon={expandParentRecs ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandParentRecs((v) => !v)}
                  />
                </HStack>
                <Collapse in={expandParentRecs} animateOpacity>
                  <Stack spacing={3} mb={4}>
                    {aiReport.parent_version.recommendations?.map(
                      (rec, idx) => (
                        <Box
                          key={idx}
                          borderWidth="1px"
                          borderRadius="md"
                          p={3}
                        >
                          <HStack justify="space-between" mb={1}>
                            <Text fontWeight="semibold">{rec.title}</Text>
                            {rec.when_to_use ? (
                              <Badge variant="subtle" colorScheme="purple">
                                {rec.when_to_use}
                              </Badge>
                            ) : null}
                          </HStack>
                          <Stack spacing={1} mt={2}>
                            {rec.steps?.map((st, i) => (
                              <Text key={i} fontSize="sm">
                                • {st}
                              </Text>
                            ))}
                          </Stack>
                        </Box>
                      )
                    )}
                  </Stack>
                </Collapse>

                <Divider my={3} />

                {/* Plan 7 days collapsible */}
                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">Plan 7 días (casa)</Text>
                  <IconButton
                    aria-label="toggle parent plan"
                    size="sm"
                    variant="ghost"
                    icon={expandParentPlan ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandParentPlan((v) => !v)}
                  />
                </HStack>
                <Collapse in={expandParentPlan} animateOpacity>
                  <Stack spacing={2}>
                    {(aiReport.parent_version.home_plan_7_days ?? []).map(
                      (d) => (
                        <Box
                          key={d.day}
                          borderWidth="1px"
                          borderRadius="md"
                          p={3}
                        >
                          <Text fontWeight="semibold">
                            Día {d.day}: {d.focus}
                          </Text>
                          <Text fontSize="sm" mt={1}>
                            <b>Actividad:</b> {d.activity}
                          </Text>
                          <Text fontSize="sm" mt={1}>
                            <b>Criterio de éxito:</b> {d.success_criteria}
                          </Text>
                        </Box>
                      )
                    )}
                  </Stack>
                </Collapse>

                {aiReport.guardrails_notes ? (
                  <Box mt={4}>
                    <Alert status="warning">
                      <AlertIcon />
                      <Text fontSize="sm">{aiReport.guardrails_notes}</Text>
                    </Alert>
                  </Box>
                ) : null}
              </CardBody>
            </Card>
          </Grid>
        )}
      </Box>
    </Box>
  );
}
