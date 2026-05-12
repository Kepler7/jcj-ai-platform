import { useMemo, useState } from 'react';
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
  InputRightElement,
  Image,
  useColorModeValue,
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { Link as RouterLink, useSearchParams, useNavigate } from 'react-router-dom';
import { Lock, Eye, EyeOff, ArrowLeft } from 'lucide-react';
const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

console.log('API_BASE:', API_BASE);

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const navigate = useNavigate();

  const token = useMemo(() => params.get('token') ?? '', [params]);

  const [newPassword, setNewPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const tokenMissing = !token;

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setStatusMsg(null);

    if (tokenMissing) {
      setError(t('reset_password.missing_token_submit'));
      return;
    }

    if (newPassword.length < 8) {
      setError(t('reset_password.password_min'));
      return;
    }

    if (newPassword !== confirm) {
      setError(t('reset_password.passwords_mismatch'));
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/v1/auth/reset-password`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ token, new_password: newPassword }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        throw new Error(data?.detail ?? t('reset_password.reset_failed'));
      }

      setStatusMsg(t('reset_password.success_msg'));
      setTimeout(() => navigate('/login', { replace: true }), 800);
    } catch (err: any) {
      setError(err?.message ?? t('reset_password.reset_failed'));
    } finally {
      setLoading(false);
    }
  }

  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  const outerBg = useColorModeValue("#f8f9fa", "gray.900");
  const cardBg = useColorModeValue("#ffffff", "gray.800");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const labelColor = useColorModeValue("#434654", "gray.400");
  const inputBg = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const placeholderColor = useColorModeValue("#737686", "whiteAlpha.500");
  const iconColor = useColorModeValue("#c3c5d7", "whiteAlpha.400");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const linkColor = useColorModeValue("#0c50d6", "blue.300");
  const errorText = useColorModeValue("#ba1a1a", "red.300");
  const errorBg = useColorModeValue("#ffdad6", "red.900");
  const successText = useColorModeValue("#006142", "green.300");
  const successBg = useColorModeValue("#e8f5e9", "green.900");
  const footerText = useColorModeValue("#737686", "whiteAlpha.600");

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
      bg={outerBg}
      color={textColor}
      overflow="hidden"
      fontFamily="'Manrope', sans-serif"
      transition="background-color 0.2s"
    >
      {/* Abstract Background Elements */}
      <Box position="absolute" top="-10%" right="-10%" w={{ base: "300px", md: "500px" }} h={{ base: "300px", md: "500px" }} borderRadius="full" bg="rgba(0,53,151,0.05)" filter="blur(120px)" />
      <Box position="absolute" bottom="-10%" left="-10%" w={{ base: "250px", md: "400px" }} h={{ base: "250px", md: "400px" }} borderRadius="full" bg="rgba(0,71,47,0.05)" filter="blur(100px)" />

      <Box w="full" maxW="480px" zIndex="10">
        <Box bg={cardBg} borderRadius="2rem" boxShadow="0px 24px 48px rgba(25,28,29,0.06)" overflow="hidden">
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
              <Heading as="h1" fontSize="2xl" fontWeight="extrabold" letterSpacing="tight" color={textColor} mb="2" fontFamily="'Plus Jakarta Sans', sans-serif">
                {t('reset_password.title')}
              </Heading>
              {!tokenMissing && (
                <Text fontSize="sm" color={labelColor} textAlign="center" px="4">
                  {t('reset_password.desc')}
                </Text>
              )}
            </Flex>

            {tokenMissing && (
              <Box mb="6">
                <Text color={errorText} bg={errorBg} p="4" borderRadius="xl" fontSize="sm" textAlign="center" fontWeight="bold">
                  {t('reset_password.missing_token_open_link')}
                </Text>
              </Box>
            )}

            <form onSubmit={onSubmit}>
              <Flex direction="column" gap="5">

                <Box>
                  <Text as="label" display="block" fontSize="sm" fontWeight="semibold" color={labelColor} ml="1" mb="2">
                    {t('reset_password.new_password_label')}
                  </Text>
                  <InputGroup size="lg" className="group">
                    <InputLeftElement pointerEvents="none" color={iconColor} _groupFocusWithin={{ color: primaryColor }}>
                      <Lock size={20} />
                    </InputLeftElement>
                    <Input
                      placeholder="••••••••"
                      type={showNewPassword ? 'text' : 'password'}
                      value={newPassword}
                      onChange={(e) => setNewPassword(e.target.value)}
                      autoComplete="new-password"
                      bg={inputBg}
                      border="none"
                      borderRadius="xl"
                      color={textColor}
                      isDisabled={tokenMissing}
                      _placeholder={{ color: placeholderColor }}
                      _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: outerBg, outline: "none" }}
                      fontSize="sm"
                      fontWeight="medium"
                      px="4"
                      pl="12"
                      pr="12"
                      py="1"
                    />
                    <InputRightElement width="3rem" color={iconColor} _hover={{ color: textColor }} cursor="pointer" onClick={() => setShowNewPassword(!showNewPassword)}>
                      {showNewPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </InputRightElement>
                  </InputGroup>
                </Box>

                <Box>
                  <Text as="label" display="block" fontSize="sm" fontWeight="semibold" color={labelColor} ml="1" mb="2">
                    {t('reset_password.confirm_password_label')}
                  </Text>
                  <InputGroup size="lg" className="group">
                    <InputLeftElement pointerEvents="none" color={iconColor} _groupFocusWithin={{ color: primaryColor }}>
                      <Lock size={20} />
                    </InputLeftElement>
                    <Input
                      placeholder="••••••••"
                      type={showConfirmPassword ? 'text' : 'password'}
                      value={confirm}
                      onChange={(e) => setConfirm(e.target.value)}
                      autoComplete="new-password"
                      bg={inputBg}
                      border="none"
                      borderRadius="xl"
                      color={textColor}
                      isDisabled={tokenMissing}
                      _placeholder={{ color: placeholderColor }}
                      _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: outerBg, outline: "none" }}
                      fontSize="sm"
                      fontWeight="medium"
                      px="4"
                      pl="12"
                      pr="12"
                      py="1"
                    />
                    <InputRightElement width="3rem" color={iconColor} _hover={{ color: textColor }} cursor="pointer" onClick={() => setShowConfirmPassword(!showConfirmPassword)}>
                      {showConfirmPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </InputRightElement>
                  </InputGroup>
                </Box>

                {statusMsg && (
                  <Text color={successText} bg={successBg} p="3" borderRadius="xl" fontSize="sm" textAlign="center" fontWeight="bold">
                    {statusMsg}
                  </Text>
                )}
                {error && (
                  <Text color={errorText} bg={errorBg} p="3" borderRadius="xl" fontSize="sm" textAlign="center" fontWeight="bold">
                    {error}
                  </Text>
                )}

                <Box pt="2">
                  <Button
                    type="submit"
                    isLoading={loading}
                    isDisabled={tokenMissing}
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
                    {t('reset_password.reset_button')}
                  </Button>
                </Box>

                <Flex justify="center" align="center" mt="4">
                  <Link as={RouterLink} to="/login" fontSize="sm" fontWeight="bold" color={linkColor} _hover={{ color: primaryColor }} display="flex" alignItems="center" gap="2">
                    <ArrowLeft size={16} /> {t('forgot_password.back_to_login')}
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
          color={footerText}
          fontSize="sm"
          gap={{ base: 4, md: 0 }}
        >
          <Text order={{ base: 2, md: 1 }}>{t('login.footer')}</Text>
          <Flex gap="8" order={{ base: 1, md: 2 }}>
            <Link href="#" _hover={{ color: primaryColor }} transition="colors 0.2s">{t('login.privacy')}</Link>
            <Link href="#" _hover={{ color: primaryColor }} transition="colors 0.2s">{t('login.terms')}</Link>
            <Link href="#" _hover={{ color: primaryColor }} transition="colors 0.2s">{t('login.security')}</Link>
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}
