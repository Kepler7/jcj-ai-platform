import React, { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Heading,
  HStack,
  Select,
  Spinner,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  Alert,
  AlertIcon,
  Badge,
  VStack,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Divider,
  useDisclosure,
  Code,
  Stack,
} from "@chakra-ui/react";
import { api } from "../lib/apiClient";
import { useNavigate } from "react-router-dom";

type StatusFilter = "pending" | "resolved" | "all";

type PlaybookFallbackEvent = {
  id: string;
  school_id: string;
  student_id: string;
  report_id: string;
  ai_report_id: string | null;

  topic_nucleo: string | null;
  context: string | string[] | null;
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
  strengths: string;
  challenges: string;
  notes: string | null;
  created_at: string;
};

type Recommendation = {
  title: string;
  steps: string[];
  when_to_use?: string | null;
};

type AIVersion = {
  summary: string;
  signals_detected?: string[];
  recommendations?: Recommendation[];
  // classroom_plan_7_days / home_plan_7_days los dejamos fuera a propósito (spoiler: luego lo quitamos)
};

type AIReport = {
  id: string;
  report_id: string;
  student_id: string;
  school_id: string;
  model_name: string;
  created_at: string;
  teacher_version: AIVersion;
  parent_version: AIVersion;
  guardrails_passed: boolean;
  guardrails_notes: string | null;
};

function formatContext(ctx: PlaybookFallbackEvent["context"]) {
  if (!ctx) return "-";
  if (Array.isArray(ctx)) return ctx.join(", ");
  return String(ctx);
}

function safeText(x: any) {
  if (x === null || x === undefined) return "";
  return String(x);
}

export default function PlaybookPendientesPage() {
  const navigate = useNavigate();

  const [statusFilter, setStatusFilter] = useState<StatusFilter>("pending");
  const [rows, setRows] = useState<PlaybookFallbackEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  const [reportDetail, setReportDetail] = useState<StudentReport | null>(null);
  const [aiDetail, setAiDetail] = useState<AIReport | null>(null);

  const [resolvingById, setResolvingById] = useState<Record<string, boolean>>(
    {}
  );

  // ✅ Modal state
  const { isOpen, onOpen, onClose } = useDisclosure();
  const [selected, setSelected] = useState<PlaybookFallbackEvent | null>(null);

  async function openDetail(r: PlaybookFallbackEvent) {
    setSelected(r);
    setDetailError(null);
    setReportDetail(null);
    setAiDetail(null);
    onOpen();

    setDetailLoading(true);
    try {
      // 1) Traer el reporte base
      // Preferimos /v1/reports/{id} si existe. Si no existe, fallback con lista por student_id.
      let rep: StudentReport | null = null;

      try {
        rep = await api<StudentReport>(`/v1/reports/${r.report_id}`, {
          auth: true,
        });
      } catch (e1: any) {
        // fallback: listar por alumno y buscar el ID
        const list = await api<StudentReport[]>(
          `/v1/reports?student_id=${encodeURIComponent(r.student_id)}`,
          { auth: true }
        );
        rep = list.find((x) => x.id === r.report_id) ?? null;
      }

      setReportDetail(rep);

      // 2) Traer el AI report más reciente del report_id (igual que en ReportsPage)
      const ai = await api<any>(
        `/v1/ai-reports?report_id=${encodeURIComponent(r.report_id)}`,
        { auth: true }
      );
      const latest: AIReport | null = Array.isArray(ai)
        ? ai?.[0] ?? null
        : ai ?? null;
      setAiDetail(latest);
    } catch (e: any) {
      setDetailError(e?.message ?? "No se pudo cargar el detalle del reporte");
    } finally {
      setDetailLoading(false);
    }
  }

  function closeDetail() {
    onClose();
    setSelected(null);
    setDetailError(null);
    setReportDetail(null);
    setAiDetail(null);
  }

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const data = await api<PlaybookFallbackEvent[]>(
        `/v1/playbook-fallbacks?status_filter=${encodeURIComponent(
          statusFilter
        )}&limit=200`,
        { auth: true }
      );
      setRows(data);
    } catch (e: any) {
      setError(e?.message ?? "No se pudo cargar Pendientes de Playbook");
    } finally {
      setLoading(false);
    }
  }

  async function resolveEvent(id: string) {
    setResolvingById((p) => ({ ...p, [id]: true }));
    try {
      await api(`/v1/playbook-fallbacks/${id}/resolve`, {
        method: "POST",
        auth: true,
      });
      await load();

      // ✅ avisa al navbar que refresque el badge
      window.dispatchEvent(new Event("playbook:pending-changed"));
    } catch (e: any) {
      setError(e?.message ?? "No se pudo resolver el evento");
    } finally {
      setResolvingById((p) => ({ ...p, [id]: false }));
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const pendingCount = useMemo(
    () => rows.filter((r) => !r.resolved_at).length,
    [rows]
  );

  const selectedIsResolved = !!selected?.resolved_at;

  return (
    <Box p={6}>
      <HStack justify="space-between" align="flex-start" mb={4}>
        <Box>
          <Heading size="lg">Pendientes de Playbook</Heading>
          <Text color="gray.600" mt={1}>
            Eventos donde <b>no se encontraron estrategias JCJ</b> y el modelo
            tuvo que responder con sugerencias generales.
          </Text>
        </Box>

        <HStack spacing={3}>
          <Select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            w="220px"
          >
            <option value="pending">Pendientes</option>
            <option value="resolved">Resueltos</option>
            <option value="all">Todos</option>
          </Select>

          <Button onClick={load} variant="outline" isLoading={loading}>
            Recargar
          </Button>
        </HStack>
      </HStack>

      {error && (
        <Alert status="error" mb={4} borderRadius="md">
          <AlertIcon />
          <Text>{error}</Text>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <HStack justify="space-between">
            <Heading size="md">
              Lista{" "}
              {statusFilter === "pending" && (
                <Badge ml={2} colorScheme="orange">
                  {pendingCount} pendientes
                </Badge>
              )}
            </Heading>

            {loading && (
              <HStack>
                <Spinner size="sm" />
                <Text color="gray.600">Cargando…</Text>
              </HStack>
            )}
          </HStack>
        </CardHeader>

        <CardBody>
          {rows.length === 0 ? (
            <Text color="gray.600">
              No hay eventos para este filtro por ahora.
            </Text>
          ) : (
            <Box overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>CREATED</Th>
                    <Th>TOPIC</Th>
                    <Th>CONTEXT</Th>
                    <Th>REASON</Th>
                    <Th>QUERY</Th>
                    <Th>SUMMARY</Th>
                    <Th>STATUS</Th>
                    <Th>ACTIONS</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {rows.map((r) => {
                    const isResolved = !!r.resolved_at;

                    return (
                      <Tr key={r.id} opacity={isResolved ? 0.7 : 1}>
                        <Td whiteSpace="nowrap">
                          {new Date(r.created_at).toLocaleString()}
                        </Td>

                        <Td>
                          <Text fontSize="sm">{r.topic_nucleo ?? "-"}</Text>
                        </Td>

                        <Td>
                          <Text fontSize="sm">{formatContext(r.context)}</Text>
                        </Td>

                        <Td>
                          <Badge colorScheme={r.reason ? "purple" : "gray"}>
                            {r.reason || "n/a"}
                          </Badge>
                        </Td>

                        <Td maxW="280px">
                          <Text fontSize="sm" noOfLines={3}>
                            {r.query_text ?? "-"}
                          </Text>
                        </Td>

                        <Td maxW="320px">
                          <Text fontSize="sm" noOfLines={3}>
                            {r.model_output_summary ?? "-"}
                          </Text>
                        </Td>

                        <Td whiteSpace="nowrap">
                          {isResolved ? (
                            <Badge colorScheme="green">Resuelto</Badge>
                          ) : (
                            <Badge colorScheme="orange">Pendiente</Badge>
                          )}
                        </Td>

                        <Td whiteSpace="nowrap">
                          <VStack align="stretch" spacing={2}>
                            <Button
                              size="xs"
                              variant="outline"
                              onClick={() => openDetail(r)}
                            >
                              Ver detalle
                            </Button>

                            {!isResolved ? (
                              <Button
                                size="xs"
                                onClick={() => resolveEvent(r.id)}
                                isLoading={!!resolvingById[r.id]}
                                colorScheme="green"
                              >
                                Marcar resuelto
                              </Button>
                            ) : (
                              <Text fontSize="xs" color="gray.600">
                                {r.resolved_at
                                  ? new Date(r.resolved_at).toLocaleString()
                                  : ""}
                              </Text>
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
        </CardBody>
      </Card>

      {/* ✅ MODAL DETALLE (con Reporte + AI completo) */}
      <Modal
        isOpen={isOpen}
        onClose={closeDetail}
        size="4xl"
        scrollBehavior="inside"
      >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>
            Detalle de fallback{" "}
            {selected ? `• ${new Date(selected.created_at).toLocaleString()}` : ""}
          </ModalHeader>
          <ModalCloseButton />

          <ModalBody>
            {detailError && (
              <Alert status="error" mb={4} borderRadius="md">
                <AlertIcon />
                <Text>{detailError}</Text>
              </Alert>
            )}

            {!selected ? (
              <Text color="gray.600">Sin selección.</Text>
            ) : detailLoading ? (
              <HStack>
                <Spinner size="sm" />
                <Text>Cargando detalle…</Text>
              </HStack>
            ) : (
              <VStack align="stretch" spacing={4}>
                {/* Header */}
                <HStack justify="space-between" align="start">
                  <Box>
                    <Text fontSize="sm" color="gray.600">
                      Estado
                    </Text>
                    {selectedIsResolved ? (
                      <Badge colorScheme="green">Resuelto</Badge>
                    ) : (
                      <Badge colorScheme="orange">Pendiente</Badge>
                    )}
                    <Text fontSize="xs" color="gray.600" mt={1}>
                      Reason: <b>{selected.reason || "n/a"}</b>
                    </Text>
                  </Box>

                  <HStack spacing={2} flexWrap="wrap" justify="flex-end">
                    <Badge variant="subtle" colorScheme="blue">
                      Topic: {selected.topic_nucleo ?? "-"}
                    </Badge>
                    <Badge variant="subtle" colorScheme="gray">
                      Context: {formatContext(selected.context)}
                    </Badge>
                  </HStack>
                </HStack>

                <Divider />

                {/* Fallback content */}
                <Box>
                  <Text fontWeight="semibold" mb={1}>
                    Query (completo)
                  </Text>
                  <Box borderWidth="1px" borderRadius="md" p={3} bg="gray.50">
                    <Text fontSize="sm" whiteSpace="pre-wrap">
                      {selected.query_text ?? "-"}
                    </Text>
                  </Box>
                </Box>

                <Box>
                  <Text fontWeight="semibold" mb={1}>
                    Summary del modelo (completo)
                  </Text>
                  <Box borderWidth="1px" borderRadius="md" p={3} bg="gray.50">
                    <Text fontSize="sm" whiteSpace="pre-wrap">
                      {selected.model_output_summary ?? "-"}
                    </Text>
                  </Box>
                </Box>

                <Divider />

                {/* StudentReport */}
                <Box>
                  <Heading size="sm" mb={2}>
                    Reporte del maestro (StudentReport)
                  </Heading>

                  {!reportDetail ? (
                    <Alert status="warning" borderRadius="md">
                      <AlertIcon />
                      <Text fontSize="sm">
                        No se pudo cargar el reporte base. (Revisa si existe
                        <Code mx={1} fontSize="xs">
                          GET /v1/reports/:id
                        </Code>
                        o si el reporte pertenece al alumno.)
                      </Text>
                    </Alert>
                  ) : (
                    <Stack spacing={3}>
                      <Box>
                        <Text fontWeight="semibold">Fortalezas</Text>
                        <Text fontSize="sm" whiteSpace="pre-wrap">
                          {safeText(reportDetail.strengths) || "-"}
                        </Text>
                      </Box>

                      <Box>
                        <Text fontWeight="semibold">Retos</Text>
                        <Text fontSize="sm" whiteSpace="pre-wrap">
                          {safeText(reportDetail.challenges) || "-"}
                        </Text>
                      </Box>

                      <Box>
                        <Text fontWeight="semibold">Notas</Text>
                        <Text fontSize="sm" whiteSpace="pre-wrap">
                          {reportDetail.notes ?? "-"}
                        </Text>
                      </Box>
                    </Stack>
                  )}
                </Box>

                <Divider />

                {/* AI Report */}
                <Box>
                  <Heading size="sm" mb={2}>
                    Apoyo generado por IA
                  </Heading>

                  {!aiDetail ? (
                    <Alert status="warning" borderRadius="md">
                      <AlertIcon />
                      <Text fontSize="sm">
                        No se encontró AI report para este reporte (o no se pudo
                        cargar).
                      </Text>
                    </Alert>
                  ) : (
                    <Stack spacing={4}>
                      <HStack justify="space-between" align="start" flexWrap="wrap">
                        <Box>
                          <Text fontSize="sm" color="gray.600">
                            Modelo
                          </Text>
                          <Text fontWeight="semibold">{aiDetail.model_name}</Text>
                        </Box>
                        <Box textAlign="right">
                          <Text fontSize="sm" color="gray.600">
                            Creado
                          </Text>
                          <Text fontWeight="semibold">
                            {new Date(aiDetail.created_at).toLocaleString()}
                          </Text>
                        </Box>
                      </HStack>

                      <Box>
                        <Text fontWeight="semibold" mb={1}>
                          Resumen (familia)
                        </Text>
                        <Box borderWidth="1px" borderRadius="md" p={3}>
                          <Text fontSize="sm" whiteSpace="pre-wrap">
                            {aiDetail.parent_version?.summary ?? "-"}
                          </Text>
                        </Box>
                      </Box>

                      <Box>
                        <Text fontWeight="semibold" mb={1}>
                          Señales detectadas (familia)
                        </Text>
                        <Box borderWidth="1px" borderRadius="md" p={3}>
                          {(aiDetail.parent_version?.signals_detected ?? [])
                            .length === 0 ? (
                            <Text fontSize="sm" color="gray.600">
                              -
                            </Text>
                          ) : (
                            <Stack spacing={1}>
                              {(aiDetail.parent_version?.signals_detected ??
                                []).map((s, idx) => (
                                <Text key={idx} fontSize="sm">
                                  • {s}
                                </Text>
                              ))}
                            </Stack>
                          )}
                        </Box>
                      </Box>

                      <Box>
                        <Text fontWeight="semibold" mb={1}>
                          Recomendaciones (familia)
                        </Text>
                        {(aiDetail.parent_version?.recommendations ?? [])
                          .length === 0 ? (
                          <Text fontSize="sm" color="gray.600">
                            -
                          </Text>
                        ) : (
                          <Stack spacing={3}>
                            {(aiDetail.parent_version?.recommendations ??
                              []).map((rec, idx) => (
                              <Box
                                key={idx}
                                borderWidth="1px"
                                borderRadius="md"
                                p={3}
                              >
                                <HStack justify="space-between" mb={1}>
                                  <Text fontWeight="semibold">{rec.title}</Text>
                                  {rec.when_to_use ? (
                                    <Badge
                                      variant="subtle"
                                      colorScheme="purple"
                                    >
                                      {rec.when_to_use}
                                    </Badge>
                                  ) : null}
                                </HStack>
                                <Stack spacing={1} mt={2}>
                                  {(rec.steps ?? []).map((st, i) => (
                                    <Text key={i} fontSize="sm">
                                      • {st}
                                    </Text>
                                  ))}
                                </Stack>
                              </Box>
                            ))}
                          </Stack>
                        )}
                      </Box>

                      {aiDetail.guardrails_notes ? (
                        <Alert status="warning" borderRadius="md">
                          <AlertIcon />
                          <Text fontSize="sm">{aiDetail.guardrails_notes}</Text>
                        </Alert>
                      ) : null}
                    </Stack>
                  )}
                </Box>

                <Divider />

                {/* IDs debug */}
                <Box>
                  <Text fontWeight="semibold" mb={2}>
                    IDs (debug)
                  </Text>
                  <VStack align="stretch" spacing={1}>
                    <Text fontSize="sm">
                      student_id:{" "}
                      <Code fontSize="xs">{selected.student_id}</Code>
                    </Text>
                    <Text fontSize="sm">
                      report_id:{" "}
                      <Code fontSize="xs">{selected.report_id}</Code>
                    </Text>
                    <Text fontSize="sm">
                      ai_report_id:{" "}
                      <Code fontSize="xs">{selected.ai_report_id ?? "-"}</Code>
                    </Text>
                    <Text fontSize="sm">
                      school_id:{" "}
                      <Code fontSize="xs">{selected.school_id}</Code>
                    </Text>
                  </VStack>
                </Box>
              </VStack>
            )}
          </ModalBody>

          <ModalFooter>
            <HStack spacing={3}>
              {selected?.student_id && selected?.report_id ? (
                <Button
                  variant="outline"
                  onClick={() => {
                    // ✅ Navega a los reportes del alumno.
                    // Si luego quieres autoseleccionar el reporte, lo haces con query param.
                    navigate(
                      `/students/${selected.student_id}/reports?report_id=${encodeURIComponent(
                        selected.report_id
                      )}`
                    );
                    closeDetail();
                  }}
                >
                  Ir al reporte
                </Button>
              ) : null}

              {!selectedIsResolved && selected ? (
                <Button
                  colorScheme="green"
                  isLoading={!!resolvingById[selected.id]}
                  onClick={async () => {
                    await resolveEvent(selected.id);
                    closeDetail();
                  }}
                >
                  Marcar resuelto
                </Button>
              ) : null}

              <Button onClick={closeDetail}>Cerrar</Button>
            </HStack>
          </ModalFooter>
        </ModalContent>
      </Modal>
    </Box>
  );
}
