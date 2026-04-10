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
  Link,
  Spacer,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";
import { HamburgerIcon } from "@chakra-ui/icons";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
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
        px={3}
        py={2}
        borderRadius="md"
        bg={active ? "blue.50" : "transparent"}
        color={active ? "blue.700" : "inherit"}
        fontWeight={active ? "semibold" : "normal"}
        borderWidth={active ? "1px" : "1px"}
        borderColor={active ? "blue.200" : "transparent"}
        _hover={{
          textDecoration: "none",
          bg: active ? "blue.50" : "gray.50",
        }}
        onClick={onNavigate}
        align="center"
      >
        <Text>{label}</Text>
        {showBadge && pendingCount > 0 && (
          <Badge colorScheme="red" borderRadius="full" px={2}>
            {pendingCount}
          </Badge>
        )}
      </HStack>
    );
  };

  const NavLinks = ({ mobile = false }: { mobile?: boolean }) => (
    <VStack
      align={mobile ? "stretch" : "center"}
      spacing={mobile ? 2 : 0}
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
    <Box minH="100vh">
      <Flex px="6" py="4" borderBottomWidth="1px" align="center" gap={4}>
        <Text fontWeight="bold">IHUI AI</Text>

        <Flex
          ml="6"
          gap="2"
          align="center"
          wrap="wrap"
          display={{ base: "none", md: "flex" }}
        >
          <NavLinks />
        </Flex>

        <Spacer />

        <HStack display={{ base: "none", md: "flex" }} spacing={4}>
          <Text fontSize="sm">
            {me?.email} ({me?.role})
          </Text>

          <Button size="sm" onClick={signOut}>
            Sign out
          </Button>
        </HStack>

        <IconButton
          aria-label="Open menu"
          icon={<HamburgerIcon />}
          onClick={onOpen}
          display={{ base: "inline-flex", md: "none" }}
          variant="outline"
        />
      </Flex>

      <Drawer isOpen={isOpen} placement="right" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerCloseButton />
          <DrawerHeader>IHUI AI</DrawerHeader>

          <DrawerBody>
            <VStack align="stretch" spacing={6}>
              <Box>
                <Text fontSize="sm" color="gray.600">
                  Usuario
                </Text>
                <Text fontWeight="medium">{me?.email}</Text>
                <Text fontSize="sm" color="gray.600">
                  {me?.role}
                </Text>
              </Box>

              <NavLinks mobile />

              <Button
                size="sm"
                onClick={() => {
                  onClose();
                  signOut();
                }}
              >
                Sign out
              </Button>
            </VStack>
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      <Box p="6">
        <Outlet />
      </Box>
    </Box>
  );
}

