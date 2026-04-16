import { useState } from 'react';
import {
  Box,
  Button,
  Heading,
  Input,
  Text,
  Link,
  Flex,
  InputGroup,
  InputLeftElement,
  Image,
} from '@chakra-ui/react';
import { Link as RouterLink } from 'react-router-dom';
import { Mail, ArrowLeft } from 'lucide-react';
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

console.log('API_BASE:', API_BASE);

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatusMsg(null);
    setLoading(true);

    try {
      const res = await fetch(`${API_BASE}/v1/auth/forgot-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email.trim() }),
      });

      // aunque falle, tu backend puede devolver siempre neutro,
      // pero si hay error real (500, etc.) lo mostramos.
      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? 'Request failed');
      }

      setStatusMsg('If the email exists, you will receive instructions.');
    } catch (err: any) {
      setError(err?.message ?? 'Request failed');
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box
      position="relative"
      minH="100vh"
      display="flex"
      flexDir="column"
      alignItems="center"
      justifyContent="center"
      px="6"
      pb="12"
      bg="#f8f9fa"
      color="#191c1d"
      overflow="hidden"
      fontFamily="'Manrope', sans-serif"
    >
      {/* Abstract Background Elements */}
      <Box position="absolute" top="-10%" right="-10%" w={{ base: "300px", md: "500px" }} h={{ base: "300px", md: "500px" }} borderRadius="full" bg="rgba(0,53,151,0.05)" filter="blur(120px)" />
      <Box position="absolute" bottom="-10%" left="-10%" w={{ base: "250px", md: "400px" }} h={{ base: "250px", md: "400px" }} borderRadius="full" bg="rgba(0,71,47,0.05)" filter="blur(100px)" />

      <Box w="full" maxW="480px" zIndex="10">
        <Box bg="#ffffff" borderRadius="2rem" boxShadow="0px 24px 48px rgba(25,28,29,0.06)" overflow="hidden">
          <Box p={{ base: 10, md: 14 }}>
            <Flex direction="column" align="center" mb="6">
              <Image
                alt="IHUI Logo"
                h={{ base: 32, md: 40 }}
                w="auto"
                mb="4"
                objectFit="contain"
                src="/ihui_logo.png"
              />
              <Heading as="h1" fontSize="2xl" fontWeight="extrabold" letterSpacing="tight" color="#191c1d" mb="2" fontFamily="'Plus Jakarta Sans', sans-serif">
                Recover your password
              </Heading>
              <Text fontSize="sm" color="#434654" textAlign="center" px="4">
                Enter your email address and we'll send you a link to reset your password.
              </Text>
            </Flex>

            <form onSubmit={onSubmit}>
              <Flex direction="column" gap="5">
                <Box>
                  <Text as="label" display="block" fontSize="sm" fontWeight="semibold" color="#434654" ml="1" mb="2">
                    Email Address
                  </Text>
                  <InputGroup size="lg" className="group">
                    <InputLeftElement pointerEvents="none" color="#c3c5d7" _groupFocusWithin={{ color: "#003597" }}>
                      <Mail size={20} />
                    </InputLeftElement>
                    <Input
                      placeholder="name@company.com"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      autoComplete="email"
                      type="email"
                      bg="#f3f4f5"
                      border="none"
                      borderRadius="xl"
                      color="#191c1d"
                      _placeholder={{ color: "#737686" }}
                      _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: "#f8f9fa", outline: "none" }}
                      fontSize="sm"
                      fontWeight="medium"
                      px="4"
                      pl="12"
                      py="1"
                    />
                  </InputGroup>
                </Box>

                {statusMsg && (
                  <Text color="#006142" bg="#e8f5e9" p="3" borderRadius="xl" fontSize="sm" textAlign="center" fontWeight="bold">
                    {statusMsg}
                  </Text>
                )}
                {error && (
                  <Text color="#ba1a1a" bg="#ffdad6" p="3" borderRadius="xl" fontSize="sm" textAlign="center" fontWeight="bold">
                    {error}
                  </Text>
                )}

                <Box pt="2">
                  <Button
                    type="submit"
                    isLoading={loading}
                    w="full"
                    py="6"
                    bgGradient="linear(to-r, #003597, #0049ca)"
                    color="white"
                    borderRadius="full"
                    fontWeight="bold"
                    fontSize="md"
                    boxShadow="0px 10px 15px -3px rgba(0, 53, 151, 0.2)"
                    _hover={{ transform: "scale(1.02)", bgGradient: "linear(to-r, #003597, #0049ca)" }}
                    _active={{ transform: "scale(0.98)" }}
                    transition="all 0.2s ease-in-out"
                  >
                    Send reset link
                  </Button>
                </Box>

                <Flex justify="center" align="center" mt="4">
                  <Link as={RouterLink} to="/login" fontSize="sm" fontWeight="bold" color="#0c50d6" _hover={{ color: "#003597" }} display="flex" alignItems="center" gap="2">
                    <ArrowLeft size={16} /> Back to login
                  </Link>
                </Flex>
              </Flex>
            </form>
          </Box>
        </Box>
      </Box>

      {/* Footer */}
      <Box as="footer" position="absolute" bottom="0" w="full" py={{ base: 4, md: 6 }} px={{ base: 6, md: 12 }}>
        <Flex
          direction={{ base: "column", md: "row" }}
          justify="space-between"
          align="center"
          maxW="100%"
          mx="auto"
          color="#737686"
          fontSize="sm"
          gap={{ base: 4, md: 0 }}
        >
          <Text order={{ base: 2, md: 1 }}>© 2026 IHUI Architect. -Aprende asi Enseña asi-</Text>
          <Flex gap="8" order={{ base: 1, md: 2 }}>
            <Link href="#" _hover={{ color: "#003597" }} transition="colors 0.2s">Privacy Policy</Link>
            <Link href="#" _hover={{ color: "#003597" }} transition="colors 0.2s">Terms of Service</Link>
            <Link href="#" _hover={{ color: "#003597" }} transition="colors 0.2s">Security</Link>
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}