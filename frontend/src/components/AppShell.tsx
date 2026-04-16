import { useEffect, useState } from "react";
import {
  Badge,
  Box,
  Button,
  Drawer,
  DrawerBody,
  DrawerCloseButton,
  DrawerContent,
  DrawerHeader,
  DrawerOverlay,
  Flex,
  HStack,
  IconButton,
  Spacer,
  Text,
  VStack,
  Avatar,
  useDisclosure,
} from "@chakra-ui/react";
import { HamburgerIcon, ChevronLeftIcon } from "@chakra-ui/icons";
import { Link as RouterLink, Outlet, useLocation, useNavigate } from "react-router-dom";
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
  const { isOpen, onOpen, onClose } = useDisclosure();

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

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <VStack
      align={mobile ? "stretch" : "center"}
      spacing={mobile ? 4 : 8}
      display={mobile ? "flex" : "contents"}
    >
      {me?.role === "platform_admin" && (
        <>
          <NavItem
            to="/schools"
            label="Schools"
            onNavigate={mobile ? onClose : undefined}
          />

          <NavItem
            to="/playbook-pendientes"
            label="Pendientes de Playbook"
            showBadge
            onNavigate={mobile ? onClose : undefined}
          />
        </>
      )}

      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem
          to="/students"
          label="Students"
          onNavigate={mobile ? onClose : undefined}
        />
      )}

      {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem
          to="/admin/classes-board"
          label="Classes Board"
          onNavigate={mobile ? onClose : undefined}
        />
      )}

      {canSee(me?.role, ["platform_admin", "school_admin"]) && (
        <NavItem
          to="/admin/bulk-students"
          label="Bulk Students"
          onNavigate={mobile ? onClose : undefined}
        />
      )}
    </VStack>
  );

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

        {/* Mobile menu trigger */}
        <IconButton
          aria-label="Open menu"
          icon={<HamburgerIcon />}
          onClick={onOpen}
          display={{ base: "inline-flex", md: "none" }}
          variant="ghost"
          color="#191c1d"
          _hover={{ bg: "#f3f4f5" }}
        />
      </Flex>

      {/* Mobile Menu Drawer */}
      <Drawer isOpen={isOpen} placement="right" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent bg="#ffffff">
          <DrawerCloseButton color="#191c1d" />
          <DrawerHeader color="#003597" fontFamily="'Plus Jakarta Sans', sans-serif" fontWeight="extrabold">
            IHUI AI
          </DrawerHeader>

          <DrawerBody>
            <VStack align="stretch" spacing={8}>
              <Box p={4} bg="#f3f4f5" borderRadius="xl">
                <HStack mb={2}>
                  <Avatar size="sm" name={me?.email || "User"} />
                  <Box>
                    <Text fontWeight="bold" fontSize="sm" color="#191c1d">
                      {me?.email}
                    </Text>
                    <Text fontSize="xs" color="#737686" textTransform="capitalize">
                      {me?.role?.replace('_', ' ')}
                    </Text>
                  </Box>
                </HStack>
              </Box>

              <NavLinks mobile />

              <Button
                variant="outline"
                borderColor="#c3c5d7"
                color="#434654"
                mt={8}
                onClick={() => {
                  onClose();
                  signOut();
                }}
                _hover={{ bg: "#f3f4f5", color: "#003597" }}
              >
                Sign out
              </Button>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <Box p={{ base: 4, md: 8 }}>
        <Outlet />
      </Box>
    </Box>
  );
}

