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
  useColorModeValue,
} from "@chakra-ui/react";
import { useTranslation } from 'react-i18next';
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
  const { t } = useTranslation();
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

  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const pageBg = useColorModeValue("#f8f9fa", "gray.900");
  const inputBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.500");
  const textLabel = useColorModeValue("#434654", "gray.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryBg = useColorModeValue("#e8edff", "blue.900");
  const successText = useColorModeValue("#1b5e20", "green.300");
  const successBg = useColorModeValue("#e8f5e9", "green.900");
  const errorText = useColorModeValue("#c62828", "red.300");
  const errorBg = useColorModeValue("#ffebee", "red.900");
  const borderColor = useColorModeValue("rgba(195, 197, 215, 0.4)", "whiteAlpha.200");

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
      toast({ status: "warning", title: t('bulk_page.toast.select_csv') });
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
          title: t('bulk_page.toast.preview_errors'),
          description: t('bulk_page.toast.invalid_rows').replace('{{count}}', String(data.invalid_rows)),
        });
      } else {
        toast({ status: "success", title: t('bulk_page.toast.preview_ok') });
      }
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? t('bulk_page.toast.preview_error');
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
      toast({ status: "success", title: t('bulk_page.toast.import_ok') });
    } catch (e: any) {
      const msg = e?.body?.detail ?? e?.message ?? t('bulk_page.toast.import_error');
      toast({ status: "error", title: "Error", description: String(msg) });
    } finally {
      setLoadingApply(false);
    }
  }

  return (
    <Box p={{ base: 4, md: 8 }} bg={pageBg} minH="100vh" maxW="100%" overflowX="hidden">
      <Flex justify="space-between" align="flex-start" mb={{ base: 6, md: 8 }} gap={4} direction={{ base: "column", md: "row" }} maxW="1200px" mx="auto">
        <Box>
          <Heading size="2xl" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor} mb={2}>
            {t('bulk_page.header.title')}
          </Heading>
          <Text fontFamily="'Manrope', sans-serif" color={textLabel}>
            <span dangerouslySetInnerHTML={{ __html: t('bulk_page.header.desc') }} />
          </Text>
        </Box>
        <Button
          w={{ base: "full", md: "auto" }}
          variant="outline"
          borderRadius="xl"
          borderColor={borderColor}
          bg={cardBg}
          color={primaryColor}
          fontFamily="'Manrope', sans-serif"
          fontWeight="bold"
          _hover={{ bg: inputBg }}
          onClick={downloadTemplate}
        >
          {t('bulk_page.header.download')}
        </Button>
      </Flex>

      <Grid templateColumns={{ base: "1fr", lg: "300px 1fr" }} gap={{ base: 6, md: 8 }} maxW="1200px" mx="auto">
        <GridItem>
          <Box bg={cardBg} border="1px solid" borderColor={borderColor} p={6} borderRadius="2rem" mb={6}>
            <Box bg={primaryBg} w="48px" h="48px" borderRadius="xl" mb={4} display="flex" alignItems="center" justifyContent="center">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" fill="white" fillOpacity="0.2" />
                <path d="M10.5 7.5L12 4.5L13.5 7.5L16.5 9L13.5 10.5L12 13.5L10.5 10.5L7.5 9L10.5 7.5Z" fill="currentColor" color={primaryColor} />
                <path d="M15 15L16 13L17 15L19 16L17 17L16 19L15 17L13 16L15 15Z" fill="currentColor" color={primaryColor} />
                <path d="M7.5 16.5L8.25 14.75L10 14L8.25 13.25L7.5 11.5L6.75 13.25L5 14L6.75 14.75L7.5 16.5Z" fill="currentColor" color={primaryColor} />
              </svg>
            </Box>
            <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor} mb={3}>
              {t('bulk_page.fluid_arch.title')}
            </Heading>
            <Text fontFamily="'Manrope', sans-serif" color={textLabel} fontSize="sm" mb={4}>
              {t('bulk_page.fluid_arch.desc')}
            </Text>
            <VStack align="start" spacing={3}>
              <HStack spacing={2}>
                <CheckCircleIcon color={primaryColor} w={4} h={4} />
                <Text fontFamily="'Manrope', sans-serif" color={textLabel} fontSize="sm">{t('bulk_page.fluid_arch.max_size')}</Text>
              </HStack>
              <HStack spacing={2}>
                <CheckCircleIcon color={primaryColor} w={4} h={4} />
                <Text fontFamily="'Manrope', sans-serif" color={textLabel} fontSize="sm">{t('bulk_page.fluid_arch.format')}</Text>
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
              {t('bulk_page.fluid_arch.banner')}
            </Text>
          </Box>
        </GridItem>

        <GridItem minW="0">

          <Box mb={6} bg={cardBg} borderRadius="2rem" boxShadow="0 20px 40px rgba(0,0,0,0.03)" p={{ base: 6, md: 8 }}>
            <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor} mb={8}>
              {t('bulk_page.upload.title')}
            </Heading>

            <VStack align="stretch" spacing={6}>
              {isPlatformAdmin && (
                <Box bg={inputBg} p={5} borderRadius="xl" border="1px solid" borderColor={borderColor}>
                  <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color={textLabel} fontSize="sm" textTransform="uppercase" letterSpacing="wider" mb={2}>
                    {t('bulk_page.upload.admin_label')}
                  </Text>
                  <Input
                    value={schoolId}
                    onChange={(e) => setSchoolId(e.target.value)}
                    placeholder={t('bulk_page.upload.admin_placeholder')}
                    bg={cardBg}
                    color={textColor}
                    fontFamily="'Manrope', sans-serif"
                    borderRadius="xl"
                    border="1px solid"
                    borderColor={borderColor}
                    _focus={{ borderColor: primaryColor, boxShadow: `0 0 0 1px ${primaryColor}` }}
                  />
                  <Text fontSize="xs" color={textMuted} fontFamily="'Manrope', sans-serif" mt={2}>
                    <span dangerouslySetInnerHTML={{ __html: t('bulk_page.upload.admin_help') }} />
                  </Text>
                </Box>
              )}

              <Box>
                <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color={textLabel} fontSize="sm" textTransform="uppercase" letterSpacing="wider" mb={3}>
                  {t('bulk_page.upload.csv_label')}
                </Text>

                <Box
                  bg={inputBg}
                  borderRadius="2rem"
                  border="2px dashed"
                  borderColor={borderColor}
                  p={10}
                  textAlign="center"
                  position="relative"
                  transition="all 0.2s"
                  _hover={{ bg: pageBg, borderColor: primaryColor }}
                >
                  <Box
                    bg={cardBg}
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
                      <path d="M14 2H6C4.89543 2 4 2.89543 4 4V20C4 21.1046 4.89543 22 6 22H18C19.1046 22 20 21.1046 20 20V8L14 2Z" fill="currentColor" color={primaryColor} />
                      <path d="M14 2V8H20" stroke="currentColor" color={cardBg} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                      <path d="M12 18V12M12 12L9 15M12 12L15 15" stroke="currentColor" color={cardBg} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  </Box>

                  <Heading size="sm" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor} mb={1}>
                    {t('bulk_page.upload.drop')}
                  </Heading>
                  <Text fontFamily="'Manrope', sans-serif" color={textMuted} fontSize="sm" mb={6}>
                    {t('bulk_page.upload.select')}
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
                    <Badge bg={primaryBg} color={primaryColor} px={4} py={2} borderRadius="full" fontFamily="'Manrope', sans-serif" textTransform="none">
                      {file.name}
                    </Badge>
                  )}
                </Box>
              </Box>

              <HStack spacing={4} mt={2}>
                <Button
                  onClick={onPreview}
                  isLoading={loadingPreview}
                  bg={primaryColor}
                  color="white"
                  borderRadius="full"
                  px={8}
                  fontFamily="'Manrope', sans-serif"
                  _hover={{ filter: "brightness(0.9)" }}
                  isDisabled={!file}
                >
                  {t('bulk_page.upload.preview_btn')}
                </Button>

                <Button
                  onClick={onApply}
                  isLoading={loadingApply}
                  bg={inputBg}
                  color={textColor}
                  borderRadius="full"
                  px={8}
                  fontFamily="'Manrope', sans-serif"
                  _hover={{ filter: "brightness(0.95)" }}
                  isDisabled={!canApply}
                >
                  {t('bulk_page.upload.apply_btn')}
                </Button>
              </HStack>

              {!preview && (
                <Alert status="info" borderRadius="xl" bg={primaryBg} color={primaryColor} mt={4} border="1px solid" borderColor={borderColor}>
                  <AlertIcon color={primaryColor} />
                  <Box>
                    <Text fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="bold" fontSize="sm" mb={1}>
                      {t('bulk_page.upload.info_title')}
                    </Text>
                    <Text fontFamily="'Manrope', sans-serif" fontSize="xs" color={textMuted}>
                      {t('bulk_page.upload.info_desc')}
                    </Text>
                  </Box>
                </Alert>
              )}
            </VStack>
          </Box>

          {preview && (
            <Box mb={6} bg={cardBg} borderRadius="2rem" border="1px solid" borderColor={borderColor} p={6}>
              <Box mb={4}>
                <Flex justify="space-between" align="center" flexWrap="wrap" gap={4}>
                  <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={textColor}>
                    {t('bulk_page.preview_data.title')}
                  </Heading>
                  <HStack spacing={2} wrap="wrap">
                    <Badge variant="subtle" bg={inputBg} color={textLabel} borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      {t('bulk_page.preview_data.total')} {preview.total_rows}
                    </Badge>
                    <Badge variant="subtle" bg={successBg} color={successText} borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      {t('bulk_page.preview_data.valid')} {preview.valid_rows}
                    </Badge>
                    <Badge variant="subtle" bg={preview.invalid_rows > 0 ? errorBg : successBg} color={preview.invalid_rows > 0 ? errorText : successText} borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" textTransform="none">
                      {t('bulk_page.preview_data.invalid')} {preview.invalid_rows}
                    </Badge>
                  </HStack>
                </Flex>
              </Box>

              <Box>
                {preview.will_create_classes?.length > 0 && (
                  <Box mb={6}>
                    <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color={textColor} mb={3}>
                      {t('bulk_page.preview_data.will_create')}
                    </Text>
                    <Flex wrap="wrap" gap={2}>
                      {preview.will_create_classes.map((c) => (
                        <Tag key={c} bg={inputBg} color={primaryColor} borderRadius="full" px={3} py={1} fontFamily="'Manrope', sans-serif" fontWeight="bold">
                          {c}
                        </Tag>
                      ))}
                    </Flex>
                    <Divider borderColor={borderColor} mt={6} />
                  </Box>
                )}

                {preview.invalid_rows > 0 && (
                  <Box mb={6}>
                    <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color={errorText} mb={3}>
                      {t('bulk_page.preview_data.errors')} ({t('bulk_page.preview_data.first')} {Math.min(50, preview.errors.length)}):
                    </Text>
                    <Box overflowX="auto" bg={errorBg} borderRadius="xl" border="1px solid" borderColor="red.200">
                      <Table size="sm" variant="simple">
                        <Thead>
                          <Tr>
                            <Th color={errorText} fontFamily="'Manrope', sans-serif">Row</Th>
                            <Th color={errorText} fontFamily="'Manrope', sans-serif">Field</Th>
                            <Th color={errorText} fontFamily="'Manrope', sans-serif">Message</Th>
                          </Tr>
                        </Thead>
                        <Tbody>
                          {preview.errors.slice(0, 50).map((err, idx) => (
                            <Tr key={idx} _hover={{ bg: "whiteAlpha.100" }}>
                              <Td color={textColor} fontFamily="'Manrope', sans-serif">{err.row}</Td>
                              <Td color={textColor} fontFamily="'Manrope', sans-serif">{err.field || "-"}</Td>
                              <Td color={textColor} fontFamily="'Manrope', sans-serif">{err.message}</Td>
                            </Tr>
                          ))}
                        </Tbody>
                      </Table>
                    </Box>
                    <Divider borderColor={borderColor} mt={6} />
                  </Box>
                )}

                <Text fontWeight="bold" fontFamily="'Manrope', sans-serif" color={textColor} mb={3}>
                  {t('bulk_page.preview_data.sample')} {preview.sample.length} {t('bulk_page.preview_data.parsed_rows')}):
                </Text>

                <Box overflowX="auto" borderRadius="xl" border="1px solid" borderColor={borderColor}>
                  <Table size="sm" variant="simple">
                    <Thead bg={inputBg}>
                      <Tr>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted}>full_name</Th>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted} display={{ base: "none", md: "table-cell" }}>age</Th>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted} display={{ base: "none", md: "table-cell" }}>group</Th>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted}>classes</Th>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted} display={{ base: "none", md: "table-cell" }}>notes</Th>
                        <Th fontFamily="'Manrope', sans-serif" color={textMuted} display={{ base: "none", md: "table-cell" }}>school_id</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {preview.sample.map((r, idx) => (
                        <Tr key={idx} _hover={{ bg: inputBg }}>
                          <Td fontFamily="'Manrope', sans-serif" color={textColor}>{r.full_name}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color={textLabel} display={{ base: "none", md: "table-cell" }}>{r.age ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color={textLabel} display={{ base: "none", md: "table-cell" }}>{r.group ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color={textLabel}>{Array.isArray(r.classes) ? r.classes.join(" | ") : "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color={textLabel} display={{ base: "none", md: "table-cell" }}>{r.notes ?? "-"}</Td>
                          <Td fontFamily="'Manrope', sans-serif" color={textLabel} display={{ base: "none", md: "table-cell" }}>{r.school_id}</Td>
                        </Tr>
                      ))}
                    </Tbody>
                  </Table>
                </Box>
              </Box>
            </Box>
          )}

          {applyResult && (
            <Box bg={successBg} borderRadius="2rem" border="1px solid" borderColor="green.200" p={6}>
              <Box mb={4}>
                <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={successText}>
                  {t('bulk_page.result.title')}
                </Heading>
              </Box>
              <HStack spacing={3} wrap="wrap">
                <Badge variant="subtle" bg="green.100" color="green.800" borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  {t('bulk_page.result.students')} {applyResult.created_students}
                </Badge>
                <Badge variant="subtle" bg={inputBg} color={textLabel} borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  {t('bulk_page.result.classes')} {applyResult.created_classes}
                </Badge>
                <Badge variant="subtle" bg={inputBg} color={textLabel} borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  {t('bulk_page.result.links')} {applyResult.created_student_class_links}
                </Badge>
                <Badge variant="subtle" bg={applyResult.skipped_rows > 0 ? errorBg : inputBg} color={applyResult.skipped_rows > 0 ? errorText : textMuted} borderRadius="full" px={4} py={2} fontFamily="'Manrope', sans-serif" textTransform="none" fontSize="sm">
                  {t('bulk_page.result.skipped')} {applyResult.skipped_rows}
                </Badge>
              </HStack>
            </Box>
          )}
        </GridItem>
      </Grid>
    </Box>
  );
}
