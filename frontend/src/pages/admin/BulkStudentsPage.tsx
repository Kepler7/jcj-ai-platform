import { useMemo, useState } from "react";
import {
  Alert,
  AlertIcon,
  Badge,
  Box,
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
  Grid,
  GridItem,
  Button,
} from "@chakra-ui/react";
import { CheckCircleIcon } from "@chakra-ui/icons";

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
    <Box p={{ base: 4, md: 8 }} bg="#f8f9fa" minH="100vh" maxW="100%" overflowX="hidden">
      <Flex justify="space-between" align="flex-start" mb={{ base: 6, md: 8 }} gap={4} direction={{ base: "column", md: "row" }} maxW="1200px" mx="auto">
        <Box>
          <Heading size="2xl" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={2}>
            Bulk Students
          </Heading>
          <Text fontFamily="'Manrope', sans-serif" color="#434654">
            Efficiently manage institutional data. Import multiple student records via CSV <br />
            and synchronize your database in seconds.
          </Text>
        </Box>
        <Button
          w={{ base: "full", md: "auto" }}
          variant="outline"
          borderRadius="xl"
          borderColor="rgba(195, 197, 215, 0.4)"
          bg="#ffffff"
          color="#003597"
          fontFamily="'Manrope', sans-serif"
          fontWeight="bold"
          _hover={{ bg: "#f3f4f5" }}
          onClick={downloadTemplate}
        >
          Descargar template CSV
        </Button>
      </Flex>

      <Grid templateColumns={{ base: "1fr", lg: "300px 1fr" }} gap={{ base: 6, md: 8 }} maxW="1200px" mx="auto">
        <GridItem>
          <Box bg="#f4f6fb" p={6} borderRadius="2rem" mb={6}>
            <Box bg="#00472f" w="48px" h="48px" borderRadius="xl" mb={4} display="flex" alignItems="center" justifyContent="center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" fill="white" />
                <path d="M10.5 7.5L12 4.5L13.5 7.5L16.5 9L13.5 10.5L12 13.5L10.5 10.5L7.5 9L10.5 7.5Z" fill="#81d8ae" />
                <path d="M15 15L16 13L17 15L19 16L17 17L16 19L15 17L13 16L15 15Z" fill="#81d8ae" />
                <path d="M7.5 16.5L8.25 14.75L10 14L8.25 13.25L7.5 11.5L6.75 13.25L5 14L6.75 14.75L7.5 16.5Z" fill="#81d8ae" />
              </svg>
            </Box>
            <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={3}>
              Fluid Architecture
            </Heading>
            <Text fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm" mb={4}>
              Our intelligent engine validates data types, name formats, and institutional IDs automatically before ingestion.
            </Text>
            <VStack align="start" spacing={3}>
              <HStack spacing={2}>
                <CheckCircleIcon color="#003597" w={4} h={4} />
                <Text fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">Max size: 10MB per file</Text>
              </HStack>
              <HStack spacing={2}>
                <CheckCircleIcon color="#003597" w={4} h={4} />
                <Text fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm">Format: UTF-8 Encoded CSV</Text>
              </HStack>
            </VStack>
          </Box>

          <Box
            h="180px"
            bg="linear-gradient(to bottom, rgba(0, 53, 151, 0.4), rgba(0, 53, 151, 0.8)), url('https://images.unsplash.com/photo-1522202176988-66273c2fd55f?q=80&w=1471&auto=format&fit=crop')"
            bgSize="cover"
            bgPosition="center"
            borderRadius="2rem"
            p={6}
            display="flex"
            alignItems="flex-end"
          >
            <Text fontFamily="'Manrope', sans-serif" color="#ffffff" fontSize="sm" fontWeight="bold">
              Enseña asi , Aprende asi...
            </Text>
          </Box>
        </GridItem>

        <GridItem minW="0">

          <Box mb={6} bg="#ffffff" borderRadius="2rem" boxShadow="0 20px 40px rgba(0,0,0,0.03)" p={{ base: 6, md: 8 }}>
            <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={8}>
              Subir archivo
            </Heading>

            <VStack align="stretch" spacing={6}>
              {isPlatformAdmin && (
                <Box bg="#fcfcfc" p={5} borderRadius="xl" border="1px solid rgba(195, 197, 215, 0.2)">
                  <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm" textTransform="uppercase" letterSpacing="wider" mb={2}>
                    School ID (Solo Admin)
                  </Text>
                  <Input
                    value={schoolId}
                    onChange={(e) => setSchoolId(e.target.value)}
                    placeholder="UUID de la escuela (opcional si viene en el CSV)"
                    bg="#ffffff"
                    fontFamily="'Manrope', sans-serif"
                    borderRadius="xl"
                    border="1px solid rgba(195, 197, 215, 0.3)"
                    _focus={{ borderColor: "rgba(0, 53, 151, 0.3)", boxShadow: "0 0 0 1px rgba(0, 53, 151, 0.3)" }}
                  />
                  <Text fontSize="xs" color="#737686" fontFamily="'Manrope', sans-serif" mt={2}>
                    Si no lo pones aquí, el CSV debe traer columna <b>school_id</b>.
                  </Text>
                </Box>
              )}

              <Box>
                <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#434654" fontSize="sm" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  Archivo CSV
                </Text>

                <Box
                  bg="#f8f9fa"
                  borderRadius="2rem"
                  border="2px dashed rgba(195, 197, 215, 0.6)"
                  p={10}
                  textAlign="center"
                  position="relative"
                  transition="all 0.2s"
                  _hover={{ bg: "#f3f4f5", borderColor: "#0c50d6" }}
                >
                  <Box
                    bg="#ffffff"
                    w="48px"
                    h="48px"
                    borderRadius="full"
                    display="inline-flex"
                    alignItems="center"
                    justifyContent="center"
                    boxShadow="sm"
                    mb={4}
                  >
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <path d="M14 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2Z" fill="#0c50d6" />
                      <path d="M14 2V8H20" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M12 18V12M12 12L9 15M12 12L15 15" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </Box>

                  <Heading size="sm" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d" mb={1}>
                    Drop your file here or browse
                  </Heading>
                  <Text fontFamily="'Manrope', sans-serif" color="#737686" fontSize="sm" mb={6}>
                    Select a CSV file to begin the preview process
                  </Text>

                  <Input
                    type="file"
                    accept=".csv,text/csv"
                    onChange={(e) => setFile(e.target.files?.[0] || null)}
                    position="absolute"
                    top="0"
                    left="0"
                    width="100%"
                    height="100%"
                    opacity="0"
                    cursor="pointer"
                  />

                  {file && (
                    <Badge bg="#e8edff" color="#0c50d6" px={4} py={2} borderRadius="full" fontFamily="'Manrope', sans-serif" textTransform="none">
                      {file.name}
                    </Badge>
                  )}
                </Box>
              </Box>

              <HStack spacing={4} mt={2}>
                <Button
                  onClick={onPreview}
                  isLoading={loadingPreview}
                  bg="#003597"
                  color="#ffffff"
                  borderRadius="full"
                  px={8}
                  fontFamily="'Manrope', sans-serif"
                  _hover={{ bg: "#0049ca", boxShadow: "0px 4px 8px rgba(0, 53, 151, 0.2)" }}
                  isDisabled={!file}
                >
                  Preview
                </Button>

                <Button
                  onClick={onApply}
                  isLoading={loadingApply}
                  bg="#edeeef"
                  color="#737686"
                  borderRadius="full"
                  px={8}
                  fontFamily="'Manrope', sans-serif"
                  _hover={{ bg: "#e1e3e4" }}
                  isDisabled={!canApply}
                >
                  Apply Changes
                </Button>
              </HStack>

              {!preview && (
                <Alert status="info" borderRadius="xl" bg="#eef2ff" color="#191c1d" mt={4} border="1px solid rgba(0, 73, 202, 0.1)">
                  <AlertIcon color="#0049ca" />
                  <Box>
                    <Text fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="bold" fontSize="sm" mb={1}>
                      Sube un CSV y presiona Preview.
                    </Text>
                    <Text fontFamily="'Manrope', sans-serif" fontSize="xs" color="#434656">
                      Solo podrás hacer Apply si no hay errores detectados en la validación inicial del archivo.
                    </Text>
                  </Box>
                </Alert>
              )}
            </VStack>
          </Box>

          {preview && (
            <Box mb={6} bg="#ffffff" borderRadius="2rem" border="1px solid rgba(195, 197, 215, 0.3)" p={6}>
              <Box mb={4}>
                <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
                  <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
                    Preview de Datos
                  </Heading>
                  <HStack spacing={2} wrap="wrap">
                    <Badge variant="subtle" bg="#f3f4f5" color="#434654" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      Total: {preview.total_rows}
                    </Badge>
                    <Badge variant="subtle" bg="#e8f5e9" color="#2e7d32" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      Válidas: {preview.valid_rows}
                    </Badge>
                    <Badge variant="subtle" bg={preview.invalid_rows > 0 ? "#ffebee" : "#e8f5e9"} color={preview.invalid_rows > 0 ? "#c62828" : "#2e7d32"} borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      Inválidas: {preview.invalid_rows}
                    </Badge>
                  </HStack>
                </Flex>
              </Box>

              <Box>
                {preview.will_create_classes?.length > 0 && (
                  <Box mb={6}>
                    <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d" mb={3}>
                      Se crearán estas clases (si aplicas):
                    </Text>
                    <Flex wrap="wrap" gap={2}>
                      {preview.will_create_classes.map((c) => (
                        <Tag key={c} bg="#f3f4f5" color="#003597" borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" fontWeight="bold">
                          {c}
                        </Tag>
                      ))}
                    </Flex>
                    <Divider borderColor="rgba(195, 197, 215, 0.3)" mt={6} />
                  </Box>
                )}

                {preview.invalid_rows > 0 && (
                  <Box mb={6}>
                    <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#c62828" mb={3}>
                      ⚠️ Errores (primeros {Math.min(50, preview.errors.length)}):
                    </Text>
                    <Box overflowX="auto" bg="#ffebee" borderRadius="xl" border="1px solid rgba(198, 40, 40, 0.2)">
                      <Table size="sm" variant="simple">
                        <Thead>
                          <Tr>
                            <Th color="#c62828" fontFamily="'Manrope', sans-serif">Row</Th>
                            <Th color="#c62828" fontFamily="'Manrope', sans-serif">Field</Th>
                            <Th color="#c62828" fontFamily="'Manrope', sans-serif">Message</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {preview.errors.slice(0, 50).map((err, idx) => (
                            <Tr key={idx} _hover={{ bg: "rgba(198, 40, 40, 0.05)" }}>
                              <Td color="#434654" fontFamily="'Manrope', sans-serif">{err.row}</Td>
                              <Td color="#434654" fontFamily="'Manrope', sans-serif">{err.field || "-"}</Td>
                              <Td color="#434654" fontFamily="'Manrope', sans-serif">{err.message}</Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </Box>
                    <Divider borderColor="rgba(195, 197, 215, 0.3)" mt={6} />
                  </Box>
                )}

                <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color="#191c1d" mb={3}>
                  Muestra (primeras {preview.sample.length} filas parseadas):
                </Text>

                <Box overflowX="auto" borderRadius="xl" border="1px solid rgba(195, 197, 215, 0.3)">
                  <Table size="sm" variant="simple">
                    <Thead bg="#f8f9fa">
                      <Tr>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686">full_name</Th>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686" display={{ base: "none", md: "table-cell" }}>age</Th>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686" display={{ base: "none", md: "table-cell" }}>group</Th>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686">classes</Th>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686" display={{ base: "none", md: "table-cell" }}>notes</Th>
                        <Th fontFamily="'Manrope', sans-serif" color="#737686" display={{ base: "none", md: "table-cell" }}>school_id</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {preview.sample.map((r, idx) => (
                        <Tr key={idx} _hover={{ bg: "#f3f4f5" }}>
                          <Td fontFamily="'Manrope', sans-serif" color="#191c1d">{r.full_name}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color="#434654" display={{ base: "none", md: "table-cell" }}>{r.age ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color="#434654" display={{ base: "none", md: "table-cell" }}>{r.group ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color="#434654">{Array.isArray(r.classes) ? r.classes.join(" | ") : "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color="#434654" display={{ base: "none", md: "table-cell" }}>{r.notes ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color="#434654" display={{ base: "none", md: "table-cell" }}>{r.school_id}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </Box>
            </Box>
          )}

          {applyResult && (
            <Box bg="#e8f5e9" borderRadius="2rem" border="1px solid rgba(46, 125, 50, 0.2)" p={6}>
              <Box mb={4}>
                <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#1b5e20">
                  Resultado de Importación
                </Heading>
              </Box>
              <HStack spacing={3} wrap="wrap">
                <Badge variant="subtle" bg="#c8e6c9" color="#1b5e20" borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  Estudiantes creados: {applyResult.created_students}
                </Badge>
                <Badge variant="subtle" bg="#f3f4f5" color="#434654" borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  Clases creadas: {applyResult.created_classes}
                </Badge>
                <Badge variant="subtle" bg="#f3f4f5" color="#434654" borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  Links creados: {applyResult.created_student_class_links}
                </Badge>
                <Badge variant="subtle" bg={applyResult.skipped_rows > 0 ? "#ffebee" : "#f8f9fa"} color={applyResult.skipped_rows > 0 ? "#c62828" : "#737686"} borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  Skipped: {applyResult.skipped_rows}
                </Badge>
              </HStack>
            </Box>
          )}
        </GridItem>
      </Grid>
    </Box>
  );
}