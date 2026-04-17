import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Button,
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
  Flex,
  useColorModeValue,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import {
  ChevronDown,
  ChevronUp,
  ChevronRight,
  UserPlus,
  Users,
  Download,
  PlusCircle,
  RefreshCw,
  Sparkles,
  School,
  Home,
  Activity,
  FileText
} from 'lucide-react';
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
  topic_nucleo?: string[] | null;
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

function formatTopics(topics?: string[] | string | null, max = 3): string {
  if (!topics) return "—";

  const list = Array.isArray(topics)
    ? topics.map((x) => String(x).trim()).filter(Boolean)
    : String(topics)
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean);

  if (list.length === 0) return "—";

  const first = list.slice(0, max);
  const extra = list.length - first.length;

  return extra > 0 ? `${first.join(", ")} (+${extra})` : first.join(", ");
}

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

export function MicroInterventionCard({
  mi,
  idx,
  accentColor
}: {
  mi: MicroIntervention;
  idx: number;
  accentColor: string;
}) {
  const { t } = useTranslation();
  const steps = normalizeSteps(mi.estrategias_paso_a_paso);

  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.500");
  const textLabel = useColorModeValue("#434654", "gray.400");

  return (
    <Box bg={cardBg} p="5" borderRadius="2xl" border="1px dashed" borderColor={`${accentColor}40`}>
      <Flex gap="4" align="flex-start">
        <Flex w="10" h="10" borderRadius="full" bg={`${accentColor}10`} color={accentColor} align="center" justify="center" fontWeight="black" flexShrink={0}>
          {idx + 1}
        </Flex>
        <Box>
          <Text fontWeight="bold" fontSize="sm" color={textColor}>
            {mi.microobjetivo?.trim() ? mi.microobjetivo : `Microintervención ${idx + 1}`}
          </Text>
          <Text fontSize="xs" color={textLabel} mt="1">
            {formatTopics(mi.topic_nucleo)}{mi.subhabilidad ? ` · ${mi.subhabilidad}` : ''}
          </Text>
        </Box>
      </Flex>

      {/*mi.senal_observable && (
        <Box mt="4">
          <Text fontSize="xs" fontWeight="bold" color={textColor}>{t('reports_page.mi.observable')}</Text>
          <Text fontSize="sm" color={textLabel} mt="1">{mi.senal_observable}</Text>
        </Box>
      )*/}

      {mi.hipotesis_funcional && (
        <Box mt="3">
          <Text fontSize="xs" fontWeight="bold" color={textColor}>{t('reports_page.mi.hypothesis')}</Text>
          <Text fontSize="sm" color={textLabel} mt="1">{mi.hipotesis_funcional}</Text>
        </Box>
      )}

      {steps.length > 0 && (
        <Box mt="3">
          <Text fontSize="xs" fontWeight="bold" color={textColor} mb="1">{t('reports_page.mi.steps')}</Text>
          <Stack spacing="1">
            {steps.map((st, i) => (
              <Text key={i} fontSize="sm" color={textLabel}>• {st}</Text>
            ))}
          </Stack>
        </Box>
      )}

      {(mi.indicador_de_avance || mi.escalamiento) && (
        <Box mt="4" pt="4" borderTop="1px dashed" borderColor="#e1e3e4">
          {mi.indicador_de_avance && (
            <Box mb={mi.escalamiento ? "3" : "0"}>
              <Text fontSize="10px" fontWeight="black" textTransform="uppercase" color={textMuted} mb="1">{t('reports_page.mi.indicator')}</Text>
              <Text fontSize="xs" color={textLabel}>{mi.indicador_de_avance}</Text>
            </Box>
          )}

          {mi.escalamiento && (
            <Box>
              <Text fontSize="10px" fontWeight="black" textTransform="uppercase" color={accentColor} mb="1">{t('reports_page.mi.escalation')}</Text>
              <Text fontSize="10px" color={textLabel} fontStyle="italic">{mi.escalamiento}</Text>
            </Box>
          )}
        </Box>
      )}
    </Box>
  );
}

export default function ReportsPage() {
  const { t } = useTranslation();
  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const pageBg = useColorModeValue("#f8f9fa", "gray.900");
  const inputBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const inputFocusBg = useColorModeValue("#ffffff", "gray.800");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.500");
  const textLabel = useColorModeValue("#434654", "gray.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryBg = useColorModeValue("#e8edff", "blue.900");
  const badgeBg = useColorModeValue("#e1e3e4", "whiteAlpha.200");

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

  const [expandedSignalsByReportId, setExpandedSignalsByReportId] = useState<Record<string, boolean>>({});
  const [expandedNotesByReportId, setExpandedNotesByReportId] = useState<Record<string, boolean>>({});

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
        title: t('reports_page.create_success'),
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
          title: t('reports_page.ai_working'),
          description: t('reports_page.ai_status').replace('{{status}}', lastStatus),
          status: 'info',
          duration: 2500,
          isClosable: true,
        });
        return;
      }

      toast({
        title: t('reports_page.ai_generated'),
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

  const title = loadingStudent ? 'Informes del alumno' : `Informes de ${student?.full_name || 'Alumno'}`;

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

  const selectedReport =
    reports.find((r) => r.id === selectedReportId) ?? null;

  const detectedSignalsFromTeacherReport = (() => {
    if (!selectedReport?.signals_observed) return [];

    const raw = selectedReport.signals_observed;

    // Si detecta separadores → split
    if (/[|•;\n]+/.test(raw)) {
      return raw
        .split(/[|•;\n]+/)
        .map((s) => s.trim())
        .filter(Boolean);
    }

    // Si no → dejarlo como un solo elemento
    return [raw.trim()];
  })();

  function isLongText(value?: string | null, limit = 120) {
    return !!value && value.trim().length > limit;
  }

  return (
    <Box>
      {/* Header */}
      <Box mb="8">
        <HStack spacing="2" mb="2">
          <Text fontSize="sm" fontWeight="medium" color={textMuted} cursor="pointer" _hover={{ color: "#003597" }}>Students</Text>
          <ChevronRight size={14} color={textMuted} />
          <Text fontSize="sm" fontWeight="medium" color={textLabel}>Student Report</Text>
        </HStack>
        <Flex align="flex-end" justify="space-between">
          <Box>
            <Heading as="h1" fontSize={{ base: "3xl", md: "4xl" }} fontWeight="extrabold" color={textColor} fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight">
              {title}
            </Heading>
            <Text color={textLabel} mt="1" fontFamily="'Manrope', monospace" fontSize="sm">
              ID: {studentId}
            </Text>
          </Box>
          <Button
            leftIcon={<Download size={18} />}
            bg={cardBg}
            border="1px solid rgba(195, 197, 215, 0.3)"
            color={textColor}
            borderRadius="xl"
            px="6"
            py="6"
            fontSize="sm"
            fontWeight="bold"
            boxShadow="0px 4px 12px rgba(25, 28, 29, 0.03)"
            _hover={{ bg: "#f8f9fa", transform: "translateY(-1px)" }}
            transition="all 0.2s"
          >
            Export PDF
          </Button>
        </Flex>
      </Box>

      {error && (
        <Alert status="error" mb="6" borderRadius="xl">
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      {/* Tutores Section (Bento Card) */}
      <Box bg={cardBg} borderRadius="2rem" p={{ base: 6, lg: 8 }} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" mb="8">
        <Grid templateColumns={{ base: "1fr", lg: "1fr 1fr" }} gap="12">
          {/* Form Side */}
          <GridItem>
            <Stack spacing="6">
              <Flex align="center" gap="3">
                <Flex align="center" justify="center" w="10" h="10" bg={primaryBg} color={primaryColor} borderRadius="lg">
                  <UserPlus size={20} />
                </Flex>
                <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor}>{t('reports_page.add_guardian_title')}</Heading>
              </Flex>

              {guardianError && (
                <Alert status="error" borderRadius="md">
                  <AlertIcon />
                  {guardianError}
                </Alert>
              )}

              <Grid templateColumns={{ base: "1fr", md: "1fr 1fr" }} gap="4">
                <GridItem colSpan={{ base: 1, md: 2 }}>
                  <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">{t('reports_page.name')}</Text>
                  <Input
                    placeholder={t('reports_page.guardian_name_placeholder')}
                    value={gFullName}
                    onChange={(e) => setGFullName(e.target.value)}
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    py="6"
                    fontSize="sm"
                    color={textColor}
                    _placeholder={{ color: textMuted }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                  />
                </GridItem>

                <GridItem>
                  <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">{t('reports_page.whatsapp')}</Text>
                  <Input
                    placeholder={t('reports_page.guardian_phone_placeholder')}
                    value={gPhone}
                    onChange={(e) => setGPhone(e.target.value)}
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    py="6"
                    fontSize="sm"
                    color={textColor}
                    _placeholder={{ color: textMuted }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                  />
                </GridItem>

                <GridItem>
                  <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">{t('reports_page.parent_type')}</Text>
                  <Select
                    value={gRelationship}
                    onChange={(e) => setGRelationship(e.target.value)}
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    h="12"
                    fontSize="sm"
                    color={textColor}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                  >
                    <option value="madre">Madre</option>
                    <option value="padre">Padre</option>
                    <option value="tutor">Tutor Legal</option>
                    <option value="abuela">Abuela</option>
                    <option value="abuelo">Abuelo</option>
                    <option value="otro">Familiar</option>
                  </Select>
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 2 }}>
                  <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">{t('reports_page.notes_optional')}</Text>
                  <Textarea
                    placeholder={t('reports_page.guardian_notes_placeholder')}
                    value={gNotes}
                    onChange={(e) => setGNotes(e.target.value)}
                    bg={inputBg}
                    border="none"
                    borderRadius="xl"
                    py="3"
                    fontSize="sm"
                    resize="none"
                    rows={2}
                    color={textColor}
                    _placeholder={{ color: textMuted }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                  />
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 2 }}>
                  <Flex flexWrap="wrap" gap="6" pt="2">
                    <Checkbox isChecked={gIsPrimary} onChange={(e) => {
                      const next = e.target.checked;
                      if (next) {
                        const existingPrimary = guardians.some((x) => x.is_active && x.is_primary);
                        setShowPrimaryWarning(existingPrimary);
                      } else {
                        setShowPrimaryWarning(false);
                      }
                      setGIsPrimary(next);
                    }}
                      colorScheme="blue" borderColor="#c3c5d7">
                      <Text fontSize="sm" fontWeight="medium" color={textLabel}>Principal</Text>
                    </Checkbox>

                    <Checkbox isChecked={gReceiveWhatsapp} onChange={(e) => setGReceiveWhatsapp(e.target.checked)} colorScheme="blue" borderColor="#c3c5d7">
                      <Text fontSize="sm" fontWeight="medium" color={textLabel}>{t('reports_page.receive_wa')}</Text>
                    </Checkbox>

                    <Checkbox isChecked={gConsent} onChange={(e) => setGConsent(e.target.checked)} colorScheme="blue" borderColor="#c3c5d7">
                      <Text fontSize="sm" fontWeight="medium" color={textLabel}>{t('reports_page.consent')}</Text>
                    </Checkbox>
                  </Flex>

                  {showPrimaryWarning && gIsPrimary && (
                    <Alert status="warning" borderRadius="md" mt="4">
                      <AlertIcon />
                      <Text fontSize="sm">{t('reports_page.already_primary')} <strong>Principal</strong>.</Text>
                    </Alert>
                  )}
                </GridItem>

                <GridItem colSpan={{ base: 1, md: 2 }} mt="4">
                  <Button
                    w="full"
                    onClick={createGuardian}
                    isLoading={creatingGuardian}
                    isDisabled={!gFullName.trim() || !gPhone.trim() || !gConsent}
                    bgGradient="linear(to-r, #003597, #0049ca)"
                    color="white"
                    borderRadius="xl"
                    py="6"
                    fontWeight="bold"
                    _hover={{ transform: "scale(1.02)", bgGradient: "linear(to-r, #003597, #0049ca)" }}
                    _active={{ transform: "scale(0.98)" }}
                  >
                    Guardar Tutor
                  </Button>
                </GridItem>
              </Grid>
            </Stack>
          </GridItem>

          {/* List Side */}
          <GridItem>
            <Box bg={pageBg} borderRadius="3xl" p="6" h="full">
              <Flex align="center" justify="space-between" mb="6">
                <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor}>{t('reports_page.guardian_list')}</Heading>
                <Badge bg={badgeBg} color={textLabel} px="3" py="1" borderRadius="full" fontSize="xs" fontWeight="bold">
                  {guardians.filter(g => g.is_active).length} Activos
                </Badge>
              </Flex>

              {guardiansLoading && (
                <HStack>
                  <Spinner size="sm" color={primaryColor} />
                  <Text fontSize="sm" color={textLabel}>{t('reports_page.guardians_loading')}</Text>
                </HStack>
              )}

              {guardiansError && <Text fontSize="sm" color="#ba1a1a">{guardiansError}</Text>}

              {!guardiansLoading && !guardiansError && guardians.length === 0 && (
                <Text fontSize="sm" color={textMuted}>
                  Este alumno aún no tiene tutores registrados.
                </Text>
              )}

              {!guardiansLoading && !guardiansError && guardians.length > 0 && (
                <Stack spacing="3">
                  {guardians.filter(g => g.is_active).map(g => {
                    const sendState = canSendWhatsapp(g);
                    const hasSelectedReport = !!selectedReportId;
                    const hasAiForSelected = selectedReportId ? !!aiExistsByReportId[selectedReportId] : false;

                    return (
                      <Box key={g.id} bg={cardBg} p="4" borderRadius="2xl" border="1px solid rgba(195,197,215,0.2)" transition="all 0.2s" _hover={{ borderColor: "#003597" }}>
                        <Flex align="center" justify="space-between">
                          <Flex align="center" gap="4">
                            <Flex w="12" h="12" borderRadius="full" bg={primaryBg} color={primaryColor} align="center" justify="center">
                              <Users size={20} />
                            </Flex>
                            <Box>
                              <Text fontWeight="bold" color={textColor}>{g.full_name}</Text>
                              <Text fontSize="sm" color={textMuted}>{g.relationship ?? "Sin relación"} • {g.whatsapp_phone ?? "Sin WhatsApp"}</Text>
                            </Box>
                          </Flex>
                          {g.is_primary && (
                            <Badge bg={primaryBg} color={primaryColor} px="3" py="1" borderRadius="full" fontSize="10px" fontWeight="black" letterSpacing="widest">
                              PRIMARIO
                            </Badge>
                          )}
                        </Flex>
                        {g.notes && (
                          <Text mt="3" fontSize="sm" color={textLabel} bg={pageBg} p="3" borderRadius="xl">
                            {g.notes}
                          </Text>
                        )}
                        {SHOW_WHATSAPP_BUTTONS && (
                          <Box mt="4" pt="4" borderTop="1px dashed" borderColor="#e1e3e4">
                            <Button
                              size="sm"
                              bg="#e1fedc"
                              color="#006c4a"
                              borderRadius="full"
                              px="4"
                              isDisabled={!hasSelectedReport || !hasAiForSelected || !sendState.ok}
                              isLoading={!!sendingWaByGuardianId[g.id]}
                              onClick={() => handleSendWhatsapp(g)}
                              _hover={{ bg: "#c6fcc0" }}
                            >
                              Enviar WhatsApp
                            </Button>
                            {(!hasSelectedReport || !hasAiForSelected || !sendState.ok) && (
                              <Text fontSize="xs" color={textMuted} mt="2">
                                {!hasSelectedReport ? "Selecciona un reporte." : !hasAiForSelected ? "Genera el apoyo AI primero." : sendState.reason}
                              </Text>
                            )}
                          </Box>
                        )}
                      </Box>
                    );
                  })}
                </Stack>
              )}
            </Box>
          </GridItem>
        </Grid>
      </Box>

      {/* Crear Nuevo Reporte */}
      <Grid templateColumns={{ base: "1fr", lg: "1fr 2fr" }} gap="8" mb="12">
        <GridItem>
          <Box bgGradient="linear(to-br, #003597, #0c50d6)" color="white" p="8" borderRadius="2xl" display="flex" flexDirection="column" justifyContent="space-between" h="full" boxShadow="0px 12px 24px rgba(0, 53, 151, 0.2)">
            <Box>
              <Heading as="h2" size="lg" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" mb="2">{t('reports_page.create_new')}</Heading>
              <Text color="whiteAlpha.80" fontSize="sm" lineHeight="relaxed">
                Nuestra IA analizará las señales detectadas para proporcionar estrategias de intervención personalizadas tanto para el aula como para el hogar.
              </Text>
            </Box>
            <Flex mt="8" align="center" gap="4">
              <Box p="4" bg="whiteAlpha.20" backdropFilter="blur(12px)" borderRadius="2xl">
                <Sparkles size={30} />
              </Box>
              <Text fontSize="xs" fontWeight="bold" lineHeight="tight">{t('reports_page.powered_by')}</Text>
            </Flex>
          </Box>
        </GridItem>

        <GridItem>
          <Box bg={cardBg} borderRadius="2rem" p="8" border="1px solid rgba(195,197,215,0.1)" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" h="full">
            <Stack spacing="6">
              <Box>
                <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">Señales observables</Text>
                <Textarea
                  value={signalsObserved}
                  onChange={(e) => setSignalsObserved(e.target.value)}
                  placeholder={t('reports_page.report_signals_placeholder')}
                  bg={inputBg}
                  border="none"
                  borderRadius="2xl"
                  px="4"
                  py="4"
                  fontSize="sm"
                  rows={3}
                  resize="none"
                  color={textColor}
                  _placeholder={{ color: textMuted }}
                  _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                />
              </Box>
              <Box>
                <Text fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" mb="2">Notas (opcional)</Text>
                <Textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  placeholder={t('reports_page.report_notes_placeholder')}
                  bg={inputBg}
                  border="none"
                  borderRadius="2xl"
                  px="4"
                  py="4"
                  fontSize="sm"
                  rows={2}
                  resize="none"
                  color={textColor}
                  _placeholder={{ color: textMuted }}
                  _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: inputFocusBg }}
                />
              </Box>
              <Flex justify="flex-end">
                <Button
                  onClick={createReport}
                  isLoading={creating}
                  isDisabled={!signalsObserved.trim()}
                  bgGradient="linear(to-r, #003597, #0049ca)"
                  color="white"
                  px="8"
                  py="6"
                  borderRadius="full"
                  fontWeight="bold"
                  boxShadow="0px 10px 15px -3px rgba(0, 53, 151, 0.2)"
                  _hover={{ transform: "translateY(-2px)", bgGradient: "linear(to-r, #003597, #0049ca)" }}
                  _active={{ transform: "scale(0.98)" }}
                  leftIcon={<PlusCircle size={18} />}
                >
                  Crear reporte
                </Button>
              </Flex>
            </Stack>
          </Box>
        </GridItem>
      </Grid>

      {/* Historial de Reportes */}
      <Box mb="12">
        <Flex align="center" justify="space-between" mb="6">
          <Heading as="h2" size="lg" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" color={textColor}>{t('reports_page.history')}</Heading>
          <HStack gap="2">
            <Text fontSize="sm" fontWeight="medium" color={textMuted}>{t('reports_page.filter_by')}</Text>
            <Button variant="ghost" size="sm" color={primaryColor} fontWeight="bold" rightIcon={<ChevronDown size={14} />}>Date</Button>
            <IconButton aria-label={t('reports_page.reload')} icon={<RefreshCw size={16} />} size="sm" variant="ghost" color={textMuted} onClick={() => loadReports()} isLoading={loading} />
          </HStack>
        </Flex>

        <Box bg={cardBg} borderRadius="2rem" overflow="hidden" border="1px solid rgba(195,197,215,0.1)" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)">
          {reports.length === 0 ? (
            <Box p="10" textAlign="center">
              <Text color={textMuted}>{t('reports_page.no_reports')}</Text>
            </Box>
          ) : (
            <Box overflowX="auto" pb="2">
              <Table variant="unstyled" sx={{ "tbody tr": { transition: "background 0.2s" }, "tbody tr:hover": { bg: "rgba(243, 244, 245, 0.3)" } }}>
                <Thead bg="rgba(243, 244, 245, 0.5)">
                  <Tr>
                    <Th fontSize="10px" fontWeight="black" color={textMuted} textTransform="uppercase" letterSpacing="widest" px="6" py="5">Created</Th>
                    <Th fontSize="10px" fontWeight="black" color={textMuted} textTransform="uppercase" letterSpacing="widest" px="6" py="5">Signals Observed</Th>
                    <Th fontSize="10px" fontWeight="black" color={textMuted} textTransform="uppercase" letterSpacing="widest" px="6" py="5">Notes</Th>
                    <Th fontSize="10px" fontWeight="black" color={textMuted} textTransform="uppercase" letterSpacing="widest" px="6" py="5">{t('reports_page.table.id')}</Th>
                    <Th fontSize="10px" fontWeight="black" color={textMuted} textTransform="uppercase" letterSpacing="widest" px="6" py="5" textAlign="right">AI Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {reports.map((r) => {
                    const isSelected = selectedReportId === r.id;
                    const exists = !!aiExistsByReportId[r.id];
                    const reportDate = new Date(r.created_at);

                    return (
                      <Tr key={r.id} bg={isSelected ? "rgba(232, 237, 255, 0.5)" : "transparent"} borderBottom="1px solid rgba(195,197,215,0.1)">
                        <Td px="6" py="5" verticalAlign="top">
                          <Text fontWeight="bold" fontSize="sm" color={textColor}>{reportDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</Text>
                          <Text fontSize="xs" color={textMuted} mt="1">{reportDate.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</Text>
                        </Td>
                        <Td px="6" py="5" verticalAlign="top" maxW="sm">
                          <Box>
                            <Text
                              fontSize="sm"
                              color={textLabel}
                              noOfLines={expandedSignalsByReportId[r.id] ? undefined : 2}
                              whiteSpace={expandedSignalsByReportId[r.id] ? "pre-wrap" : "normal"}
                              wordBreak="break-word"
                            >
                              {r.signals_observed || '-'}
                            </Text>

                            {isLongText(r.signals_observed) && (
                              <Button
                                mt="2"
                                size="xs"
                                variant="ghost"
                                color={primaryColor}
                                fontWeight="bold"
                                rightIcon={
                                  expandedSignalsByReportId[r.id]
                                    ? <ChevronUp size={14} />
                                    : <ChevronDown size={14} />
                                }
                                onClick={() =>
                                  setExpandedSignalsByReportId((prev) => ({
                                    ...prev,
                                    [r.id]: !prev[r.id],
                                  }))
                                }
                              >
                                {expandedSignalsByReportId[r.id] ? 'Ver menos' : 'Ver más'}
                              </Button>
                            )}
                          </Box>
                        </Td>
                        <Td px="6" py="5" verticalAlign="top" maxW="sm">
                          <Box>
                            <Text
                              fontSize="sm"
                              color={textLabel}
                              noOfLines={expandedNotesByReportId[r.id] ? undefined : 2}
                              whiteSpace={expandedNotesByReportId[r.id] ? "pre-wrap" : "normal"}
                              wordBreak="break-word"
                            >
                              {r.notes || 'N/A'}
                            </Text>

                            {isLongText(r.notes) && (
                              <Button
                                mt="2"
                                size="xs"
                                variant="ghost"
                                color={primaryColor}
                                fontWeight="bold"
                                rightIcon={
                                  expandedNotesByReportId[r.id]
                                    ? <ChevronUp size={14} />
                                    : <ChevronDown size={14} />
                                }
                                onClick={() =>
                                  setExpandedNotesByReportId((prev) => ({
                                    ...prev,
                                    [r.id]: !prev[r.id],
                                  }))
                                }
                              >
                                {expandedNotesByReportId[r.id] ? 'Ver menos' : 'Ver más'}
                              </Button>
                            )}
                          </Box>
                        </Td>
                        <Td px="6" py="5" verticalAlign="top">
                          <Text fontSize="xs" fontFamily="'Plus Jakarta Sans', monospace" color={textMuted}>{r.id.substring(0, 10)}...</Text>
                        </Td>
                        <Td px="6" py="5" verticalAlign="top" textAlign="right">
                          <Flex align="center" justify="flex-end" gap="2">
                            <Button
                              size="sm"
                              bg={exists ? "rgba(0, 53, 151, 0.05)" : "transparent"}
                              border={exists ? "none" : "1px solid #e1e3e4"}
                              color={exists ? "#003597" : "#434654"}
                              fontWeight="bold"
                              borderRadius="full"
                              px="4"
                              onClick={() => viewOrGenerateAI(r.id)}
                              isLoading={aiLoading && selectedReportId === r.id}
                              _hover={{ bg: "#003597", color: "white" }}
                            >
                              {exists ? 'Ver apoyo' : 'Generar IA'}
                            </Button>
                            {exists && (
                              <IconButton
                                aria-label={t('reports_page.regenerate')}
                                icon={<RefreshCw size={16} />}
                                size="sm"
                                variant="ghost"
                                color={textMuted}
                                _hover={{ color: "#003597" }}
                                onClick={() => {
                                  setSelectedReportId(r.id);
                                  generateAI(r.id);
                                }}
                                isLoading={aiLoading && selectedReportId === r.id}
                              />
                            )}
                          </Flex>
                        </Td>
                      </Tr>
                    );
                  })}
                </Tbody>
              </Table>
            </Box>
          )}
        </Box>
      </Box>

      {/* Apoyo generado por IA Section */}
      <Box animation="fade-in 0.7s">
        <Flex direction="column" align="center" textAlign="center" mb="8" gap="2">
          <Flex align="center" gap="2" px="4" py="1.5" bg={primaryBg} color={primaryColor} borderRadius="full" fontSize="xs" fontWeight="black" textTransform="uppercase" letterSpacing="widest">
            <Sparkles size={14} />
            IA Insight Active
          </Flex>
          <Heading as="h2" size="xl" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" color={textColor}>{t('reports_page.ai_generated_support')}</Heading>
          <Text color={textLabel} maxW="2xl">
            {!selectedReportId
              ? "Selecciona un reporte en la tabla superior para visualizar las estrategias diferenciadas basadas en el análisis de comportamiento."
              : "Estrategias diferenciadas basadas en el análisis del comportamiento reportado."}
          </Text>
        </Flex>

        {selectedReportId && aiLoading && (
          <Flex justify="center" mb="8">
            <Flex align="center" gap="3" bg={pageBg} p="4" borderRadius="2xl" border="1px solid #e1e3e4">
              <Spinner size="sm" color={primaryColor} />
              <Text fontSize="sm" color={textLabel} fontWeight="bold">{t('reports_page.generating_ai')}</Text>
              {aiJobStatus && <Badge colorScheme="blue">{aiJobStatus}</Badge>}
            </Flex>
          </Flex>
        )}

        {selectedReportId && !aiLoading && !aiReport && (
          <Flex justify="center" mb="8">
            <Text color={textMuted}>{t('reports_page.no_ai_report')}</Text>
          </Flex>
        )}

        {selectedReportId && aiReport && !aiLoading && (
          <Grid templateColumns={{ base: "1fr", xl: "1fr 1fr" }} gap="8">

            {/* Maestro Card */}
            <Box bg={cardBg} borderRadius="2.5rem" p="8" border="1px solid rgba(195,197,215,0.1)" boxShadow="0px 24px 48px rgba(25, 28, 29, 0.06)" position="relative" overflow="hidden">
              <Box position="absolute" top="0" left="0" w="8px" h="full" bg="#0049ca"></Box>
              <Flex align="center" justify="space-between" mb="8">
                <Flex align="center" gap="4">
                  <Flex p="3" bg={primaryBg} color={primaryColor} borderRadius="2xl">
                    <School size={24} />
                  </Flex>
                  <Heading as="h3" size="lg" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor}>{t('reports_page.teacher_version')}</Heading>
                </Flex>
                <VStack align="end" spacing="1">
                  <Text fontSize="xs" fontWeight="bold" color={textMuted}>{t('reports_page.academic_intervention')}</Text>
                  {!aiReport.guardrails_passed && <Badge colorScheme="red" variant="subtle">{t('reports_page.check_guardrails')}</Badge>}
                </VStack>
              </Flex>

              <Stack spacing="6">
                <Box bg={inputBg} borderRadius="2xl" p="5">
                  <Text fontSize="xs" fontWeight="black" textTransform="uppercase" letterSpacing="tighter" color="#0049ca" mb="2">{t('reports_page.executive_summary')}</Text>
                  {isPending ? (
                    <Box mt="2">
                      <Text fontWeight="bold" color="#ba1a1a" mb="2">{t('reports_page.validation_process')}</Text>
                      <Text mb="4" fontSize="sm" color={textLabel}>{pendingMessage}</Text>
                      <Button as="a" href={pendingWhatsappHref} target="_blank" bg="#006c4a" color="white" w="full" size="sm" borderRadius="xl" _hover={{ bg: "#005237" }}>
                        Contactar por WhatsApp
                      </Button>
                    </Box>
                  ) : (
                    <Text fontSize="sm" lineHeight="relaxed" fontWeight="medium" color={textColor}>{aiReport.teacher_version.summary}</Text>
                  )}
                </Box>

                <Box>
                  <Flex align="center" gap="2" mb="3">
                    <Activity size={16} color="#0c50d6" />
                    <Text fontSize="sm" fontWeight="bold" color={textColor}>{t('reports_page.signals_detected')}</Text>
                  </Flex>

                  <Flex flexWrap="wrap" gap="2">
                    {detectedSignalsFromTeacherReport.length > 0 ? (
                      detectedSignalsFromTeacherReport.map((s, idx) => (
                        <Badge
                          key={idx}
                          bg="#e7e8e9"
                          color={textLabel}
                          px="3"
                          py="1.5"
                          borderRadius="full"
                          fontSize="xs"
                          fontWeight="medium"
                          textTransform="none"
                          whiteSpace="normal"
                          wordBreak="break-word"
                          maxW="100%"
                        >
                          {s}
                        </Badge>
                      ))
                    ) : (
                      <Text fontSize="sm" color={textMuted}>{t('reports_page.no_signals')}</Text>
                    )}
                  </Flex>
                </Box>

                <Box border="1px solid rgba(195,197,215,0.2)" borderRadius="2xl" overflow="hidden">
                  <Flex align="center" justify="space-between" p="4" bg={pageBg} cursor="pointer" onClick={() => setExpandTeacher(!expandTeacher)} _hover={{ bg: "#f3f4f5" }} transition="colors">
                    <Flex align="center" gap="3">
                      <FileText size={18} color="#0049ca" />
                      <Text fontWeight="bold" fontSize="sm" color={textColor}>{teacherHasNew ? 'Microintervenciones en el aula' : 'Recomendaciones'}</Text>
                    </Flex>
                    {expandTeacher ? <ChevronUp size={20} color={textMuted} /> : <ChevronDown size={20} color={textMuted} />}
                  </Flex>
                  <Collapse in={expandTeacher}>
                    <Box p="5" bg={cardBg}>
                      {teacherHasNew && teacherMIs.map((mi, idx) => (
                        <Box key={idx} mb={idx === teacherMIs.length - 1 ? 0 : 4}>
                          <MicroInterventionCard mi={mi} idx={idx} accentColor="#0049ca" />
                        </Box>
                      ))}

                      {!teacherHasNew && teacherLegacyRecs.map((rec, idx) => (
                        <Box key={idx} border="1px dashed #c3c5d7" borderRadius="2xl" p="4" mb={idx === teacherLegacyRecs.length - 1 ? 0 : 4}>
                          <Flex justify="space-between" mb="2">
                            <Text fontWeight="bold" color={textColor}>{rec.title}</Text>
                            {rec.when_to_use && <Badge bg={primaryBg} color={primaryColor}>{rec.when_to_use}</Badge>}
                          </Flex>
                          <Stack spacing="1">
                            {rec.steps?.map((st, i) => <Text key={i} fontSize="sm" color={textLabel}>• {st}</Text>)}
                          </Stack>
                        </Box>
                      ))}
                      {!teacherHasNew && teacherLegacyRecs.length === 0 && <Text fontSize="sm" color={textMuted}>{t('reports_page.no_recommendations')}</Text>}
                    </Box>
                  </Collapse>
                </Box>

                {aiReport.guardrails_notes && (
                  <Alert status="warning" borderRadius="xl">
                    <AlertIcon />
                    <Text fontSize="sm">{aiReport.guardrails_notes}</Text>
                  </Alert>
                )}
              </Stack>
            </Box>

            {/* Familia Card */}
            <Box bg={cardBg} borderRadius="2.5rem" p="8" border="1px solid rgba(195,197,215,0.1)" boxShadow="0px 24px 48px rgba(25, 28, 29, 0.06)" position="relative" overflow="hidden">
              <Box position="absolute" top="0" left="0" w="8px" h="full" bg="#7d4ce7"></Box>
              <Flex align="center" justify="space-between" mb="8">
                <Flex align="center" gap="4">
                  <Flex p="3" bg="#e9ddff" color="#5516be" borderRadius="2xl">
                    <Home size={24} />
                  </Flex>
                  <Heading as="h3" size="lg" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor}>{t('reports_page.family_version')}</Heading>
                </Flex>
                <Text fontSize="xs" fontWeight="bold" color={textMuted}>{t('reports_page.home_support')}</Text>
              </Flex>

              <Stack spacing="6">
                <Box bg={inputBg} borderRadius="2xl" p="5">
                  <Text fontSize="xs" fontWeight="black" textTransform="uppercase" letterSpacing="tighter" color="#7d4ce7" mb="2">{t('reports_page.practical_rec')}</Text>
                  {isPending ? (
                    <Box mt="2">
                      <Text fontWeight="bold" color="#ba1a1a" mb="2">{t('reports_page.validation_process')}</Text>
                      <Text mb="4" fontSize="sm" color={textLabel}>{pendingMessage}</Text>
                      <Button as="a" href={pendingWhatsappHref} target="_blank" bg="#006c4a" color="white" w="full" size="sm" borderRadius="xl" _hover={{ bg: "#005237" }}>
                        Contactar por WhatsApp
                      </Button>
                    </Box>
                  ) : (
                    <Text fontSize="sm" lineHeight="relaxed" fontWeight="medium" color={textColor}>{aiReport.parent_version.summary}</Text>
                  )}
                </Box>

                <Box>
                  <Flex align="center" gap="2" mb="3">
                    <Activity size={16} color="#7d4ce7" />
                    <Text fontSize="sm" fontWeight="bold" color={textColor}>{t('reports_page.signals_detected')}</Text>
                  </Flex>

                  <Flex flexWrap="wrap" gap="2">
                    {detectedSignalsFromTeacherReport.length > 0 ? (
                      detectedSignalsFromTeacherReport.map((s, idx) => (
                        <Badge
                          key={idx}
                          bg="#e7e8e9"
                          color={textLabel}
                          px="3"
                          py="1.5"
                          borderRadius="full"
                          fontSize="xs"
                          fontWeight="medium"
                          textTransform="none"
                          whiteSpace="normal"
                          wordBreak="break-word"
                          maxW="full"
                        >
                          {s}
                        </Badge>
                      ))
                    ) : (
                      <Text fontSize="sm" color={textMuted}>{t('reports_page.no_signals')}</Text>
                    )}
                  </Flex>
                </Box>

                <Box border="1px solid rgba(195,197,215,0.2)" borderRadius="2xl" overflow="hidden">
                  <Flex align="center" justify="space-between" p="4" bg={pageBg} cursor="pointer" onClick={() => setExpandParent(!expandParent)} _hover={{ bg: "#f3f4f5" }} transition="colors">
                    <Flex align="center" gap="3">
                      <FileText size={18} color="#7d4ce7" />
                      <Text fontWeight="bold" fontSize="sm" color={textColor}>{parentHasNew ? 'Dinámicas para el hogar' : 'Recomendaciones'}</Text>
                    </Flex>
                    {expandParent ? <ChevronUp size={20} color={textMuted} /> : <ChevronDown size={20} color={textMuted} />}
                  </Flex>
                  <Collapse in={expandParent}>
                    <Box p="5" bg={cardBg}>
                      {parentHasNew && parentMIs.map((mi, idx) => (
                        <Box key={idx} mb={idx === parentMIs.length - 1 ? 0 : 4}>
                          <MicroInterventionCard mi={mi} idx={idx} accentColor="#7d4ce7" />
                        </Box>
                      ))}

                      {!parentHasNew && parentLegacyRecs.map((rec, idx) => (
                        <Box key={idx} border="1px dashed #c3c5d7" borderRadius="2xl" p="4" mb={idx === parentLegacyRecs.length - 1 ? 0 : 4}>
                          <Flex justify="space-between" mb="2">
                            <Text fontWeight="bold" color={textColor}>{rec.title}</Text>
                            {rec.when_to_use && <Badge bg="#e9ddff" color="#5516be">{rec.when_to_use}</Badge>}
                          </Flex>
                          <Stack spacing="1">
                            {rec.steps?.map((st, i) => <Text key={i} fontSize="sm" color={textLabel}>• {st}</Text>)}
                          </Stack>
                        </Box>
                      ))}
                      {!parentHasNew && parentLegacyRecs.length === 0 && <Text fontSize="sm" color={textMuted}>{t('reports_page.no_recommendations')}</Text>}
                    </Box>
                  </Collapse>
                </Box>

                {aiReport.guardrails_notes && (
                  <Alert status="warning" borderRadius="xl">
                    <AlertIcon />
                    <Text fontSize="sm">{aiReport.guardrails_notes}</Text>
                  </Alert>
                )}
              </Stack>
            </Box>
          </Grid>
        )}
      </Box>

    </Box>
  );
}
