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
} from "@chakra-ui/react";
import { ChevronLeftIcon } from "@chakra-ui/icons";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { School, Bot, Users, LayoutGrid, Database, LogOut } from "lucide-react";
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
  const { me, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [pendingCount, setPendingCount] = useState<number>(0);

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
        color={active ? "#003597" : "#737686"}
        fontWeight={active ? "bold" : "semibold"}
        _hover={{
          textDecoration: "none",
          color: "#003597",
        }}
        onClick={onNavigate}
        align="center"
      >
        <Text fontSize="sm" fontFamily="'Manrope', sans-serif">{label}</Text>
        {showBadge && pendingCount > 0 && (
          <Badge bg="#ba1a1a" color="white" borderRadius="full" px={2} fontSize="xs">
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
            bg="#003597" 
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
          <NavItem to="/schools" label="Schools" />
          <NavItem to="/playbook-pendientes" label="Pendientes de Playbook" showBadge />
        </>
      )}
      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem to="/students" label="Students" />
      )}
      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem to="/admin/classes-board" label="Classes Board" />
      )}
      {canSee(me?.role, ["platform_admin", "school_admin"]) && (
        <NavItem to="/admin/bulk-students" label="Bulk Students" />
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
        color={active ? "#003597" : "#737686"}
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
              bg="#ba1a1a" color="white" 
              position="absolute" top="-4px" right="-12px" 
              borderRadius="full" fontSize="9px" 
              px={1.5} minW="16px" textAlign="center"
              border="2px solid #ffffff"
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
    <Box minH="100vh" bg="#f8f9fa" fontFamily="'Manrope', sans-serif">
      <Flex 
        px={{ base: 4, md: 8 }} 
        py="4" 
        align="center" 
        bg="#ffffff" 
        borderBottomWidth="1px" 
        borderColor="#e1e3e4"
        position="sticky"
        top="0"
        zIndex="100"
      >
        <IconButton
          aria-label="Ir atrás"
          icon={<ChevronLeftIcon boxSize={6} />}
          variant="ghost"
          onClick={() => navigate(-1)}
          mr={3}
          ml={-2}
          color="#191c1d"
          _hover={{ bg: "#f3f4f5", color: "#003597" }}
          size="sm"
          borderRadius="full"
        />
        {/* IHUI Logo Mark */}
        <Text 
          fontWeight="extrabold" 
          fontSize="xl" 
          color="#003597" 
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
            <Avatar size="sm" name={me?.email || "User"} src="" bg="#c3c5d7" color="#191c1d" />
            <Text 
              fontSize="sm" 
              fontWeight="semibold" 
              color="#434654" 
              cursor="pointer" 
              _hover={{ color: "#003597" }}
              onClick={signOut}
              transition="colors 0.2s"
            >
              Sign out
            </Text>
          </HStack>
        </HStack>

        {/* Mobile Sign out */}
        <IconButton
          aria-label="Sign out"
          icon={<LogOut size={20} />}
          onClick={signOut}
          display={{ base: "inline-flex", md: "none" }}
          variant="ghost"
          color="#434654"
          _hover={{ bg: "#f3f4f5", color: "#003597" }}
        />
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
        bg="#ffffff"
        borderTopWidth="1px"
        borderColor="rgba(195, 197, 215, 0.4)"
        pb="env(safe-area-inset-bottom, 0px)"
        justify="space-between"
        align="center"
        zIndex="100"
        boxShadow="0px -4px 16px rgba(25, 28, 29, 0.04)"
      >
        <BottomNavItem to="/schools" icon={<School size={20} />} label="Schools" roleAllowed={["platform_admin"]} />
        <BottomNavItem to="/playbook-pendientes" icon={<Bot size={20} />} label="Playbook" showBadge roleAllowed={["platform_admin"]} />
        <BottomNavItem to="/students" icon={<Users size={20} />} label="Students" roleAllowed={["platform_admin", "school_admin", "teacher"]} />
        <BottomNavItem to="/admin/classes-board" icon={<LayoutGrid size={20} />} label="Board" roleAllowed={["platform_admin", "school_admin", "teacher"]} />
        <BottomNavItem to="/admin/bulk-students" icon={<Database size={20} />} label="Bulk" roleAllowed={["platform_admin", "school_admin"]} />
      </Flex>
    </Box>
  );
}

