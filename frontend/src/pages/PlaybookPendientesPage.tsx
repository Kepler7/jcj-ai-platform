import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  AlertIcon,
  Badge,
  Box,
  Button,
  Code,
  Divider,
  Heading,
  HStack,
  Modal,
  ModalBody,
  ModalCloseButton,
  ModalContent,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
  Select,
  Spinner,
  Stack,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  VStack,
  useDisclosure,
  useToast,
  Input
} from "@chakra-ui/react";
import { useNavigate } from "react-router-dom";
import { api } from "../lib/apiClient";
import {
  getLatestPlaybookSync,
  startPlaybookSync,
  type PlaybookSyncStatusResponse,
} from "../services/playbooks";

type StatusFilter = "pending" | "resolved" | "all";

type PlaybookFallbackEvent = {
  id: string;
  school_id: string;
  student_id: string;
  report_id: string;
  ai_report_id: string | null;
  topic_nucleo: string | null;
  signals_detected?: string[] | null;
  reason: string;
  query_text: string | null;
  model_output_summary: string | null;
  created_by_user_id: string | null;
  created_at: string;
  resolved_at: string | null;
};

type StudentReport = {
  id: string;
  student_id: string;
  school_id: string;
  strengths?: string | null;
  challenges?: string | null;
  notes: string | null;
  created_at: string;
  signals_observed: string | null;
};

type MicroIntervention = {
  duracion: string;
  frecuencia: string;
  escalamiento: string;
  subhabilidad: string;
  topic_nucleo: string;
  microobjetivo: string;
  senal_observable: string;
  hipotesis_funcional: string;
  indicador_de_avance: string;
  estrategias_paso_a_paso: string[];
};

type AIVersion = {
  summary: string;
  signals_detected?: string[];
  microintervenciones?: MicroIntervention[];
};

type AIReport = {
  id: string;
  school_id: string;
  student_id: string;
  report_id: string;
  generated_by_user_id: string;
  model_name: string;
  teacher_version: AIVersion;
  parent_version: AIVersion;
  signals_detected: string[];
  guardrails_passed: boolean;
  guardrails_notes: string | null;
  created_at: string;
};

type PlaybookPreview = {
  id: string;
  topic_nucleo?: string | null;
  subhabilidad?: string | null;
  senal_observable?: string | null;
  age_min?: number | null;
  age_max?: number | null;
};

type AIPrediction = {
  id: string;
  report_id: string;
  predicted_playbook_id: string | null;
  predicted_playbook_base_row: string | null;
  status: string;
  confidence_score: number | null;
  confidence_gap: number | null;
  top_candidates_json: string[] | null;
  top_scores_json: number[] | null;
  retrieval_version: string | null;
  reranker_version: string | null;
  used_hyde: boolean;
  model_name: string | null;
  resolved_by_human: boolean;
  final_playbook_id: string | null;
  created_at: string;

  predicted_playbook_preview?: PlaybookPreview | null;
  top_candidates_preview?: PlaybookPreview[] | null;
};

type PendingRow = {
  row_type: "fallback" | "prediction_pending";
  id: string;
  report_id: string;
  student_id: string;
  school_id: string;
  ai_report_id: string | null;

  reason: string;
  query_text: string | null;
  model_output_summary: string | null;
  topic_nucleo: string | null;
  signals_detected?: string[] | null;

  resolved_at: string | null;
  created_at: string;

  // prediction_pending
  prediction_id?: string;
  predicted_playbook_id?: string | null;
  confidence_score?: number | null;
  confidence_gap?: number | null;
  top_candidates_json?: string[] | null;

  // previews enriquecidos desde backend
  predicted_playbook_preview?: PlaybookPreview | null;
  top_candidates_preview?: PlaybookPreview[] | null;
};

function safeText(x: unknown) {
  if (x === null || x === undefined) return "";
  return String(x);
}

function truncate(text: string | null | undefined, max = 100) {
  const value = safeText(text).trim();
  if (!value) return "-";
  return value.length <= max ? value : `${value.slice(0, max).trim()}...`;
}

function formatReason(reason: string | null | undefined) {
  if (!reason) return "-";
  return String(reason).toUpperCase();
}

function formatSignals(signals?: string[] | null) {
  if (!signals || signals.length === 0) return "-";
  const first = signals.slice(0, 3);
  const extra = signals.length - first.length;
  return extra > 0 ? `${first.join(", ")} (+${extra})` : first.join(", ");
}

export default function PlaybookPendientesPage() {
  const navigate = useNavigate();
  const toast = useToast();
  const { isOpen, onOpen, onClose } = useDisclosure();

  const [rows, setRows] = useState<PendingRow[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");

  const [selected, setSelected] = useState<PendingRow | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [reportDetail, setReportDetail] = useState<StudentReport | null>(null);
  const [aiDetail, setAiDetail] = useState<AIReport | null>(null);

  const [selectedPlaybookId, setSelectedPlaybookId] = useState<string | null>(null);
  const [selectedPlaybookDetail, setSelectedPlaybookDetail] = useState<any | null>(null);
  const [loadingPlaybookDetail, setLoadingPlaybookDetail] = useState(false);

  const [pendingPrediction, setPendingPrediction] =
    useState<AIPrediction | null>(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [approvingSuggestion, setApprovingSuggestion] = useState(false);

  const [resolvingById, setResolvingById] = useState<Record<string, boolean>>(
    {}
  );

  const [isSyncing, setIsSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<string | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [latestSync, setLatestSync] =
    useState<PlaybookSyncStatusResponse | null>(null);

  const [showAlternativeSearch, setShowAlternativeSearch] = useState(false);
  const [playbookSearchQuery, setPlaybookSearchQuery] = useState("");
  const [playbookSearchResults, setPlaybookSearchResults] = useState<PlaybookPreview[]>([]);
  const [searchingPlaybooks, setSearchingPlaybooks] = useState(false);

  function renderPlaybookPreview(pb?: PlaybookPreview | null) {
    if (!pb) return null;

    const isSelected = selectedPlaybookId === pb.id;

    return (
      <Box
        borderWidth="2px"
        borderColor={isSelected ? "blue.400" : "gray.200"}
        borderRadius="md"
        p={3}
        bg={isSelected ? "blue.50" : "gray.50"}
        cursor="pointer"
        onClick={() => loadPlaybookDetail(pb.id)}
        _hover={{ borderColor: "blue.300", bg: "blue.50" }}
      >
        <HStack justify="space-between" align="start">
          <Text fontSize="sm" fontWeight="semibold">
            {pb.topic_nucleo || "Sin topic_nucleo"}
          </Text>

          {isSelected ? (
            <Badge colorScheme="blue">Seleccionado</Badge>
          ) : null}
        </HStack>

        {pb.subhabilidad ? (
          <Text fontSize="sm" color="gray.700" mt={1}>
            Subhabilidad: {pb.subhabilidad}
          </Text>
        ) : null}

        {pb.senal_observable ? (
          <Text fontSize="sm" color="gray.700" mt={1}>
            Señal observable: {pb.senal_observable}
          </Text>
        ) : null}

        <HStack mt={2} spacing={2} flexWrap="wrap">
          <Code fontSize="xs">{pb.id}</Code>
          {(pb.age_min !== null && pb.age_min !== undefined) ||
            (pb.age_max !== null && pb.age_max !== undefined) ? (
            <Badge variant="subtle">
              Edad: {pb.age_min ?? "?"}–{pb.age_max ?? "?"}
            </Badge>
          ) : null}
        </HStack>
      </Box>
    );
  }

  async function loadLatestSync() {
    try {
      const latest = await getLatestPlaybookSync();
      setLatestSync(latest);
      setSyncStatus(latest?.status ?? null);
      return latest;
    } catch {
      setLatestSync(null);
      setSyncStatus(null);
      return null;
    }
  }

  async function handleReprocessPlaybooks() {
    setSyncError(null);
    setIsSyncing(true);

    try {
      const result = await startPlaybookSync();

      setSyncStatus(result.status);

      toast({
        title: "Sincronización iniciada",
        description: `Job ${result.job_id} en estado: ${result.status}`,
        status: "success",
        duration: 4000,
        isClosable: true,
      });

      await loadLatestSync();
    } catch (e: any) {
      const message =
        e instanceof Error
          ? e.message
          : e?.message ?? "No se pudo iniciar la sincronización";

      setSyncError(message);
      setIsSyncing(false);

      toast({
        title: "Error al reprocesar playbooks",
        description: message,
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    }
  }

  function closeDetail() {
    onClose();
    setSelected(null);
    setDetailError(null);
    setReportDetail(null);
    setAiDetail(null);
    setPendingPrediction(null);
    setPredictionLoading(false);
    setApprovingSuggestion(false);
    setSelectedPlaybookId(null);
    setSelectedPlaybookDetail(null);
    setLoadingPlaybookDetail(false);
    setShowAlternativeSearch(false);
    setPlaybookSearchQuery("");
    setPlaybookSearchResults([]);
  }

  async function resolveEvent(id: string) {
    setResolvingById((p) => ({ ...p, [id]: true }));
    setError(null);

    try {
      await api(`/v1/playbook-fallbacks/${id}/resolve`, {
        method: "POST",
        auth: true,
      });

      await load();
      window.dispatchEvent(new Event("playbook:pending-changed"));

      toast({
        title: "Pendiente resuelto",
        status: "success",
        duration: 3000,
        isClosable: true,
      });

      if (selected?.id === id) {
        closeDetail();
      }
    } catch (e: any) {
      setError(e?.message ?? "No se pudo resolver el evento");
      toast({
        title: "Error al resolver",
        description: e?.message ?? "No se pudo resolver el evento",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setResolvingById((p) => ({ ...p, [id]: false }));
    }
  }

  async function approvePredictionSuggestion(
    predictionId: string,
    fallbackEventId?: string
  ) {
    setApprovingSuggestion(true);
    setError(null);

    try {
      await api("/v1/ai-feedback", {
        method: "POST",
        auth: true,
        body: JSON.stringify({
          prediction_id: predictionId,
          verdict: "correct",
          note: "Aprobado desde UI de Pendientes de Playbook",
        }),
      });

      if (selected?.report_id) {
        const ai = await api<any>(
          `/v1/ai-reports?report_id=${encodeURIComponent(selected.report_id)}`,
          { auth: true }
        );

        const latest: AIReport | null = Array.isArray(ai)
          ? ai?.[0] ?? null
          : ai ?? null;

        setAiDetail(latest);
      }

      setPendingPrediction(null);

      if (fallbackEventId) {
        await api(`/v1/playbook-fallbacks/${fallbackEventId}/resolve`, {
          method: "POST",
          auth: true,
        });
      }

      await load();
      window.dispatchEvent(new Event("playbook:pending-changed"));

      toast({
        title: "Sugerencia aprobada",
        description: "El AI report fue actualizado con el playbook confirmado.",
        status: "success",
        duration: 4000,
        isClosable: true,
      });
    } catch (e: any) {
      setError(e?.message ?? "No se pudo aprobar la sugerencia");
      toast({
        title: "Error al aprobar sugerencia",
        description: e?.message ?? "No se pudo aprobar la sugerencia",
        status: "error",
        duration: 5000,
        isClosable: true,
      });
    } finally {
      setApprovingSuggestion(false);
    }
  }

  async function loadPlaybookDetail(playbookId: string) {
    setSelectedPlaybookId(playbookId);
    setLoadingPlaybookDetail(true);

    try {
      const pb = await api<any>(`/v1/playbooks/${playbookId}`, { auth: true });
      setSelectedPlaybookDetail(pb);
    } catch (e: any) {
      setSelectedPlaybookDetail(null);
      toast({
        title: "Error al cargar playbook",
        description: e?.message ?? "No se pudo cargar el detalle del playbook",
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setLoadingPlaybookDetail(false);
    }
  }

  async function searchAlternativePlaybooks() {
    const q = playbookSearchQuery.trim();
    if (!q || q.length < 2) {
      setPlaybookSearchResults([]);
      return;
    }

    setSearchingPlaybooks(true);

    try {
      const rows = await api<PlaybookPreview[]>(
        `/v1/playbooks/search?q=${encodeURIComponent(q)}&limit=10`,
        { auth: true }
      );
      setPlaybookSearchResults(rows);
    } catch (e: any) {
      setPlaybookSearchResults([]);
      toast({
        title: "Error al buscar playbooks",
        description: e?.message ?? "No se pudo buscar playbooks",
        status: "error",
        duration: 4000,
        isClosable: true,
      });
    } finally {
      setSearchingPlaybooks(false);
    }
  }

  async function openDetail(r: PendingRow) {
    setShowAlternativeSearch(false);
    setPlaybookSearchQuery("");
    setPlaybookSearchResults([]);
    setSelected(r);
    setDetailError(null);
    setReportDetail(null);
    setAiDetail(null);
    setPendingPrediction(null);
    onOpen();

    if (r.row_type === "prediction_pending" && r.prediction_id) {
      setPendingPrediction({
        id: r.prediction_id,
        report_id: r.report_id,
        predicted_playbook_id: r.predicted_playbook_id ?? null,
        predicted_playbook_base_row: null,
        status: "pending_human_review",
        confidence_score: r.confidence_score ?? null,
        confidence_gap: r.confidence_gap ?? null,
        top_candidates_json: r.top_candidates_json ?? [],
        top_scores_json: [],
        retrieval_version: null,
        reranker_version: null,
        used_hyde: false,
        model_name: null,
        resolved_by_human: false,
        final_playbook_id: null,
        created_at: r.created_at,

        predicted_playbook_preview: r.predicted_playbook_preview ?? null,
        top_candidates_preview: r.top_candidates_preview ?? [],
      });
    }

    const initialSelectedId = r.predicted_playbook_id ?? null;
    setSelectedPlaybookId(initialSelectedId);
    setSelectedPlaybookDetail(null);

    if (initialSelectedId) {
      void loadPlaybookDetail(initialSelectedId);
    }

    setDetailLoading(true);

    try {
      let aiLoaded: AIReport | null = null;

      try {
        const ai = await api<any>(
          `/v1/ai-reports?report_id=${encodeURIComponent(r.report_id)}`,
          { auth: true }
        );
        aiLoaded = Array.isArray(ai) ? ai?.[0] ?? null : ai ?? null;
        setAiDetail(aiLoaded);
      } catch {
        setAiDetail(null);
      }

      let rep: StudentReport | null = null;

      try {
        rep = await api<StudentReport>(`/v1/reports/${r.report_id}`, {
          auth: true,
        });
      } catch {
        const fallbackStudentId = r.student_id || aiLoaded?.student_id || "";

        if (fallbackStudentId) {
          const list = await api<StudentReport[]>(
            `/v1/reports?student_id=${encodeURIComponent(fallbackStudentId)}`,
            { auth: true }
          );
          rep = list.find((x) => x.id === r.report_id) ?? null;
        }
      }

      setReportDetail(rep);

      if (r.row_type !== "prediction_pending") {
        setPredictionLoading(true);

        try {
          const pending = await api<AIPrediction[]>(
            `/v1/ai-feedback/pending?limit=200`,
            { auth: true }
          );

          const match =
            pending
              .filter((x) => x.report_id === r.report_id)
              .sort(
                (a, b) =>
                  new Date(b.created_at).getTime() -
                  new Date(a.created_at).getTime()
              )[0] ?? null;
          if (match?.predicted_playbook_id) {
            setSelectedPlaybookId(match.predicted_playbook_id);
            void loadPlaybookDetail(match.predicted_playbook_id);
          }

          setPendingPrediction(match);
        } catch {
          setPendingPrediction(null);
        } finally {
          setPredictionLoading(false);
        }
      } else {
        setPredictionLoading(false);
      }
    } catch (e: any) {
      setDetailError(e?.message ?? "No se pudo cargar el detalle");
    } finally {
      setDetailLoading(false);
    }
  }

  async function load() {
    setLoading(true);
    setError(null);

    try {
      const fallbackRows = await api<PlaybookFallbackEvent[]>(
        `/v1/playbook-fallbacks?status_filter=${encodeURIComponent(
          statusFilter
        )}&limit=200`,
        { auth: true }
      );

      const fallbackMapped: PendingRow[] = fallbackRows.map((row) => ({
        row_type: "fallback",
        id: row.id,
        report_id: row.report_id,
        student_id: row.student_id,
        school_id: row.school_id,
        ai_report_id: row.ai_report_id,
        reason: row.reason,
        query_text: row.query_text,
        model_output_summary: row.model_output_summary,
        topic_nucleo: row.topic_nucleo,
        signals_detected: row.signals_detected,
        resolved_at: row.resolved_at,
        created_at: row.created_at,
      }));

      let predictionMapped: PendingRow[] = [];

      if (statusFilter !== "resolved") {
        const predictions = await api<AIPrediction[]>(
          `/v1/ai-feedback/pending?limit=200`,
          { auth: true }
        );

        const fallbackReportIds = new Set(fallbackRows.map((x) => x.report_id));

        predictionMapped = predictions
          .filter((p) => !fallbackReportIds.has(p.report_id))
          .map((p) => ({
            row_type: "prediction_pending" as const,
            id: `prediction-${p.id}`,
            prediction_id: p.id,
            report_id: p.report_id,
            student_id: "",
            school_id: "",
            ai_report_id: null,
            reason: "pending_human_review",
            query_text: null,
            model_output_summary:
              "Este caso requiere validación humana antes de compartir una estrategia final.",
            topic_nucleo: null,
            signals_detected: [],
            resolved_at: null,
            created_at: p.created_at,
            predicted_playbook_id: p.predicted_playbook_id,
            confidence_score: p.confidence_score,
            confidence_gap: p.confidence_gap,
            top_candidates_json: p.top_candidates_json,
            predicted_playbook_preview: p.predicted_playbook_preview ?? null,
            top_candidates_preview: p.top_candidates_preview ?? [],
          }));
      }

      const combined = [...fallbackMapped, ...predictionMapped].sort(
        (a, b) =>
          new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      );

      setRows(combined);
    } catch (e: any) {
      setError(e?.message ?? "No se pudo cargar Pendientes de Playbook");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useEffect(() => {
    loadLatestSync();
  }, []);

  useEffect(() => {
    if (!isSyncing) return;

    const intervalId = window.setInterval(async () => {
      const current = await loadLatestSync();

      if (!current) {
        window.clearInterval(intervalId);
        setIsSyncing(false);
        return;
      }

      const stillActive =
        current.status === "queued" || current.status === "started";

      if (!stillActive) {
        window.clearInterval(intervalId);
        setIsSyncing(false);

        if (current.status === "finished") {
          toast({
            title: "Playbooks reprocesados",
            description: "La sincronización terminó correctamente.",
            status: "success",
            duration: 4000,
            isClosable: true,
          });
        }

        if (current.status === "failed") {
          toast({
            title: "La sincronización falló",
            description:
              current.error_message || "Ocurrió un error en el proceso",
            status: "error",
            duration: 5000,
            isClosable: true,
          });
        }
      }
    }, 2500);

    return () => window.clearInterval(intervalId);
  }, [isSyncing, toast]);

  const pendingCount = useMemo(
    () => rows.filter((r) => !r.resolved_at).length,
    [rows]
  );

  const selectedIsResolved = !!selected?.resolved_at;
  const detailStudentId = selected?.student_id || reportDetail?.student_id || "";

  return (
    <Box p={{ base: 6, lg: 8 }} minH="100vh" bg="#f8f9fa">
      <HStack justify="space-between" align="flex-start" mb={8} wrap="wrap" gap={4}>
        <Box>
          <Heading
            as="h1"
            fontSize={{ base: "3xl", md: "4xl" }}
            fontWeight="extrabold"
            color="#191c1d"
            fontFamily="'Plus Jakarta Sans', sans-serif"
            letterSpacing="tight"
            mb={2}
          >
            Pendientes de Playbook
          </Heading>
          <Text color="#434654" fontFamily="'Manrope', sans-serif">
            Casos donde no se encontró estrategia JCJ o donde una sugerencia JCJ
            requiere validación humana.
          </Text>
        </Box>

        <HStack spacing={4} align="center" wrap="wrap">
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            w="220px"
            bg="#ffffff"
            border="1px solid rgba(195, 197, 215, 0.15)"
            borderRadius="xl"
            _focus={{ borderColor: "rgba(0, 53, 151, 0.3)", boxShadow: "0 0 0 1px rgba(0, 53, 151, 0.3)" }}
            fontFamily="'Manrope', sans-serif"
            size="md"
          >
            <option value="pending">Pendientes</option>
            <option value="resolved">Resueltos</option>
            <option value="all">Todos</option>
          </Select>

          <Button
            onClick={load}
            variant="outline"
            isLoading={loading}
            borderRadius="full"
            color="#434654"
            borderColor="rgba(195, 197, 215, 0.4)"
            bg="#ffffff"
            _hover={{ bg: "#f3f4f5" }}
            fontFamily="'Manrope', sans-serif"
          >
            Recargar
          </Button>

          <Button
            onClick={handleReprocessPlaybooks}
            isLoading={isSyncing}
            loadingText="Procesando..."
            bg="#003597"
            color="#ffffff"
            borderRadius="full"
            _hover={{ bg: "#0049ca", transform: "translateY(-1px)", boxShadow: "0px 8px 16px rgba(0, 53, 151, 0.2)" }}
            transition="all 0.2s"
            fontFamily="'Manrope', sans-serif"
            fontWeight="bold"
          >
            Reprocesar playbooks
          </Button>

          {isSyncing && <Spinner size="sm" color="#003597" />}

          {syncStatus && (
            <Badge
              bg={syncStatus === "finished" ? "#e8edff" : syncStatus === "failed" ? "#fce8e8" : "#f3f4f5"}
              color={syncStatus === "finished" ? "#003597" : syncStatus === "failed" ? "#c52828" : "#434654"}
              borderRadius="full"
              px={4}
              py={1.5}
              textTransform="none"
              fontSize="sm"
              fontFamily="'Manrope', sans-serif"
            >
              {syncStatus}
            </Badge>
          )}
        </HStack>
      </HStack>

      <Box p={6} borderRadius="2rem" bg="#ffffff" mb={8} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)">
        <VStack align="start" spacing={3}>
          <Text fontWeight="bold" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">Última sincronización</Text>

          {syncError ? (
            <Alert status="error" borderRadius="xl" bg="#fce8e8" color="#c52828">
              <AlertIcon color="#c52828" />
              <Text fontFamily="'Manrope', sans-serif">{syncError}</Text>
            </Alert>
          ) : !latestSync ? (
            <HStack>
              <Text fontFamily="'Manrope', sans-serif" color="#434654">Estado:</Text>
              <Badge bg="#f3f4f5" color="#737686" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">N/A</Badge>
            </HStack>
          ) : (
            <Stack spacing={2}>
              <HStack>
                <Text fontWeight="medium" fontFamily="'Manrope', sans-serif" color="#191c1d">Estado:</Text>
                <Badge
                  bg={latestSync.status === "finished" ? "#e8edff" : latestSync.status === "failed" ? "#fce8e8" : "#f3f4f5"}
                  color={latestSync.status === "finished" ? "#003597" : latestSync.status === "failed" ? "#c52828" : "#434654"}
                  borderRadius="full"
                  px={3}
                  py={1}
                  textTransform="none"
                  fontFamily="'Manrope', sans-serif"
                >
                  {latestSync.status}
                </Badge>
              </HStack>

              <Text fontSize="sm" color="#434654" fontFamily="'Manrope', sans-serif">
                Fecha:{" "}
                {latestSync.finished_at
                  ? new Date(latestSync.finished_at).toLocaleString()
                  : latestSync.created_at
                    ? new Date(latestSync.created_at).toLocaleString()
                    : "-"}
              </Text>

              <Text fontSize="sm" color="#434654" fontFamily="'Manrope', sans-serif">
                Playbooks cargados:{" "}
                <Text as="span" fontWeight="bold">
                  {typeof (latestSync.result as any)?.loaded_count === "number"
                    ? (latestSync.result as any).loaded_count
                    : "-"}
                </Text>
              </Text>

              <Text fontSize="sm" color="#434654" fontFamily="'Manrope', sans-serif">
                Colección:{" "}
                <Text as="span" fontWeight="bold">
                  {(latestSync.result as any)?.chroma_collection ?? "-"}
                </Text>
              </Text>

              {latestSync.error_message ? (
                 <Alert status="error" borderRadius="xl" bg="#fce8e8" color="#c52828" mt={2} p={3}>
                  <AlertIcon color="#c52828" boxSize={4} />
                  <Text fontSize="sm" fontFamily="'Manrope', sans-serif">
                    {latestSync.error_message}
                  </Text>
                 </Alert>
              ) : null}
            </Stack>
          )}
        </VStack>
      </Box>

      {error && (
        <Alert status="error" mb={6} borderRadius="xl" bg="#fce8e8" color="#c52828">
          <AlertIcon color="#c52828" />
          <Text fontFamily="'Manrope', sans-serif">{error}</Text>
        </Alert>
      )}

      <Box bg="#ffffff" borderRadius="2rem" p={6} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)">
        <HStack justify="space-between" align="center" mb={6}>
            <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">Lista</Heading>
            <Badge bg="#e8edff" color="#003597" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
              {pendingCount} PENDIENTES
            </Badge>
        </HStack>

        <Box>
          {loading ? (
            <HStack py={6} justify="center">
              <Spinner color="#003597" />
              <Text fontFamily="'Manrope', sans-serif" color="#434654">Cargando pendientes…</Text>
            </HStack>
          ) : rows.length === 0 ? (
            <Text color="#737686" fontFamily="'Manrope', sans-serif" py={4}>No hay eventos para este filtro.</Text>
          ) : (
            <Box overflowX="auto">
              <Table variant="unstyled" sx={{
                "th": { color: "#737686", fontFamily: "'Manrope', sans-serif", fontSize: "xs", textTransform: "uppercase", letterSpacing: "wider", pb: 4, pt: 2, px: 4 },
                "td": { py: 4, px: 4, borderColor: "rgba(195, 197, 215, 0.15)", borderBottomWidth: "1px" },
                "tr:last-child td": { borderBottomWidth: "0" }
              }}>
                <Thead>
                  <Tr borderBottom="1px solid rgba(195, 197, 215, 0.15)">
                    <Th>Created</Th>
                    <Th>Reason</Th>
                    <Th>Query</Th>
                    <Th>Summary</Th>
                    <Th>Status</Th>
                    <Th>Actions</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {rows.map((row) => {
                    const isResolved = !!row.resolved_at;

                    return (
                      <Tr key={row.id}>
                        <Td whiteSpace="nowrap" fontFamily="'Manrope', sans-serif" fontSize="sm" color="#191c1d">
                          {new Date(row.created_at).toLocaleString()}
                        </Td>

                        <Td>
                          <VStack align="start" spacing={2}>
                            <Badge bg="#f4e8ff" color="#6b0097" borderRadius="full" px={3} py={0.5} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="xs">
                              {formatReason(row.reason)}
                            </Badge>
                            <Badge
                              bg={row.row_type === "prediction_pending" ? "#fff0e0" : "#e8edff"}
                              color={row.row_type === "prediction_pending" ? "#e06c00" : "#003597"}
                              borderRadius="full"
                              px={3}
                              py={0.5}
                              fontFamily="'Manrope', sans-serif"
                              textTransform="none"
                              fontSize="xs"
                            >
                              {row.row_type === "prediction_pending"
                                ? "Revisión humana"
                                : "Fallback"}
                            </Badge>
                          </VStack>
                        </Td>

                        <Td maxW="300px">
                          {row.query_text ? (
                            <Text whiteSpace="normal" fontFamily="'Manrope', sans-serif" fontSize="sm" color="#434654">
                              {truncate(row.query_text, 100)}
                            </Text>
                          ) : row.predicted_playbook_id ? (
                            <Text whiteSpace="normal" fontFamily="'Manrope', sans-serif" fontSize="sm" color="#434654">
                              Suggested playbook:{" "}
                              <Text as="span" fontWeight="bold">{truncate(row.predicted_playbook_id, 80)}</Text>
                            </Text>
                          ) : (
                            <Text whiteSpace="normal" color="#737686">-</Text>
                          )}
                        </Td>

                        <Td maxW="300px">
                          <Text whiteSpace="normal" fontFamily="'Manrope', sans-serif" fontSize="sm" color="#434654">
                            {truncate(row.model_output_summary, 100)}
                          </Text>
                        </Td>

                        <Td>
                          {isResolved ? (
                            <Badge bg="#e6f4ea" color="#137333" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">Resuelto</Badge>
                          ) : (
                            <Badge bg="#fff0e0" color="#e06c00" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">Pendiente</Badge>
                          )}
                        </Td>

                        <Td>
                          <VStack align="stretch" spacing={2} maxW="150px">
                            <Button
                              size="sm"
                              variant="outline"
                              borderRadius="full"
                              borderColor="rgba(195, 197, 215, 0.4)"
                              color="#434654"
                              _hover={{ bg: "#f3f4f5" }}
                              fontFamily="'Manrope', sans-serif"
                              onClick={() => openDetail(row)}
                            >
                              Ver detalle
                            </Button>

                            {!isResolved && row.row_type === "fallback" && (
                              <Button
                                size="sm"
                                bg="#003597"
                                color="#ffffff"
                                borderRadius="full"
                                _hover={{ bg: "#0049ca", transform: "translateY(-1px)", boxShadow: "0px 4px 8px rgba(0, 53, 151, 0.2)" }}
                                onClick={() => resolveEvent(row.id)}
                                isLoading={!!resolvingById[row.id]}
                                fontFamily="'Manrope', sans-serif"
                              >
                                Marcar resuelto
                              </Button>
                            )}
                          </VStack>
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

      <Modal isOpen={isOpen} onClose={closeDetail} size="6xl" scrollBehavior="inside">
        <ModalOverlay bg="rgba(25, 28, 29, 0.4)" backdropFilter="blur(4px)" />
        <ModalContent borderRadius="2rem" bg="#ffffff" boxShadow="0px 24px 48px rgba(25, 28, 29, 0.08)" overflow="hidden" pt={4}>
          <ModalHeader pt={6} px={8} pb={4} fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">Detalle del pendiente</ModalHeader>
          <ModalCloseButton mt={6} mr={6} borderRadius="full" />

          <ModalBody px={8}>
            {detailError && (
              <Alert status="error" mb={6} borderRadius="xl" bg="#fce8e8" color="#c52828">
                <AlertIcon color="#c52828" />
                <Text fontFamily="'Manrope', sans-serif">{detailError}</Text>
              </Alert>
            )}

            {!selected ? (
              <Text color="#737686" fontFamily="'Manrope', sans-serif">Sin selección.</Text>
            ) : detailLoading ? (
              <HStack>
                <Spinner size="sm" color="#003597" />
                <Text fontFamily="'Manrope', sans-serif" color="#434654">Cargando detalle…</Text>
              </HStack>
            ) : (
              <VStack align="stretch" spacing={6}>
                <HStack justify="space-between" align="start" p={6} bg="#f8f9fa" borderRadius="2rem" border="1px solid rgba(195, 197, 215, 0.3)">
                  <Box>
                    <Text fontSize="sm" color="#737686" fontFamily="'Manrope', sans-serif">
                      Estado
                    </Text>
                    {selectedIsResolved ? (
                      <Badge bg="#e6f4ea" color="#137333" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none" mt={1}>Resuelto</Badge>
                    ) : (
                      <Badge bg="#fff0e0" color="#e06c00" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none" mt={1}>Pendiente</Badge>
                    )}
                    <Text fontSize="sm" color="#434654" mt={3} fontFamily="'Manrope', sans-serif">
                      Reason: <Text as="span" fontWeight="bold">{selected.reason || "n/a"}</Text>
                    </Text>
                    <Text fontSize="sm" color="#434654" mt={1} fontFamily="'Manrope', sans-serif">
                      Tipo:{" "}
                      <Text as="span" fontWeight="bold">
                        {selected.row_type === "prediction_pending"
                          ? "Revisión humana"
                          : "Fallback"}
                      </Text>
                    </Text>
                  </Box>

                  <HStack spacing={2} flexWrap="wrap" justify="flex-end">
                    <Badge variant="subtle" bg="#e8edff" color="#003597" borderRadius="full" px={3} py={1.5} fontFamily="'Manrope', sans-serif" textTransform="none">
                      Topic: {selected.topic_nucleo ?? "-"}
                    </Badge>
                    <Badge variant="subtle" bg="#f3f4f5" color="#434654" borderRadius="full" px={3} py={1.5} fontFamily="'Manrope', sans-serif" textTransform="none">
                      Signals: {formatSignals(selected.signals_detected)}
                    </Badge>
                  </HStack>
                </HStack>

                <Divider borderColor="rgba(195, 197, 215, 0.15)" />

                {selected.query_text ? (
                  <Box>
                    <Text fontWeight="bold" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={2}>
                      Query (completo)
                    </Text>
                    <Box border="1px solid rgba(195, 197, 215, 0.3)" borderRadius="xl" p={4} bg="#ffffff">
                      <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                        {selected.query_text}
                      </Text>
                    </Box>
                  </Box>
                ) : null}

                <Box>
                  <Text fontWeight="bold" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={2}>
                    Summary del modelo (completo)
                  </Text>
                  <Box border="1px solid rgba(195, 197, 215, 0.3)" borderRadius="xl" p={4} bg="#ffffff">
                    <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                      {selected.model_output_summary ?? "-"}
                    </Text>
                  </Box>
                </Box>

                <Divider />

                <Box>
                  <Heading size="sm" mb={4} fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
                    Reporte del maestro (StudentReport)
                  </Heading>

                  {!reportDetail ? (
                    <Alert status="warning" borderRadius="xl" bg="#fff0e0" color="#e06c00">
                      <AlertIcon color="#e06c00" />
                      <Text fontSize="sm" fontFamily="'Manrope', sans-serif">
                        No se pudo cargar el reporte base.
                      </Text>
                    </Alert>
                  ) : (
                    <Stack spacing={4}>
                      <Box>
                        <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">Señales observables</Text>
                        <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                          {safeText(reportDetail.signals_observed) || "-"}
                        </Text>
                      </Box>

                      <Box>
                        <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">Notas</Text>
                        <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                          {reportDetail.notes ?? "-"}
                        </Text>
                      </Box>
                    </Stack>
                  )}
                </Box>

                <Divider />

                <Box>
                  <Heading size="sm" mb={4} fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
                    Apoyo generado por IA
                  </Heading>

                  {!aiDetail ? (
                    <Alert status="warning" borderRadius="xl" bg="#fff0e0" color="#e06c00">
                      <AlertIcon color="#e06c00" />
                      <Text fontSize="sm" fontFamily="'Manrope', sans-serif">
                        No se encontró AI report para este reporte.
                      </Text>
                    </Alert>
                  ) : (
                    <Stack spacing={6}>
                      <HStack justify="space-between" align="start" flexWrap="wrap">
                        <Box>
                          <Text fontSize="sm" color="#737686" fontFamily="'Manrope', sans-serif">
                            Modelo
                          </Text>
                          <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">{aiDetail.model_name}</Text>
                        </Box>

                        <Box textAlign="right">
                          <Text fontSize="sm" color="#737686" fontFamily="'Manrope', sans-serif">
                            Creado
                          </Text>
                          <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                            {new Date(aiDetail.created_at).toLocaleString()}
                          </Text>
                        </Box>
                      </HStack>

                      <Box>
                        <Text fontWeight="bold" mb={2} fontFamily="'Manrope', sans-serif" color="#191c1d">
                          Resumen (familia)
                        </Text>
                        <Box border="1px solid rgba(195, 197, 215, 0.3)" borderRadius="xl" p={4} bg="#f3f4f5">
                          <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                            {aiDetail.parent_version?.summary ?? "-"}
                          </Text>
                        </Box>
                      </Box>

                      {(aiDetail.parent_version?.signals_detected ?? []).length > 0 ? (
                        <Box>
                          <Text fontWeight="bold" mb={2} fontFamily="'Manrope', sans-serif" color="#191c1d">
                            Señales detectadas (familia)
                          </Text>
                          <Box border="1px solid rgba(195, 197, 215, 0.3)" borderRadius="xl" p={4} bg="#f3f4f5">
                            <Stack spacing={2}>
                              {(aiDetail.parent_version?.signals_detected ?? []).map((s, idx) => (
                                <Text key={idx} fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                                  • {s}
                                </Text>
                              ))}
                            </Stack>
                          </Box>
                        </Box>
                      ) : null}

                      {(aiDetail.parent_version?.microintervenciones ?? []).length > 0 ? (
                        <Box>
                          <Text fontWeight="bold" mb={3} fontFamily="'Manrope', sans-serif" color="#191c1d">
                            Microintervenciones (familia)
                          </Text>

                          <Stack spacing={4}>
                            {(aiDetail.parent_version?.microintervenciones ?? []).map((mi, idx) => (
                              <Box key={idx} bg="#f3f4f5" borderRadius="2rem" p={6}>
                                <HStack justify="space-between" align="start" flexWrap="wrap">
                                  <Box>
                                    <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      {mi.topic_nucleo} · {mi.subhabilidad}
                                    </Text>
                                    <Text fontSize="sm" color="#434654" mt={1} fontFamily="'Manrope', sans-serif">
                                      Señal observable: {mi.senal_observable}
                                    </Text>
                                  </Box>

                                  <VStack align="end" spacing={2}>
                                    <Badge variant="subtle" bg="#f4e8ff" color="#6b0097" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                                      Frecuencia: {mi.frecuencia}
                                    </Badge>
                                    <Badge variant="subtle" bg="#e8f5e9" color="#2e7d32" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                                      Duración: {mi.duracion}
                                    </Badge>
                                  </VStack>
                                </HStack>

                                <Divider borderColor="rgba(195, 197, 215, 0.3)" my={4} />

                                <Stack spacing={4}>
                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      Hipótesis funcional
                                    </Text>
                                    <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                                      {mi.hipotesis_funcional}
                                    </Text>
                                  </Box>

                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      Microobjetivo
                                    </Text>
                                    <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                                      {mi.microobjetivo}
                                    </Text>
                                  </Box>

                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      Estrategias paso a paso
                                    </Text>
                                    <Stack spacing={1} mt={2}>
                                      {(mi.estrategias_paso_a_paso ?? []).map((st, i) => (
                                        <Text key={i} fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                                          • {st}
                                        </Text>
                                      ))}
                                    </Stack>
                                  </Box>

                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      Indicador de avance
                                    </Text>
                                    <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                                      {mi.indicador_de_avance}
                                    </Text>
                                  </Box>

                                  <Box>
                                    <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                                      Escalamiento
                                    </Text>
                                    <Text fontSize="sm" whiteSpace="pre-wrap" fontFamily="'Manrope', sans-serif" color="#434654">
                                      {mi.escalamiento}
                                    </Text>
                                  </Box>
                                </Stack>
                              </Box>
                            ))}
                          </Stack>
                        </Box>
                      ) : null}

                      {aiDetail.guardrails_notes ? (
                        <Alert status="warning" borderRadius="xl" bg="#fff0e0" color="#e06c00">
                          <AlertIcon color="#e06c00" />
                          <Text fontSize="sm" fontFamily="'Manrope', sans-serif">{aiDetail.guardrails_notes}</Text>
                        </Alert>
                      ) : null}
                    </Stack>
                  )}
                </Box>

                <Divider borderColor="rgba(195, 197, 215, 0.15)" />

                <Box>
                  <Heading size="sm" mb={4} fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
                    Revisión humana de sugerencia JCJ
                  </Heading>

                  {predictionLoading ? (
                    <HStack>
                      <Spinner size="sm" color="#003597" />
                      <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">Buscando sugerencia pendiente…</Text>
                    </HStack>
                  ) : !pendingPrediction ? (
                    <Alert status="info" borderRadius="xl" bg="#e8edff" color="#003597">
                      <AlertIcon color="#003597" />
                      <Text fontSize="sm" fontFamily="'Manrope', sans-serif">
                        No hay una sugerencia de playbook pendiente para este
                        reporte.
                      </Text>
                    </Alert>
                  ) : (
                    <Stack spacing={4}>
                      <Alert status="warning" borderRadius="xl" bg="#fff0e0" color="#e06c00">
                        <AlertIcon color="#e06c00" />
                        <Box>
                          <Text fontSize="sm" fontWeight="bold" fontFamily="'Manrope', sans-serif">
                            Este reporte tiene una sugerencia JCJ pendiente de
                            validación humana.
                          </Text>
                          <Text fontSize="sm" mt={1} fontFamily="'Manrope', sans-serif">
                            Si esta sugerencia es correcta, puedes aprobarla y
                            el AI report se actualizará.
                          </Text>
                        </Box>
                      </Alert>

                      <HStack justify="space-between" align="start" flexWrap="wrap">
                        <Box>
                          <Text fontSize="sm" color="#737686" fontFamily="'Manrope', sans-serif">
                            Sugerencia principal
                          </Text>
                        </Box>

                        <VStack align="end" spacing={2}>
                          <Badge bg="#fff0e0" color="#e06c00" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                            Score: {pendingPrediction.confidence_score ?? "-"}
                          </Badge>
                          <Badge variant="subtle" bg="#f3f4f5" color="#434654" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                            Gap: {pendingPrediction.confidence_gap ?? "-"}
                          </Badge>
                        </VStack>
                      </HStack>

                      {pendingPrediction.predicted_playbook_preview ? (
                        <Box>
                          {renderPlaybookPreview(pendingPrediction.predicted_playbook_preview)}
                        </Box>
                      ) : (
                        <Box>
                          <Text fontSize="sm" color="#737686" mb={1} fontFamily="'Manrope', sans-serif">
                            Predicted playbook ID
                          </Text>
                          <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">
                            {pendingPrediction.predicted_playbook_id ?? "-"}
                          </Code>
                        </Box>
                      )}

                      {!!pendingPrediction.top_candidates_preview?.length && (
                        <Box mt={4}>
                          <Text fontWeight="bold" mb={3} fontFamily="'Manrope', sans-serif" color="#191c1d">
                            Candidatos sugeridos
                          </Text>
                          <Stack spacing={3}>
                            {pendingPrediction.top_candidates_preview.map((pb, idx) => (
                              <Box key={`${pb.id}-${idx}`}>
                                <Text fontSize="sm" fontWeight="bold" mb={2} color="#003597" fontFamily="'Manrope', sans-serif">
                                  Opción {idx + 1}
                                </Text>
                                {renderPlaybookPreview(pb)}
                              </Box>
                            ))}
                          </Stack>
                        </Box>
                      )}

                      {!pendingPrediction.top_candidates_preview?.length &&
                        !!pendingPrediction.top_candidates_json?.length ? (
                        <Box mt={4}>
                          <Text fontWeight="bold" mb={2} fontFamily="'Manrope', sans-serif" color="#191c1d">
                            Top candidates
                          </Text>
                          <Stack spacing={2}>
                            {pendingPrediction.top_candidates_json.map((id, idx) => (
                              <Text key={`${id}-${idx}`} fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                                {idx + 1}. <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{id}</Code>
                              </Text>
                            ))}
                          </Stack>
                        </Box>
                      ) : null}
                      {loadingPlaybookDetail ? (
                        <HStack mt={4}>
                          <Spinner size="sm" color="#003597" />
                          <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">Cargando detalle del playbook…</Text>
                        </HStack>
                      ) : selectedPlaybookDetail ? (
                        <Box mt={6} bg="#ffffff" borderRadius="2rem" border="1px solid rgba(195, 197, 215, 0.3)" p={6}>
                          <Heading size="sm" mb={4} fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
                            Detalle del playbook seleccionado
                          </Heading>

                          <Box>
                            <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d">
                              {selectedPlaybookDetail.topic_nucleo || "-"}
                            </Text>

                            <Text mt={2} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Subhabilidad:</Text> {selectedPlaybookDetail.subhabilidad || "-"}
                            </Text>

                            <Text mt={2} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Señal observable:</Text> {selectedPlaybookDetail.senal_observable || "-"}
                            </Text>

                            <Text mt={3} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Hipótesis funcional:</Text><br />
                              {selectedPlaybookDetail.hipotesis_funcional || "-"}
                            </Text>

                            <Text mt={3} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Microobjetivo:</Text><br />
                              {selectedPlaybookDetail.microobjetivo || "-"}
                            </Text>

                            <Box mt={4}>
                              <Text as="span" fontWeight="bold" color="#191c1d" fontSize="sm" fontFamily="'Manrope', sans-serif">Estrategias paso a paso:</Text>
                              <Stack mt={2} spacing={1}>
                                {(selectedPlaybookDetail.estrategias_paso_a_paso || []).map(
                                  (s: string, i: number) => (
                                    <Text key={i} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">• {s}</Text>
                                  )
                                )}
                              </Stack>
                            </Box>

                            <HStack mt={4} spacing={2} wrap="wrap">
                              <Badge variant="subtle" bg="#f4e8ff" color="#6b0097" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                                Frecuencia: {selectedPlaybookDetail.frecuencia || "-"}
                              </Badge>
                              <Badge variant="subtle" bg="#e8f5e9" color="#2e7d32" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                                Duración: {selectedPlaybookDetail.duracion || "-"}
                              </Badge>
                            </HStack>

                            <Text mt={4} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Indicador de avance:</Text><br />
                              {selectedPlaybookDetail.indicador_de_avance || "-"}
                            </Text>

                            <Text mt={3} fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">
                              <Text as="span" fontWeight="bold" color="#191c1d">Escalamiento:</Text><br />
                              {selectedPlaybookDetail.escalamiento || "-"}
                            </Text>
                          </Box>
                        </Box>
                      ) : null}

                      <Box mt={2}>
                        <Button
                          variant="outline"
                          borderRadius="full"
                          color="#434654"
                          borderColor="rgba(195, 197, 215, 0.4)"
                          bg="#ffffff"
                          _hover={{ bg: "#f3f4f5" }}
                          fontFamily="'Manrope', sans-serif"
                          size="md"
                          onClick={() => setShowAlternativeSearch((v) => !v)}
                        >
                          No es ninguna de estas opciones
                        </Button>
                      </Box>

                      {showAlternativeSearch ? (
                        <Box mt={4} p={6} bg="#f8f9fa" borderRadius="2rem" border="1px solid rgba(195, 197, 215, 0.3)">
                          <Text fontWeight="bold" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={4}>
                            Buscar otro playbook
                          </Text>

                          <HStack align="stretch" spacing={3} wrap="wrap">
                            <Input
                              placeholder="Busca por topic, subhabilidad o señal observable"
                              value={playbookSearchQuery}
                              onChange={(e) => setPlaybookSearchQuery(e.target.value)}
                              bg="#ffffff"
                              border="1px solid rgba(195, 197, 215, 0.3)"
                              borderRadius="xl"
                              _focus={{ borderColor: "rgba(0, 53, 151, 0.3)", boxShadow: "0 0 0 1px rgba(0, 53, 151, 0.3)" }}
                              fontFamily="'Manrope', sans-serif"
                            />
                            <Button
                              onClick={searchAlternativePlaybooks}
                              isLoading={searchingPlaybooks}
                              bg="#003597"
                              color="#ffffff"
                              borderRadius="full"
                              _hover={{ bg: "#0049ca", transform: "translateY(-1px)", boxShadow: "0px 4px 8px rgba(0, 53, 151, 0.2)" }}
                              fontFamily="'Manrope', sans-serif"
                            >
                              Buscar
                            </Button>
                          </HStack>

                          {playbookSearchResults.length > 0 ? (
                            <Stack spacing={3} mt={6}>
                              {playbookSearchResults.map((pb) => (
                                <Box key={pb.id}>{renderPlaybookPreview(pb)}</Box>
                              ))}
                            </Stack>
                          ) : playbookSearchQuery.trim().length >= 2 && !searchingPlaybooks ? (
                            <Text fontSize="sm" color="#737686" mt={4} fontFamily="'Manrope', sans-serif">
                              No se encontraron resultados.
                            </Text>
                          ) : null}
                        </Box>
                      ) : null}

                      <HStack mt={4}>
                        <Button
                          bg="#003597"
                          color="#ffffff"
                          borderRadius="full"
                          _hover={{ bg: "#0049ca", transform: "translateY(-1px)", boxShadow: "0px 4px 8px rgba(0, 53, 151, 0.2)" }}
                          fontFamily="'Manrope', sans-serif"
                          onClick={() =>
                            approvePredictionSuggestion(
                              pendingPrediction.id,
                              selected.row_type === "fallback"
                                ? selected.id
                                : undefined
                            )
                          }
                          isLoading={approvingSuggestion}
                        >
                          Aprobar sugerencia
                        </Button>
                        {selectedPlaybookId &&
                          selectedPlaybookId !== pendingPrediction.predicted_playbook_id ? (
                          <Button
                            bg="#6b0097"
                            color="#ffffff"
                            borderRadius="full"
                            _hover={{ bg: "#8e00c7", transform: "translateY(-1px)", boxShadow: "0px 4px 8px rgba(107, 0, 151, 0.2)" }}
                            fontFamily="'Manrope', sans-serif"
                            onClick={async () => {
                              setApprovingSuggestion(true);
                              setError(null);

                              try {
                                await api("/v1/ai-feedback", {
                                  method: "POST",
                                  auth: true,
                                  body: JSON.stringify({
                                    prediction_id: pendingPrediction.id,
                                    verdict: "incorrect",
                                    corrected_playbook_id: selectedPlaybookId,
                                    note: "Corregido desde UI de Pendientes de Playbook",
                                  }),
                                });

                                if (selected?.report_id) {
                                  const ai = await api<any>(
                                    `/v1/ai-reports?report_id=${encodeURIComponent(selected.report_id)}`,
                                    { auth: true }
                                  );

                                  const latest: AIReport | null = Array.isArray(ai)
                                    ? ai?.[0] ?? null
                                    : ai ?? null;

                                  setAiDetail(latest);
                                }

                                setPendingPrediction(null);

                                if (selected?.row_type === "fallback") {
                                  await api(`/v1/playbook-fallbacks/${selected.id}/resolve`, {
                                    method: "POST",
                                    auth: true,
                                  });
                                }

                                await load();
                                window.dispatchEvent(new Event("playbook:pending-changed"));

                                toast({
                                  title: "Playbook corregido",
                                  description: "El AI report fue actualizado con el playbook seleccionado.",
                                  status: "success",
                                  duration: 4000,
                                  isClosable: true,
                                });
                              } catch (e: any) {
                                setError(e?.message ?? "No se pudo corregir el playbook");
                                toast({
                                  title: "Error al corregir playbook",
                                  description: e?.message ?? "No se pudo corregir el playbook",
                                  status: "error",
                                  duration: 5000,
                                  isClosable: true,
                                });
                              } finally {
                                setApprovingSuggestion(false);
                              }
                            }}
                            isLoading={approvingSuggestion}
                          >
                            Usar playbook seleccionado
                          </Button>
                        ) : null}
                      </HStack>
                    </Stack>
                  )}
                </Box>

                <Divider borderColor="rgba(195, 197, 215, 0.15)" />

                <Box mb={4}>
                  <Text fontWeight="bold" mb={3} fontFamily="'Manrope', sans-serif" color="#191c1d">
                    IDs (debug)
                  </Text>
                  <VStack align="stretch" spacing={2}>
                    <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                      row_type: <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{selected.row_type}</Code>
                    </Text>
                    <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                      report_id: <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{selected.report_id}</Code>
                    </Text>
                    <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                      student_id:{" "}
                      <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{detailStudentId || "-"}</Code>
                    </Text>
                    <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                      ai_report_id:{" "}
                      <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{selected.ai_report_id ?? "-"}</Code>
                    </Text>
                    <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                      school_id:{" "}
                      <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">
                        {selected.school_id || reportDetail?.school_id || "-"}
                      </Code>
                    </Text>
                    {selected.prediction_id ? (
                      <Text fontSize="sm" fontFamily="'Manrope', sans-serif" color="#434654">
                        prediction_id:{" "}
                        <Code fontSize="xs" bg="#f3f4f5" color="#191c1d" p={1} borderRadius="md">{selected.prediction_id}</Code>
                      </Text>
                    ) : null}
                  </VStack>
                </Box>
              </VStack>
            )}
          </ModalBody>

          <ModalFooter borderTop="1px solid rgba(195, 197, 215, 0.15)" bg="#f8f9fa" mt={4} py={6} px={8} borderRadius="0 0 2rem 2rem">
            <HStack spacing={4} wrap="wrap">
              {detailStudentId && selected?.report_id ? (
                <Button
                  variant="outline"
                  borderRadius="full"
                  color="#434654"
                  borderColor="rgba(195, 197, 215, 0.4)"
                  bg="#ffffff"
                  _hover={{ bg: "#f3f4f5" }}
                  fontFamily="'Manrope', sans-serif"
                  onClick={() => {
                    navigate(
                      `/students/${detailStudentId}/reports?report_id=${encodeURIComponent(
                        selected.report_id
                      )}`
                    );
                    closeDetail();
                  }}
                >
                  Ir al reporte
                </Button>
              ) : null}

              {selected &&
                selected.row_type === "fallback" &&
                !selectedIsResolved ? (
                <Button
                  bg="#003597"
                  color="#ffffff"
                  borderRadius="full"
                  _hover={{ bg: "#0049ca", transform: "translateY(-1px)", boxShadow: "0px 4px 8px rgba(0, 53, 151, 0.2)" }}
                  fontFamily="'Manrope', sans-serif"
                  onClick={() => resolveEvent(selected.id)}
                  isLoading={!!resolvingById[selected.id]}
                >
                  Marcar resuelto
                </Button>
              ) : null}

              <Button
                variant="ghost"
                borderRadius="full"
                color="#737686"
                _hover={{ bg: "rgba(195, 197, 215, 0.15)" }}
                fontFamily="'Manrope', sans-serif"
                onClick={closeDetail}
              >
                Cerrar
              </Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
