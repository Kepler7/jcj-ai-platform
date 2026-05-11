import { useEffect, useState } from 'react';
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
  Flex,
  Grid,
  GridItem,
  Avatar,
  Badge,
  InputGroup,
  InputLeftElement,
  HStack,
  IconButton,
  useColorModeValue,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Building2, ArrowRight, Search, ListFilter, ArrowUpDown, ChevronLeft, ChevronRight } from 'lucide-react';
import { api } from '../lib/apiClient';

type School = {
  id: string;
  name: string;
  legal_name?: string | null;
  city?: string | null;
  state?: string | null;
  is_active: boolean;
};

export default function SchoolsPage() {
  const { t } = useTranslation();
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [creating, setCreating] = useState(false);

  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const inputBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.600");
  const textLabel = useColorModeValue("#434654", "gray.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const primaryBg = useColorModeValue("#e8edff", "blue.900");
  const highlightColor = useColorModeValue("#006c4a", "green.300");
  const highlightBg = useColorModeValue("#e1fedc", "green.900");
  const errorText = useColorModeValue("#ba1a1a", "red.300");
  const errorBg = useColorModeValue("#ffeceb", "red.900");
  const borderColor = useColorModeValue("#f3f4f5", "whiteAlpha.100");

  async function load() {
    setError(null);
    setLoading(true);
    try {
      const data = await api<School[]>('/v1/schools', { auth: true });
      setSchools(data);
    } catch (e: any) {
      setError(e?.message ?? 'Failed to load schools');
    } finally {
      setLoading(false);
    }
  }

  async function createSchool() {
    setError(null);
    setCreating(true);
    try {
      const created = await api<School>('/v1/schools', {
        method: 'POST',
        auth: true,
        body: {
          name: name.trim(),
          city: city.trim() || null,
          state: state.trim() || null,
        },
      });
      setSchools((prev) => [created, ...prev]);
      setName('');
      setCity('');
      setState('');
    } catch (e: any) {
      setError(e?.message ?? 'Failed to create school');
    } finally {
      setCreating(false);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <Box px={{ base: 4, md: 8 }} py={{ base: 6, md: 8 }} maxW="100%" overflowX="hidden">
      {/* Header */}
      <Flex direction={{ base: "column", md: "row" }} justify="space-between" align={{ base: "flex-start", md: "center" }} mb={{ base: 6, md: 8 }} gap="4">
        <Box>
          <Heading as="h1" fontSize={{ base: "3xl", md: "4xl" }} fontWeight="extrabold" color={primaryColor} fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" mb="2">
            {t("schools_page.title")}
          </Heading>
          <Text color={textMuted} fontSize="sm" maxW="550px" lineHeight="tall">
            {t("schools_page.subtitle")}
          </Text>
        </Box>
        <Flex align="center" gap="2">
          <Box w="2" h="2" borderRadius="full" bg={highlightColor} mt="0.5" />
          <Text color={textLabel} fontSize="sm" fontWeight="semibold">{t("schools_page.system_status")}</Text>
        </Flex>
      </Flex>

      {/* Main Grid */}
      <Grid templateColumns={{ base: '1fr', lg: '350px 1fr' }} gap={{ base: 6, md: 8 }}>

        {/* Left Column */}
        <GridItem minW="0">
          {/* Create School Widget */}
          <Box bg={cardBg} borderRadius="2rem" p={{ base: 6, md: 8 }} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" mb="6">
            <Flex align="center" mb="8" gap="4">
              <Flex align="center" justify="center" w="12" h="12" bg={primaryBg} color={primaryColor} borderRadius="xl">
                <Building2 size={24} />
              </Flex>
              <Text fontSize="xl" fontWeight="bold" color={textColor}>{t("schools_page.add_new")}</Text>
            </Flex>

            <Stack gap="5">
              <Box>
                <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="2" textTransform="uppercase" letterSpacing="wider">
                  {t("schools_page.name")}
                </Text>
                <Input
                  placeholder={t("schools_page.placeholder_name")}
                  value={name}
                  onChange={(e) => setName(e.target.value)}
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
                    {t("schools_page.city")}
                  </Text>
                  <Input
                    placeholder="Guadalajara"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
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
                    {t("schools_page.state")}
                  </Text>
                  <Input
                    placeholder="Jalisco"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
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
              </Flex>

              <Button
                mt="4"
                onClick={createSchool}
                isLoading={creating}
                isDisabled={!name.trim()}
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
                {t("schools_page.add_btn")}
              </Button>

              {error && (
                <Text mt="1" color={errorText} fontSize="sm" textAlign="center">
                  {error}
                </Text>
              )}
            </Stack>
          </Box>

          {/* Active Institutions Widget */}
          <Box bg={inputBg} borderRadius="2rem" p={{ base: 6, md: 8 }} position="relative" overflow="hidden">
            <Box position="relative" zIndex="2">
              <Text fontSize="xs" fontWeight="bold" color={textLabel} mb="1">
                {t("schools_page.active_schools")}
              </Text>
              <Text fontSize="4xl" fontWeight="extrabold" color={primaryColor} fontFamily="'Plus Jakarta Sans', sans-serif">
                {schools.filter(s => s.is_active).length}
              </Text>
            </Box>
            <Box position="absolute" right="-4" bottom="-6" opacity="0.05" transform="scale(1.5)" zIndex="1" color={textColor}>
              <Building2 size={100} />
            </Box>
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
                placeholder={t("schools_page.search_placeholder")}
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
              <Button leftIcon={<ListFilter size={16} />} bg={cardBg} border="none" borderRadius="full" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" px="6" fontSize="sm" fontWeight="bold" color={textColor} _hover={{ bg: inputBg }}>
                {t("schools_page.filter")}
              </Button>
              <Button leftIcon={<ArrowUpDown size={16} />} bg={cardBg} border="none" borderRadius="full" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" px="6" fontSize="sm" fontWeight="bold" color={textColor} _hover={{ bg: inputBg }}>
                {t("schools_page.sort")}
              </Button>
            </HStack>
          </Flex>

          {/* Table Box */}
          <Box bg={cardBg} borderRadius="2rem" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" overflow="hidden">
            {loading ? (
              <Box p="10" textAlign="center">
                <Text color={textMuted} fontWeight="medium">{t("schools_page.loading")}</Text>
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
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" pl={{ base: 4, md: 8 }} py="6">{t("schools_page.table.school_name")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" py="6">{t("schools_page.table.location")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" py="6" display={{ base: "none", md: "table-cell" }}>{t("schools_page.table.active")}</Th>
                        <Th fontSize="xs" fontWeight="bold" color={textMuted} textTransform="uppercase" letterSpacing="wider" pr={{ base: 4, md: 8 }} py="6" display={{ base: "none", md: "table-cell" }}>{t("schools_page.table.id")}</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {schools.map((s, idx) => {
                        const colors = [
                          { bg: primaryBg, text: primaryColor },
                          { bg: highlightBg, text: highlightColor },
                          { bg: errorBg, text: errorText }
                        ];
                        const color = colors[idx % 3];
                        const isYes = s.is_active;

                        return (
                          <Tr key={s.id} position="relative" role="group">
                            <Td pl={{ base: 4, md: 8 }} py="4">
                              <Flex align="center" gap="4">
                                <Avatar
                                  size="md"
                                  name={s.name}
                                  bg={color.bg}
                                  color={color.text}
                                  fontWeight="bold"
                                />
                                <Box>
                                  <Text fontWeight="bold" color={textColor} fontSize="sm">{s.name}</Text>
                                  <Text fontSize="xs" color={textMuted}>{t("schools_page.last_updated_recently")}</Text>
                                </Box>
                              </Flex>
                            </Td>
                            <Td py="4">
                              <Box>
                                <Text fontWeight="bold" color={textLabel} fontSize="sm">{s.city ?? t("schools_page.unknown")}</Text>
                                <Text fontSize="xs" color={textMuted}>{s.state ? `${s.state}` : '-'}</Text>
                              </Box>
                            </Td>
                            <Td py="4" display={{ base: "none", md: "table-cell" }}>
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
                                {isYes ? t("schools_page.table.yes") : t("schools_page.table.no")}
                              </Badge>
                            </Td>
                            <Td pr={{ base: 4, md: 8 }} py="4" display={{ base: "none", md: "table-cell" }}>
                              <Badge bg={inputBg} color={textLabel} fontFamily="mono" fontSize="xs" px="2" py="1" borderRadius="md" textTransform="none">
                                {(s.id || '').substring(0, 36)}
                              </Badge>
                            </Td>
                          </Tr>
                        )
                      })}
                      {schools.length === 0 && !loading && (
                        <Tr>
                          <Td colSpan={4} textAlign="center" py="10" color={textMuted} fontSize="sm">
                            {t("schools_page.table.empty")}
                          </Td>
                        </Tr>
                      )}
                    </Tbody>
                  </Table>
                </Box>

                {/* Pagination Footer */}
                {schools.length > 0 && (
                  <Flex borderTop="1px solid" borderColor={borderColor} px={{ base: 4, md: 8 }} py="4" justify="space-between" align="center">
                    <Text fontSize="xs" color={textMuted} fontWeight="medium">
                      {t("schools_page.pagination.showing")} 1-{Math.min(10, schools.length)} {t("schools_page.pagination.of")} {schools.length} {t("schools_page.pagination.results")}
                    </Text>
                    <HStack spacing="1">
                      <IconButton aria-label="Previous" icon={<ChevronLeft size={16} />} size="sm" variant="ghost" color={textMuted} />
                      <Button size="sm" bg={primaryColor} color="white" borderRadius="md" _hover={{ bg: "#0049ca" }}>1</Button>
                      <Button size="sm" variant="ghost" color={textLabel} borderRadius="md">2</Button>
                      <Button size="sm" variant="ghost" color={textLabel} borderRadius="md">3</Button>
                      <IconButton aria-label="Next" icon={<ChevronRight size={16} />} size="sm" variant="ghost" color={textMuted} />
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
