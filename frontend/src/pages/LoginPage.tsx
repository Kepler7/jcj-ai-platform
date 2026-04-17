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
  InputRightElement,
  Image,
  useColorModeValue
} from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../auth/AuthContext';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import { Mail, Lock, Eye, EyeOff } from 'lucide-react';

export default function LoginPage() {
  const { t } = useTranslation();
  const { signIn, refreshMe } = useAuth();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

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
  const footerText = useColorModeValue("#737686", "whiteAlpha.600");

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const t = await signIn(email.trim(), password);
      await refreshMe(t);
      navigate('/', { replace: true });
    } catch (err: any) {
      setError(err?.message ?? t('login.login_failed'));
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
        {/* Login Card */}
        <Box bg={cardBg} borderRadius="2rem" boxShadow="0px 24px 48px rgba(25,28,29,0.06)" overflow="hidden">
          <Box p={{ base: 10, md: 14 }}>
            {/* Brand Anchor */}
            <Flex direction="column" align="center" mb="4">
              <Image
                alt="IHUI Logo"
                h={{ base: 44, md: 48 }}
                w="auto"
                mb="2"
                objectFit="contain"
                src="/ihui_logo.png"
              />
              <Heading as="h1" fontSize="3xl" fontWeight="extrabold" letterSpacing="tight" color={textColor} mb="2" fontFamily="'Plus Jakarta Sans', sans-serif">
                {/* Empty text placeholder for future flexibility */}
              </Heading>
            </Flex>

            {/* Login Form */}
            <form onSubmit={onSubmit}>
              <Flex direction="column" gap="6">

                <Box>
                  <Text as="label" display="block" fontSize="sm" fontWeight="semibold" color={labelColor} ml="1" mb="2">
                    {t('login.email_label')}
                  </Text>
                  <InputGroup size="lg" className="group">
                    <InputLeftElement pointerEvents="none" color={iconColor} _groupFocusWithin={{ color: primaryColor }}>
                      <Mail size={20} />
                    </InputLeftElement>
                    <Input
                      placeholder={t('login.email_placeholder')}
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      bg={inputBg}
                      border="none"
                      borderRadius="xl"
                      color={textColor}
                      _placeholder={{ color: placeholderColor }}
                      _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: outerBg, outline: "none" }}
                      fontSize="sm"
                      fontWeight="medium"
                      px="4"
                      pl="12"
                      py="1"
                      autoComplete="email"
                    />
                  </InputGroup>
                </Box>

                <Box>
                  <Flex justify="space-between" align="center" px="1" mb="2">
                    <Text as="label" display="block" fontSize="sm" fontWeight="semibold" color={labelColor}>
                      Password
                    </Text>
                    <Link as={RouterLink} to="/forgot-password" fontSize="xs" fontWeight="bold" color={linkColor} _hover={{ color: primaryColor }}>
                      {t('login.forgot_password')}
                    </Link>
                  </Flex>
                  <InputGroup size="lg" className="group">
                    <InputLeftElement pointerEvents="none" color={iconColor} _groupFocusWithin={{ color: primaryColor }}>
                      <Lock size={20} />
                    </InputLeftElement>
                    <Input
                      placeholder={t('login.password_placeholder')}
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      bg={inputBg}
                      border="none"
                      borderRadius="xl"
                      color={textColor}
                      _placeholder={{ color: placeholderColor }}
                      _focus={{ ring: "2px", ringColor: "rgba(0,53,151,0.2)", bg: outerBg, outline: "none" }}
                      fontSize="sm"
                      fontWeight="medium"
                      px="4"
                      pl="12"
                      pr="12"
                      py="1"
                      autoComplete="current-password"
                    />
                    <InputRightElement width="3rem" color={iconColor} _hover={{ color: textColor }} cursor="pointer" onClick={() => setShowPassword(!showPassword)}>
                      {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                    </InputRightElement>
                  </InputGroup>
                </Box>

                {error && (
                  <Text color={errorText} fontSize="sm" mt="2" textAlign="center" fontWeight="bold">
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
                    Sign in
                  </Button>
                </Box>
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
