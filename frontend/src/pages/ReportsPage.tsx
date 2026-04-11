import { useEffect, useMemo, useState } from 'react';
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
  signals_observed: string;
  notes: string | null;
  created_by_user_id: string;
  created_at: string;
};

// ✅ legacy (si te llega un AI viejo)
type Recommendation = {
  title: string;
  steps: string[];
  when_to_use?: string | null;
};

// ✅ NUEVO: MicroIntervención (IHUI 2.0)
type MicroIntervention = {
  topic_nucleo?: string | null;
  subhabilidad?: string | null;
  microobjetivo?: string | null;
  senal_observable?: string | null;
  hipotesis_funcional?: string | null;
  estrategias_paso_a_paso?: string[] | null;
  frecuencia?: string | null;
  duracion?: string | null;
  indicador_de_avance?: string | null;
  escalamiento?: string | null;
};

// ✅ NUEVO AIVersion: ahora trae microintervenciones (pero mantenemos optional recommendations por compat)
type AIVersion = {
  summary: string;
  signals_detected: string[];
  microintervenciones?: MicroIntervention[]; // ✅ nuevo
  recommendations?: Recommendation[]; // ✅ legacy compat
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

function canSendWhatsapp(g: Guardian): { ok: boolean; reason?: string } {
  if (!g.is_active) return { ok: false, reason: "Tutor inactivo" };
  if (!g.whatsapp_phone) return { ok: false, reason: "Sin teléfono" };
  if (!g.consent_to_contact) return { ok: false, reason: "Sin consentimiento" };
  if (!g.receive_whatsapp) return { ok: false, reason: "No recibe WhatsApp" };
  return { ok: true };
}

const SHOW_WHATSAPP_BUTTONS = false;

function normalizeSteps(raw: any): string[] {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw.map((x) => String(x)).filter(Boolean);
  // a veces llega como string con "1. ... 2. ..."
  if (typeof raw === 'string') {
    const s = raw.trim();
    if (!s) return [];
    // separa por saltos o por " 2. " etc
    const byLines = s.split('\n').map((x) => x.trim()).filter(Boolean);
    if (byLines.length > 1) return byLines;
    // fallback: split por números
    const byNums = s.split(/\s*\d+\.\s*/).map((x) => x.trim()).filter(Boolean);
    return byNums.length ? byNums : [s];
  }
  return [];
}

function MicroInterventionCard({
  mi,
  idx,
  colorScheme,
}: {
  mi: MicroIntervention;
  idx: number;
  colorScheme: string;
}) {
  const steps = normalizeSteps(mi.estrategias_paso_a_paso);

  const headerBadges: string[] = [];
  if (mi.frecuencia) headerBadges.push(`Frecuencia: ${mi.frecuencia}`);
  if (mi.duracion) headerBadges.push(`Duración: ${mi.duracion}`);

  return (
    <Box borderWidth="1px" borderRadius="md" p={3}>
      <HStack justify="space-between" align="start" mb={2}>
        <Box>
          <Text fontWeight="semibold">
            {mi.microobjetivo?.trim()
              ? mi.microobjetivo
              : `Microintervención ${idx + 1}`}
          </Text>
          <Text fontSize="sm" color="gray.600">
            {(mi.topic_nucleo || '—')}{mi.subhabilidad ? ` · ${mi.subhabilidad}` : ''}
          </Text>
        </Box>

        {headerBadges.length > 0 ? (
          <VStack align="end" spacing={1}>
            {headerBadges.slice(0, 2).map((b, i) => (
              <Badge key={i} variant="subtle" colorScheme={colorScheme}>
                {b}
              </Badge>
            ))}
          </VStack>
        ) : null}
      </HStack>

      {mi.senal_observable ? (
        <Box mb={2}>
          <Text fontSize="sm" fontWeight="semibold">
            Señal observable
          </Text>
          <Text fontSize="sm">{mi.senal_observable}</Text>
        </Box>
      ) : null}

      {mi.hipotesis_funcional ? (
        <Box mb={2}>
          <Text fontSize="sm" fontWeight="semibold">
            Hipótesis funcional
          </Text>
          <Text fontSize="sm">{mi.hipotesis_funcional}</Text>
        </Box>
      ) : null}

      {steps.length > 0 ? (
        <Box mt={2}>
          <Text fontSize="sm" fontWeight="semibold" mb={1}>
            Estrategias paso a paso
          </Text>
          <Stack spacing={1}>
            {steps.map((st, i) => (
              <Text key={i} fontSize="sm">
                • {st}
              </Text>
            ))}
          </Stack>
        </Box>
      ) : (
        <Text fontSize="sm" color="gray.500">
          No hay estrategias paso a paso.
        </Text>
      )}

      {(mi.indicador_de_avance || mi.escalamiento) ? (
        <>
          <Divider my={3} />
          {mi.indicador_de_avance ? (
            <Box mb={2}>
              <Text fontSize="sm" fontWeight="semibold">
                Indicador de avance
              </Text>
              <Text fontSize="sm">{mi.indicador_de_avance}</Text>
            </Box>
          ) : null}

          {mi.escalamiento ? (
            <Box>
              <Text fontSize="sm" fontWeight="semibold">
                Escalamiento
              </Text>
              <Text fontSize="sm">{mi.escalamiento}</Text>
            </Box>
          ) : null}
        </>
      ) : null}
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
  const [signalsObserved, setSignalsObserved] = useState('');
  const [notes, setNotes] = useState('');
  const [creating, setCreating] = useState(false);

  // Selected report + AI
  const [selectedReportId, setSelectedReportId] = useState<string | null>(null);
  const [aiReport, setAiReport] = useState<AIReport | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [aiJobStatus, setAiJobStatus] = useState<string | null>(null);

  // ✅ Map to know if AI exists per report
  const [aiExistsByReportId, setAiExistsByReportId] = useState<Record<string, boolean>>({});

  // UI expansions for AI cards
  const [expandTeacher, setExpandTeacher] = useState(true);
  const [expandParent, setExpandParent] = useState(true);

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

  const [sendingWaByGuardianId, setSendingWaByGuardianId] = useState<Record<string, boolean>>({});

  async function sendWhatsappPreview(aiReportId: string, guardianId: string) {
    setSendingWaByGuardianId((p) => ({ ...p, [guardianId]: true }));
    try {
      const res = await api<{ wa_url: string }>(
        `/v1/share-links/${aiReportId}/send-preview?guardian_id=${guardianId}`,
        { method: "POST", auth: true }
      );

      window.open(res.wa_url, "_blank", "noopener,noreferrer");
    } catch (e: any) {
      const msg =
        e?.message ||
        (typeof e === "string" ? e : "No se pudo generar el link de WhatsApp");
      alert(msg);
    } finally {
      setSendingWaByGuardianId((p) => ({ ...p, [guardianId]: false }));
    }
  }

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

      setGFullName("");
      setGPhone("");
      setGRelationship("madre");
      setGNotes("");
      setGIsPrimary(true);
      setGReceiveWhatsapp(true);
      setGConsent(true);

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
      const data = await api<Student>(`/v1/students/${studentId}`, {
        auth: true,
      });
      setStudent(data);
    } catch (e: any) {
      setStudent(null);
    } finally {
      setLoadingStudent(false);
    }
  }

  async function aiExists(reportId: string): Promise<boolean> {
    try {
      const data = await api<any>(
        `/v1/ai-reports?report_id=${encodeURIComponent(reportId)}`,
        { auth: true }
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

      const sorted = [...data].sort((a, b) =>
        a.created_at < b.created_at ? 1 : -1
      );
      setReports(sorted);

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
          signals_observed: signalsObserved.trim(),
          notes: notes.trim() || null,
        },
      });

      toast({
        title: 'Reporte creado',
        status: 'success',
        duration: 1500,
        isClosable: true,
      });

      setSignalsObserved('');
      setNotes('');

      await loadReports();

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
        { auth: true }
      );

      const latest: AIReport | null = Array.isArray(data)
        ? data?.[0] ?? null
        : data ?? null;

      if (!latest) {
        setAiReport(null);
        setAiExistsByReportId((prev) => ({ ...prev, [reportId]: false }));
        return null;
      }

      setAiReport(latest);
      setAiExistsByReportId((prev) => ({ ...prev, [reportId]: true }));
      return latest;
    } catch (e: any) {
      const status = e?.status ?? e?.response?.status;
      if (status === 404) {
        setAiReport(null);
        setAiExistsByReportId((prev) => ({ ...prev, [reportId]: false }));
        return null;
      }
      setError(e?.message ?? 'Error fetching AI report');
      return null;
    } finally {
      setAiLoading(false);
    }
  }

  async function generateAI(reportId: string) {
    setAiLoading(true);
    setError(null);

    try {
      const created = await api<{ job_id: string; status: string }>(
        '/v1/ai-jobs',
        {
          method: 'POST',
          auth: true,
          body: {
            report_id: reportId,
            contexts: ['aula', 'casa'],
          },
        }
      );

      const jobId = created.job_id;

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

      window.dispatchEvent(new Event("playbook:pending-changed"));

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

  async function handleSendWhatsapp(g: Guardian) {
    if (!selectedReportId) return;

    const sendState = canSendWhatsapp(g);
    if (!sendState.ok) return;

    setSendingWaByGuardianId((p) => ({ ...p, [g.id]: true }));
    try {
      const hasAiForSelected = !!aiExistsByReportId[selectedReportId];
      if (!hasAiForSelected) return;

      let aiId = aiReport?.id ?? null;
      if (!aiId || aiReport?.report_id !== selectedReportId) {
        const latest = await fetchAIReport(selectedReportId);
        aiId = latest?.id ?? null;
      }
      if (!aiId) return;

      await sendWhatsappPreview(aiId, g.id);
    } finally {
      setSendingWaByGuardianId((p) => ({ ...p, [g.id]: false }));
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

  const teacherMIs = aiReport?.teacher_version?.microintervenciones ?? [];
  const parentMIs = aiReport?.parent_version?.microintervenciones ?? [];

  const teacherLegacyRecs = aiReport?.teacher_version?.recommendations ?? [];
  const parentLegacyRecs = aiReport?.parent_version?.recommendations ?? [];

  const teacherHasNew = teacherMIs.length > 0;
  const parentHasNew = parentMIs.length > 0;

  const pendingMessage =
    "IHUI detectó que este caso necesita validación humana y queremos asegurarnos de darte una estrategia clara, segura y útil.\n\nEscríbenos por WhatsApp y lo resolvemos contigo en un lapso maximo de 24 hrs:";

  const pendingWhatsappHref =
    "https://wa.me/5213346451964?text=Hola%20IHUI,%20necesito%20ayuda%20con%20un%20caso";

  const isPending =
    !!aiReport &&
    (
      aiReport.teacher_version?.summary?.includes("validación humana") ||
      aiReport.parent_version?.summary?.includes("validación humana")
    );

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

                {!guardiansLoading && !guardiansError && guardians.length > 0 && (
                  <VStack align="stretch" spacing={3} mt={2}>
                    {guardians
                      .filter((g) => g.is_active)
                      .map((g) => {
                        const sendState = canSendWhatsapp(g);
                        const hasSelectedReport = !!selectedReportId;
                        const hasAiForSelected = selectedReportId
                          ? !!aiExistsByReportId[selectedReportId]
                          : false;

                        return (
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

                                {SHOW_WHATSAPP_BUTTONS && (
                                  <Box mt={3}>
                                    <Button
                                      size="sm"
                                      colorScheme="green"
                                      isDisabled={!hasSelectedReport || !hasAiForSelected || !sendState.ok}
                                      isLoading={!!sendingWaByGuardianId[g.id]}
                                      onClick={() => handleSendWhatsapp(g)}
                                    >
                                      Enviar WhatsApp
                                    </Button>

                                    {(!hasSelectedReport || !hasAiForSelected || !sendState.ok) && (
                                      <Text fontSize="xs" color="gray.500" mt={1}>
                                        {!hasSelectedReport
                                          ? "Selecciona un reporte."
                                          : !hasAiForSelected
                                            ? "Genera el apoyo AI primero."
                                            : sendState.reason}
                                      </Text>
                                    )}
                                  </Box>
                                )}
                              </Box>
                            </HStack>
                          </Box>
                        );
                      })}
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
            <GridItem colSpan={{ base: 1, md: 2 }}>
              <FormControl>
                <FormLabel>Señales observables</FormLabel>
                <Text fontSize="sm" color="gray.600" mb={1}>
                  Explica qué señal, conducta o situación se observa en el alumno.
                </Text>
                <Textarea
                  value={signalsObserved}
                  onChange={(e) => setSignalsObserved(e.target.value)}
                  placeholder="Ej: Busca estímulo corporal constante, habla excesiva en clase, dificultad para esperar turnos…"
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
                isDisabled={!signalsObserved.trim()}
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
                    <Th>SIGNALS OBSERVED</Th>
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
                          <Text noOfLines={2}>{r.signals_observed || '-'}</Text>
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

                            {exists && (
                              <Button
                                size="sm"
                                onClick={() => {
                                  setSelectedReportId(r.id);
                                  generateAI(r.id);
                                }}
                                isLoading={aiLoading && selectedReportId === r.id}
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
                  <Badge colorScheme={aiReport.guardrails_passed ? 'green' : 'red'}>
                    {aiReport.guardrails_passed ? 'Guardrails OK' : 'Revisar'}
                  </Badge>
                </HStack>
                <Text fontSize="sm" color="gray.600" mt={1}>
                  {aiReport.model_name} • {new Date(aiReport.created_at).toLocaleString()}
                </Text>
              </CardHeader>
              <CardBody>
                <Text fontWeight="semibold" mb={2}>
                  Resumen
                </Text>

                {isPending ? (
                  <Box
                    p={4}
                    mb={4}
                    borderRadius="md"
                    bg="yellow.50"
                    border="1px solid"
                    borderColor="yellow.300"
                  >
                    <Text fontWeight="bold" mb={2}>
                      ⚠️ Validación en proceso
                    </Text>

                    <Text mb={4}>{pendingMessage}</Text>

                    <Button
                      as="a"
                      href={pendingWhatsappHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      colorScheme="green"
                      width="100%"
                    >
                      Contactar por WhatsApp
                    </Button>
                  </Box>
                ) : (
                  <Text mb={4}>{aiReport.teacher_version.summary}</Text>
                )}

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

                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">
                    {teacherHasNew ? 'Microintervenciones' : 'Recomendaciones'}
                  </Text>
                  <IconButton
                    aria-label="toggle teacher"
                    size="sm"
                    variant="ghost"
                    icon={expandTeacher ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandTeacher((v) => !v)}
                  />
                </HStack>

                <Collapse in={expandTeacher} animateOpacity>
                  <Stack spacing={3} mb={4}>
                    {/* ✅ Nuevo render */}
                    {teacherHasNew &&
                      teacherMIs.map((mi, idx) => (
                        <MicroInterventionCard
                          key={idx}
                          mi={mi}
                          idx={idx}
                          colorScheme="blue"
                        />
                      ))}

                    {/* ✅ Legacy fallback */}
                    {!teacherHasNew && teacherLegacyRecs.length > 0 &&
                      teacherLegacyRecs.map((rec, idx) => (
                        <Box key={idx} borderWidth="1px" borderRadius="md" p={3}>
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
                      ))}

                    {!teacherHasNew && teacherLegacyRecs.length === 0 && (
                      <Text fontSize="sm" color="gray.500">
                        No hay microintervenciones/recomendaciones disponibles.
                      </Text>
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

            {/* Parent */}
            <Card>
              <CardHeader>
                <HStack justify="space-between" align="start">
                  <Box>
                    <Heading size="sm">Versión Familia</Heading>
                    <Text fontSize="sm" color="gray.600" mt={1}>
                      Recomendaciones prácticas para casa.
                    </Text>
                  </Box>
                </HStack>
              </CardHeader>
              <CardBody>
                <Text fontWeight="semibold" mb={2}>
                  Resumen
                </Text>

                {isPending ? (
                  <Box
                    p={4}
                    mb={4}
                    borderRadius="md"
                    bg="yellow.50"
                    border="1px solid"
                    borderColor="yellow.300"
                  >
                    <Text fontWeight="bold" mb={2}>
                      ⚠️ Validación en proceso
                    </Text>

                    <Text mb={4}>{pendingMessage}</Text>

                    <Button
                      as="a"
                      href={pendingWhatsappHref}
                      target="_blank"
                      rel="noopener noreferrer"
                      colorScheme="green"
                      width="100%"
                    >
                      Contactar por WhatsApp
                    </Button>
                  </Box>
                ) : (
                  <Text mb={4}>{aiReport.parent_version.summary}</Text>
                )}

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

                <HStack justify="space-between" mb={2}>
                  <Text fontWeight="semibold">
                    {parentHasNew ? 'Microintervenciones' : 'Recomendaciones'}
                  </Text>
                  <IconButton
                    aria-label="toggle parent"
                    size="sm"
                    variant="ghost"
                    icon={expandParent ? <ChevronUp /> : <ChevronDown />}
                    onClick={() => setExpandParent((v) => !v)}
                  />
                </HStack>

                <Collapse in={expandParent} animateOpacity>
                  <Stack spacing={3} mb={4}>
                    {/* ✅ Nuevo render */}
                    {parentHasNew &&
                      parentMIs.map((mi, idx) => (
                        <MicroInterventionCard
                          key={idx}
                          mi={mi}
                          idx={idx}
                          colorScheme="purple"
                        />
                      ))}

                    {/* ✅ Legacy fallback */}
                    {!parentHasNew && parentLegacyRecs.length > 0 &&
                      parentLegacyRecs.map((rec, idx) => (
                        <Box key={idx} borderWidth="1px" borderRadius="md" p={3}>
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
                      ))}

                    {!parentHasNew && parentLegacyRecs.length === 0 && (
                      <Text fontSize="sm" color="gray.500">
                        No hay microintervenciones/recomendaciones disponibles.
                      </Text>
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
