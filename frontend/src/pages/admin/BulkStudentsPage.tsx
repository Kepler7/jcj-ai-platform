import { useMemo, useState } from "react";
import {
  Alert,
  AlertIcon,
  Box,
  Button,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Flex,
  Heading,
  HStack,
  Input,
  Table,
  Tbody,
  Td,
  Text,
  Th,
  Thead,
  Tr,
  Tag,
  useToast,
  VStack,
} from "@chakra-ui/react";

import {
  bulkStudentsApply,
  bulkStudentsPreview,
  type BulkStudentsApplyResponse,
  type BulkStudentsPreviewResponse,
} from "../../lib/studentsBulk";

function getRole(): string {
  return localStorage.getItem("role") || "";
}

function getSchoolId(): string {
  return localStorage.getItem("school_id") || "";
}

export default function BulkStudentsPage() {
  const toast = useToast();

  const role = getRole();
  const mySchoolId = getSchoolId();
  const isPlatformAdmin = role === "platform_admin";

  const [file, setFile] = useState<File | null>(null);
  const [schoolId, setSchoolId] = useState<string>(mySchoolId || "");

  const [preview, setPreview] = useState<BulkStudentsPreviewResponse | null>(null);
  const [applyResult, setApplyResult] = useState<BulkStudentsApplyResponse | null>(null);

  const [loadingPreview, setLoadingPreview] = useState(false);
  const [loadingApply, setLoadingApply] = useState(false);

  const effectiveSchoolId = isPlatformAdmin ? (schoolId || undefined) : (mySchoolId || undefined);

  const canApply = useMemo(() => {
    return !!file && !!preview && preview.invalid_rows === 0;
  }, [file, preview]);

  function downloadTemplate() {
    const sid = mySchoolId || "SCHOOL_ID";
    const csv =
      "school_id,full_name,age,classes,notes\n" +
      `${sid},Juan Perez,6,PreK2-A|Inglés,Se distrae con ruido.\n` +
      `${sid},Ana López,7,PreK2-A,Le gusta participar.\n`;

    const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "students_template.csv";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function onPreview() {
    if (!file) {
      toast({ status: "warning", title: "Selecciona un CSV primero." });
      return;
    }

    setLoadingPreview(true);
    setApplyResult(null);

    try {
      const data = await bulkStudentsPreview({ file, schoolId: effectiveSchoolId });
      setPreview(data);

      if (data.invalid_rows > 0) {
        toast({
          status: "warning",
          title: "Preview listo con errores",
          description: `Filas inválidas: ${data.invalid_rows}`,
        });
      } else {
        toast({ status: "success", title: "Preview OK (sin errores)" });
      }
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? "Error al generar preview";
      toast({ status: "error", title: "Error", description: String(msg) });
      setPreview(null);
    } finally {
      setLoadingPreview(false);
    }
  }

  async function onApply() {
    if (!file) return;

    setLoadingApply(true);
    try {
      const data = await bulkStudentsApply({ file, schoolId: effectiveSchoolId });
      setApplyResult(data);
      toast({ status: "success", title: "Importación completada" });
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? "Error al aplicar importación";
      toast({ status: "error", title: "Error", description: String(msg) });
    } finally {
      setLoadingApply(false);
    }
  }

  return (
    <Box p={6}>
      <Flex justify="space-between" align="center" mb={4}>
        <Heading size="lg">Bulk Students</Heading>
        <Button variant="outline" onClick={downloadTemplate}>
          Descargar template CSV
        </Button>
      </Flex>

      <Card mb={4}>
        <CardHeader>
          <Heading size="md">Subir archivo</Heading>
        </CardHeader>
        <CardBody>
          <VStack align="stretch" spacing={4}>
            {isPlatformAdmin && (
              <Box>
                <Text fontWeight="semibold" mb={2}>
                  School ID (solo platform_admin)
                </Text>
                <Input
                  value={schoolId}
                  onChange={(e) => setSchoolId(e.target.value)}
                  placeholder="UUID de la escuela (opcional si viene en el CSV)"
                />
                <Text fontSize="sm" opacity={0.8} mt={1}>
                  Si no lo pones aquí, el CSV debe traer columna <b>school_id</b>.
                </Text>
              </Box>
            )}

            <Box>
              <Text fontWeight="semibold" mb={2}>
                Archivo CSV
              </Text>
              <Input
                type="file"
                accept=".csv,text/csv"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
              {file && (
                <Text mt={2} fontSize="sm" opacity={0.8}>
                  Seleccionado: <b>{file.name}</b>
                </Text>
              )}
            </Box>

            <HStack spacing={3}>
              <Button
                onClick={onPreview}
                isLoading={loadingPreview}
                colorScheme="blue"
                isDisabled={!file}
              >
                Preview
              </Button>

              <Button
                onClick={onApply}
                isLoading={loadingApply}
                colorScheme="green"
                isDisabled={!canApply}
              >
                Apply
              </Button>
            </HStack>

            {!preview && (
              <Alert status="info">
                <AlertIcon />
                <Text>
                Sube un CSV y presiona <b>Preview</b>. Solo podrás hacer <b>Apply</b> si no hay errores.
                </Text>
              </Alert>
            )}
          </VStack>
        </CardBody>
      </Card>

      {preview && (
        <Card mb={4}>
          <CardHeader>
            <Flex justify="space-between" align="center">
              <Heading size="md">Preview</Heading>
              <HStack>
                <Tag>Total: {preview.total_rows}</Tag>
                <Tag colorScheme="green">Válidas: {preview.valid_rows}</Tag>
                <Tag colorScheme={preview.invalid_rows > 0 ? "red" : "green"}>
                  Inválidas: {preview.invalid_rows}
                </Tag>
              </HStack>
            </Flex>
          </CardHeader>

          <CardBody>
            {preview.will_create_classes?.length > 0 && (
              <>
                <Text fontWeight="semibold" mb={2}>
                  Se crearán estas clases (si aplicas):
                </Text>
                <Flex wrap="wrap" gap={2} mb={4}>
                  {preview.will_create_classes.map((c) => (
                    <Tag key={c}>{c}</Tag>
                  ))}
                </Flex>
                <Divider mb={4} />
              </>
            )}

            {preview.invalid_rows > 0 && (
              <>
                <Text fontWeight="semibold" mb={2}>
                  Errores (primeros {Math.min(50, preview.errors.length)}):
                </Text>
                <Box overflowX="auto" mb={4}>
                  <Table size="sm">
                    <Thead>
                      <Tr>
                        <Th>Row</Th>
                        <Th>Field</Th>
                        <Th>Message</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {preview.errors.slice(0, 50).map((err, idx) => (
                        <Tr key={idx}>
                          <Td>{err.row}</Td>
                          <Td>{err.field || "-"}</Td>
                          <Td>{err.message}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
                <Divider mb={4} />
              </>
            )}

            <Text fontWeight="semibold" mb={2}>
              Muestra (primeras {preview.sample.length} filas parseadas):
            </Text>

            <Box overflowX="auto">
              <Table size="sm">
                <Thead>
                  <Tr>
                    <Th>full_name</Th>
                    <Th>age</Th>
                    <Th>group</Th>
                    <Th>classes</Th>
                    <Th>notes</Th>
                    <Th>school_id</Th>
                  </Tr>
                </Thead>
                <Tbody>
                  {preview.sample.map((r, idx) => (
                    <Tr key={idx}>
                      <Td>{r.full_name}</Td>
                      <Td>{r.age ?? "-"}</Td>
                      <Td>{r.group ?? "-"}</Td>
                      <Td>{Array.isArray(r.classes) ? r.classes.join(" | ") : "-"}</Td>
                      <Td>{r.notes ?? "-"}</Td>
                      <Td>{r.school_id}</Td>
                    </Tr>
                  ))}
                </Tbody>
              </Table>
            </Box>
          </CardBody>
        </Card>
      )}

      {applyResult && (
        <Card>
          <CardHeader>
            <Heading size="md">Resultado Apply</Heading>
          </CardHeader>
          <CardBody>
            <HStack spacing={4} wrap="wrap">
              <Tag colorScheme="green">Students creados: {applyResult.created_students}</Tag>
              <Tag>Clases creadas: {applyResult.created_classes}</Tag>
              <Tag>Links creados: {applyResult.created_student_class_links}</Tag>
              <Tag>Skipped: {applyResult.skipped_rows}</Tag>
            </HStack>
          </CardBody>
        </Card>
      )}
    </Box>
  );
}