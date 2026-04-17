import { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Flex,
  HStack,
  IconButton,
  Spacer,
  Text,
  VStack,
  Avatar,
  useColorMode,
  useColorModeValue,
  Menu,
  MenuButton,
  MenuList,
  MenuItem,
  Button,
} from "@chakra-ui/react";
import { useTranslation } from "react-i18next";
import { ChevronLeftIcon } from "@chakra-ui/icons";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { School, Bot, Users, LayoutGrid, Database, LogOut, Sun, Moon } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/apiClient";

const canSee = (role: string | undefined, allowed: string[]) =>
  !!role && allowed.includes(role);

type PlaybookFallbackEvent = {
  id: string;
  report_id: string;
  resolved_at: string | null;
};

type AIPrediction = {
  id: string;
  report_id: string;
  resolved_by_human: boolean;
};

function isActivePath(currentPath: string, targetPath: string) {
  if (targetPath === "/") return currentPath === "/";
  return currentPath === targetPath || currentPath.startsWith(`${targetPath}/`);
}

export default function AppShell() {
  const { t, i18n } = useTranslation();
  const { me, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [pendingCount, setPendingCount] = useState<number>(0);

  const { colorMode, toggleColorMode } = useColorMode();
  const bg = useColorModeValue("#f8f9fa", "gray.900");
  const headerBg = useColorModeValue("#ffffff", "gray.800");
  const borderColor = useColorModeValue("#e1e3e4", "whiteAlpha.200");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.600");
  const primaryColor = useColorModeValue("#003597", "blue.300");

  async function loadPendingCount() {
    if (me?.role !== "platform_admin") {
      setPendingCount(0);
      return;
    }

    try {
      const fallbackRows = await api<PlaybookFallbackEvent[]>(
        `/v1/playbook-fallbacks?status_filter=pending&limit=200`,
        { auth: true }
      );

      const fallbackPending = Array.isArray(fallbackRows)
        ? fallbackRows.filter((r) => !r.resolved_at)
        : [];

      const predictions = await api<AIPrediction[]>(
        `/v1/ai-feedback/pending?limit=200`,
        { auth: true }
      );

      const fallbackReportIds = new Set(fallbackPending.map((r) => r.report_id));

      const predictionPending = Array.isArray(predictions)
        ? predictions.filter((p) => !fallbackReportIds.has(p.report_id))
        : [];

      setPendingCount(fallbackPending.length + predictionPending.length);
    } catch {
      setPendingCount(0);
    }
  }

  useEffect(() => {
    loadPendingCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  useEffect(() => {
    loadPendingCount();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.pathname]);

  useEffect(() => {
    if (me?.role !== "platform_admin") return;

    const handler = () => {
      loadPendingCount();
    };

    window.addEventListener("playbook:pending-changed", handler);
    return () => {
      window.removeEventListener("playbook:pending-changed", handler);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [me?.role]);

  const NavItem = ({
    to,
    label,
    showBadge = false,
    onNavigate,
  }: {
    to: string;
    label: string;
    showBadge?: boolean;
    onNavigate?: () => void;
  }) => {
    const active = isActivePath(location.pathname, to);

    return (
      <HStack
        as={RouterLink}
        to={to}
        spacing={2}
        px={1}
        py={2}
        position="relative"
        color={active ? primaryColor : textMuted}
        fontWeight={active ? "bold" : "semibold"}
        _hover={{
          textDecoration: "none",
          color: primaryColor,
        }}
        onClick={onNavigate}
        align="center"
      >
        <Text fontSize="sm" fontFamily="'Manrope', sans-serif">{label}</Text>
        {showBadge && pendingCount > 0 && (
          <Badge bg="red.500" color="white" borderRadius="full" px={2} fontSize="xs">
            {pendingCount}
          </Badge>
        )}
        {active && (
          <Box 
            position="absolute" 
            bottom="-4px" 
            left="0" 
            w="full" 
            h="2px" 
            bg={primaryColor} 
            borderRadius="full"
          />
        )}
      </HStack>
    );
  };

  const NavLinks = () => (
    <VStack align="center" spacing={8} display="contents">
      {me?.role === "platform_admin" && (
        <>
          <NavItem to="/schools" label={t("nav.schools")} />
          <NavItem to="/playbook-pendientes" label={t("nav.playbook_pendientes")} showBadge />
        </>
      )}
      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem to="/students" label={t("nav.students")} />
      )}
      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem to="/admin/classes-board" label={t("nav.classes_board")} />
      )}
      {canSee(me?.role, ["platform_admin", "school_admin"]) && (
        <NavItem to="/admin/bulk-students" label={t("nav.bulk_students")} />
      )}
    </VStack>
  );

  const BottomNavItem = ({ to, icon, label, showBadge, roleAllowed }: any) => {
    if (!canSee(me?.role, roleAllowed)) return null;
    const active = isActivePath(location.pathname, to);

    return (
      <VStack
        as={RouterLink}
        to={to}
        spacing={1}
        color={active ? primaryColor : textMuted}
        _hover={{ textDecoration: "none" }}
        position="relative"
        flex="1"
        py={2}
        align="center"
        justify="center"
      >
        <Box position="relative">
          {icon}
          {showBadge && pendingCount > 0 && (
            <Badge 
              bg="red.500" color="white" 
              position="absolute" top="-4px" right="-12px" 
              borderRadius="full" fontSize="9px" 
              px={1.5} minW="16px" textAlign="center"
              border="2px solid"
              borderColor={headerBg}
            >
              {pendingCount > 99 ? '99+' : pendingCount}
            </Badge>
          )}
        </Box>
        <Text fontSize="10px" fontWeight={active ? "bold" : "semibold"} fontFamily="'Manrope', sans-serif" textAlign="center" lineHeight="shorter">
          {label}
        </Text>
      </VStack>
    );
  };

  return (
    <Box minH="100vh" bg={bg} fontFamily="'Manrope', sans-serif" transition="background-color 0.2s">
      <Flex 
        px={{ base: 4, md: 8 }} 
        py="4" 
        align="center" 
        bg={headerBg} 
        borderBottomWidth="1px" 
        borderColor={borderColor}
        position="sticky"
        top="0"
        zIndex="100"
        transition="all 0.2s"
      >
        <IconButton
          aria-label="Ir atrás"
          icon={<ChevronLeftIcon boxSize={6} />}
          variant="ghost"
          onClick={() => navigate(-1)}
          mr={3}
          ml={-2}
          color={textColor}
          _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100"), color: primaryColor }}
          size="sm"
          borderRadius="full"
        />
        {/* IHUI Logo Mark */}
        <Text 
          fontWeight="extrabold" 
          fontSize="xl" 
          color={primaryColor} 
          fontFamily="'Plus Jakarta Sans', sans-serif"
          letterSpacing="tight"
        >
          IHUI AI
        </Text>

        {/* Desktop Navigation Links */}
        <Flex
          ml={10}
          gap={8}
          align="center"
          display={{ base: "none", md: "flex" }}
        >
          <NavLinks />
        </Flex>

        <Spacer />

        {/* Desktop User Section */}
        <HStack display={{ base: "none", md: "flex" }} spacing={4}>
          <HStack spacing={3}>
            <Menu>
              <MenuButton as={Button} size="sm" variant="ghost" color={textMuted} fontWeight="bold" _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100"), color: primaryColor }} p={2} borderRadius="md" transition="all 0.2s">
                {i18n.language.toUpperCase().substring(0, 2)}
              </MenuButton>
              <MenuList minW="100px" bg={headerBg} borderColor={borderColor}>
                <MenuItem onClick={() => i18n.changeLanguage('es')} fontWeight={i18n.language.startsWith('es') ? "bold" : "normal"} _hover={{ bg: useColorModeValue("blackAlpha.50", "whiteAlpha.100") }} bg={headerBg}>Español</MenuItem>
                <MenuItem onClick={() => i18n.changeLanguage('en')} fontWeight={i18n.language.startsWith('en') ? "bold" : "normal"} _hover={{ bg: useColorModeValue("blackAlpha.50", "whiteAlpha.100") }} bg={headerBg}>English</MenuItem>
              </MenuList>
            </Menu>
            <IconButton
              aria-label={t("shell.toggle_dark_mode")}
              icon={colorMode === 'light' ? <Moon size={18} /> : <Sun size={18} />}
              onClick={toggleColorMode}
              variant="ghost"
              color={textColor}
              _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100") }}
              size="sm"
              borderRadius="full"
            />
            <Avatar size="sm" name={me?.email || "User"} src="" bg={useColorModeValue("#cbd5e1", "gray.600")} color={textColor} />
            <Text 
              fontSize="sm" 
              fontWeight="semibold" 
              color={textMuted} 
              cursor="pointer" 
              _hover={{ color: primaryColor }}
              onClick={signOut}
              transition="colors 0.2s"
            >
              {t("shell.sign_out")}
            </Text>
          </HStack>
        </HStack>

        {/* Mobile Top Actions */}
        <HStack display={{ base: "flex", md: "none" }} spacing={1}>
          <Menu>
            <MenuButton as={Button} size="sm" variant="ghost" color={textMuted} fontWeight="bold" _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100"), color: primaryColor }} p={2} borderRadius="md" transition="all 0.2s">
              {i18n.language.toUpperCase().substring(0, 2)}
            </MenuButton>
            <MenuList minW="100px" bg={headerBg} borderColor={borderColor}>
              <MenuItem onClick={() => i18n.changeLanguage('es')} fontWeight={i18n.language.startsWith('es') ? "bold" : "normal"} _hover={{ bg: useColorModeValue("blackAlpha.50", "whiteAlpha.100") }} bg={headerBg}>Español</MenuItem>
              <MenuItem onClick={() => i18n.changeLanguage('en')} fontWeight={i18n.language.startsWith('en') ? "bold" : "normal"} _hover={{ bg: useColorModeValue("blackAlpha.50", "whiteAlpha.100") }} bg={headerBg}>English</MenuItem>
            </MenuList>
          </Menu>
          <IconButton
            aria-label="Alternar Modo Oscuro"
            icon={colorMode === 'light' ? <Moon size={20} /> : <Sun size={20} />}
            onClick={toggleColorMode}
            variant="ghost"
            color={textMuted}
            _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100"), color: primaryColor }}
          />
          <IconButton
            aria-label="Sign out"
            icon={<LogOut size={20} />}
            onClick={signOut}
            variant="ghost"
            color={textMuted}
            _hover={{ bg: useColorModeValue("blackAlpha.100", "whiteAlpha.100"), color: primaryColor }}
          />
        </HStack>
      </Flex>

      <Box p={{ base: 4, md: 8 }} pb={{ base: 24, md: 8 }}>
        <Outlet />
      </Box>

      {/* Mobile Bottom Nav */}
      <Flex
        display={{ base: "flex", md: "none" }}
        position="fixed"
        bottom="0"
        left="0"
        right="0"
        bg={headerBg}
        borderTopWidth="1px"
        borderColor={borderColor}
        transition="all 0.2s"
        pb="env(safe-area-inset-bottom, 0px)"
        justify="space-between"
        align="center"
        zIndex="100"
        boxShadow="0px -4px 16px rgba(25, 28, 29, 0.04)"
      >
        <BottomNavItem to="/schools" icon={<School size={20} />} label={t("nav.schools")} roleAllowed={["platform_admin"]} />
        <BottomNavItem to="/playbook-pendientes" icon={<Bot size={20} />} label={t("nav.playbook")} showBadge roleAllowed={["platform_admin"]} />
        <BottomNavItem to="/students" icon={<Users size={20} />} label={t("nav.students")} roleAllowed={["platform_admin", "school_admin", "teacher"]} />
        <BottomNavItem to="/admin/classes-board" icon={<LayoutGrid size={20} />} label={t("nav.board")} roleAllowed={["platform_admin", "school_admin", "teacher"]} />
        <BottomNavItem to="/admin/bulk-students" icon={<Database size={20} />} label={t("nav.bulk")} roleAllowed={["platform_admin", "school_admin"]} />
      </Flex>
    </Box>
  );
}

