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
} from '@chakra-ui/react';
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
  const [schools, setSchools] = useState<School[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [name, setName] = useState('');
  const [city, setCity] = useState('');
  const [state, setState] = useState('');
  const [creating, setCreating] = useState(false);

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
          <Heading as="h1" fontSize={{ base: "3xl", md: "4xl" }} fontWeight="extrabold" color="#003597" fontFamily="'Plus Jakarta Sans', sans-serif" letterSpacing="tight" mb="2">
            Schools
          </Heading>
          <Text color="#737686" fontSize="sm" maxW="550px" lineHeight="tall">
            Orchestrate your educational network. Add new institutions and manage existing environments from a centralized architect dashboard.
          </Text>
        </Box>
        <Flex align="center" gap="2">
          <Box w="2" h="2" borderRadius="full" bg="#006c4a" mt="0.5" />
          <Text color="#434654" fontSize="sm" fontWeight="semibold">System Status: Optimal</Text>
        </Flex>
      </Flex>

      {/* Main Grid */}
      <Grid templateColumns={{ base: '1fr', lg: '350px 1fr' }} gap={{ base: 6, md: 8 }}>

        {/* Left Column */}
        <GridItem minW="0">
          {/* Create School Widget */}
          <Box bg="#ffffff" borderRadius="2rem" p={{ base: 6, md: 8 }} boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" mb="6">
            <Flex align="center" mb="8" gap="4">
              <Flex align="center" justify="center" w="12" h="12" bg="#e8edff" color="#003597" borderRadius="xl">
                <Building2 size={24} />
              </Flex>
              <Text fontSize="xl" fontWeight="bold" color="#191c1d">Create school</Text>
            </Flex>

            <Stack gap="5">
              <Box>
                <Text fontSize="xs" fontWeight="bold" color="#434654" mb="2" textTransform="uppercase" letterSpacing="wider">
                  Institutional Name
                </Text>
                <Input
                  placeholder="e.g. JCJ Neuroeducativo"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  bg="#f3f4f5"
                  border="none"
                  borderRadius="xl"
                  py="6"
                  fontSize="sm"
                  color="#191c1d"
                  _placeholder={{ color: "#737686" }}
                  _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: "#ffffff", outline: "none" }}
                />
              </Box>

              <Flex gap="4" direction={{ base: "column", md: "row" }}>
                <Box flex="1">
                  <Text fontSize="xs" fontWeight="bold" color="#434654" mb="2" textTransform="uppercase" letterSpacing="wider">
                    City
                  </Text>
                  <Input
                    placeholder="Guadalajara"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    bg="#f3f4f5"
                    border="none"
                    borderRadius="xl"
                    py="6"
                    fontSize="sm"
                    color="#191c1d"
                    _placeholder={{ color: "#737686" }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: "#ffffff", outline: "none" }}
                  />
                </Box>
                <Box flex="1">
                  <Text fontSize="xs" fontWeight="bold" color="#434654" mb="2" textTransform="uppercase" letterSpacing="wider">
                    State
                  </Text>
                  <Input
                    placeholder="Jalisco"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    bg="#f3f4f5"
                    border="none"
                    borderRadius="xl"
                    py="6"
                    fontSize="sm"
                    color="#191c1d"
                    _placeholder={{ color: "#737686" }}
                    _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: "#ffffff", outline: "none" }}
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
                Create School
              </Button>

              {error && (
                <Text mt="1" color="#ba1a1a" fontSize="sm" textAlign="center">
                  {error}
                </Text>
              )}
            </Stack>
          </Box>

          {/* Active Institutions Widget */}
          <Box bg="#f3f4f5" borderRadius="2rem" p={{ base: 6, md: 8 }} position="relative" overflow="hidden">
            <Box position="relative" zIndex="2">
              <Text fontSize="xs" fontWeight="bold" color="#434654" mb="1">
                Active Institutions
              </Text>
              <Text fontSize="4xl" fontWeight="extrabold" color="#003597" fontFamily="'Plus Jakarta Sans', sans-serif">
                {schools.filter(s => s.is_active).length}
              </Text>
            </Box>
            <Box position="absolute" right="-4" bottom="-6" opacity="0.05" transform="scale(1.5)" zIndex="1" color="#191c1d">
              <Building2 size={100} />
            </Box>
          </Box>
        </GridItem>

        <GridItem minW="0">
          {/* Controls Bar */}
          <Flex gap="4" mb="6" direction={{ base: "column", md: "row" }}>
            <InputGroup size="lg" flex="1">
              <InputLeftElement pointerEvents="none" color="#737686">
                <Search size={20} />
              </InputLeftElement>
              <Input
                placeholder="Search by name, city or ID..."
                bg="#ffffff"
                border="none"
                borderRadius="full"
                fontSize="sm"
                color="#191c1d"
                boxShadow="0px 4px 12px rgba(25,28,29,0.03)"
                _placeholder={{ color: "#c3c5d7" }}
                _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", outline: "none" }}
              />
            </InputGroup>

            <HStack spacing="3">
              <Button leftIcon={<ListFilter size={16} />} bg="#ffffff" border="none" borderRadius="full" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" px="6" fontSize="sm" fontWeight="bold" color="#191c1d" _hover={{ bg: "#f3f4f5" }}>
                Filter
              </Button>
              <Button leftIcon={<ArrowUpDown size={16} />} bg="#ffffff" border="none" borderRadius="full" boxShadow="0px 4px 12px rgba(25,28,29,0.03)" px="6" fontSize="sm" fontWeight="bold" color="#191c1d" _hover={{ bg: "#f3f4f5" }}>
                Sort
              </Button>
            </HStack>
          </Flex>

          {/* Table Box */}
          <Box bg="#ffffff" borderRadius="2rem" boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)" overflow="hidden">
            {loading ? (
              <Box p="10" textAlign="center">
                <Text color="#737686" fontWeight="medium">Loading schools...</Text>
              </Box>
            ) : (
              <>
                <Box w="full" overflowX="auto" pb="4">
                  <Table variant="unstyled" sx={{
                    "tbody tr": { transition: "background 0.2s" },
                    "tbody tr:hover": { bg: "#f8f9fa" }
                  }}>
                    <Thead>
                      <Tr borderBottom="1px solid #f3f4f5">
                        <Th fontSize="xs" fontWeight="bold" color="#737686" textTransform="uppercase" letterSpacing="wider" pl={{ base: 4, md: 8 }} py="6">SCHOOL NAME</Th>
                        <Th fontSize="xs" fontWeight="bold" color="#737686" textTransform="uppercase" letterSpacing="wider" py="6">LOCATION</Th>
                        <Th fontSize="xs" fontWeight="bold" color="#737686" textTransform="uppercase" letterSpacing="wider" py="6" display={{ base: "none", md: "table-cell" }}>ACTIVE</Th>
                        <Th fontSize="xs" fontWeight="bold" color="#737686" textTransform="uppercase" letterSpacing="wider" pr={{ base: 4, md: 8 }} py="6" display={{ base: "none", md: "table-cell" }}>ID</Th>
                      </Tr>
                    </Thead>
                    <Tbody>
                      {schools.map((s, idx) => {
                        const colors = [
                          { bg: "#e8edff", text: "#003597" },
                          { bg: "#e1fedc", text: "#006c4a" },
                          { bg: "#ffeceb", text: "#ba1a1a" }
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
                                  <Text fontWeight="bold" color="#191c1d" fontSize="sm">{s.name}</Text>
                                  <Text fontSize="xs" color="#737686">Last updated recently</Text>
                                </Box>
                              </Flex>
                            </Td>
                            <Td py="4">
                              <Box>
                                <Text fontWeight="bold" color="#434654" fontSize="sm">{s.city ?? 'Unknown'}</Text>
                                <Text fontSize="xs" color="#737686">{s.state ? `${s.state}` : '-'}</Text>
                              </Box>
                            </Td>
                            <Td py="4" display={{ base: "none", md: "table-cell" }}>
                              <Badge
                                bg={isYes ? "#e1fedc" : "#ffeceb"}
                                color={isYes ? "#006c4a" : "#ba1a1a"}
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
                                <Box w="1.5" h="1.5" borderRadius="full" bg={isYes ? "#006c4a" : "#ba1a1a"} />
                                {isYes ? 'YES' : 'NO'}
                              </Badge>
                            </Td>
                            <Td pr={{ base: 4, md: 8 }} py="4" display={{ base: "none", md: "table-cell" }}>
                              <Badge bg="#f3f4f5" color="#434654" fontFamily="mono" fontSize="xs" px="2" py="1" borderRadius="md" textTransform="none">
                                {(s.id || '').substring(0, 36)}
                              </Badge>
                            </Td>
                          </Tr>
                        )
                      })}
                      {schools.length === 0 && !loading && (
                        <Tr>
                          <Td colSpan={4} textAlign="center" py="10" color="#737686" fontSize="sm">
                            No schools found. Create one.
                          </Td>
                        </Tr>
                      )}
                    </Tbody>
                  </Table>
                </Box>

                {/* Pagination Footer */}
                {schools.length > 0 && (
                  <Flex borderTop="1px solid #f3f4f5" px={{ base: 4, md: 8 }} py="4" justify="space-between" align="center">
                    <Text fontSize="xs" color="#737686" fontWeight="medium">
                      Showing 1-{Math.min(10, schools.length)} of {schools.length} results
                    </Text>
                    <HStack spacing="1">
                      <IconButton aria-label="Previous" icon={<ChevronLeft size={16} />} size="sm" variant="ghost" color="#737686" />
                      <Button size="sm" bg="#003597" color="white" borderRadius="md" _hover={{ bg: "#0049ca" }}>1</Button>
                      <Button size="sm" variant="ghost" color="#434654" borderRadius="md">2</Button>
                      <Button size="sm" variant="ghost" color="#434654" borderRadius="md">3</Button>
                      <IconButton aria-label="Next" icon={<ChevronRight size={16} />} size="sm" variant="ghost" color="#737686" />
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
