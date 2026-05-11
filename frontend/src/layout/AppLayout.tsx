import React from "react";
import {
  Box,
  Flex,
  HStack,
  IconButton,
  Text,
  Drawer,
  DrawerBody,
  DrawerContent,
  DrawerOverlay,
  useDisclosure,
  VStack,
  Button,
  Badge,
} from "@chakra-ui/react";
import { Outlet, NavLink, useNavigate } from "react-router-dom";
import { Menu, LogOut, Home, School, Users, FileText, Bot, LayoutGrid } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/apiClient";
import { useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

function NavItem({
  to,
  icon,
  label,
  onClick,
  right,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
  right?: React.ReactNode;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      style={() => ({
        width: "100%",
        textDecoration: "none",
      })}
    >
      {({ isActive }) => (
        <HStack
          w="100%"
          px="3"
          py="2"
          borderRadius="md"
          bg={isActive ? "gray.100" : "transparent"}
          _hover={{ bg: "gray.50" }}
          gap="3"
          justify="space-between"
        >
          <HStack gap="3">
            <Box>{icon}</Box>
            <Text fontSize="sm" fontWeight={isActive ? "semibold" : "normal"}>
              {label}
            </Text>
          </HStack>
          {right}
        </HStack>
      )}
    </NavLink>
  );
}

const canSee = (role: string | undefined, allowed: string[]) =>
  !!role && allowed.includes(role);

function SidebarContent({
  role,
  pendingCount,
  onNavigate,
}: {
  role?: string;
  pendingCount: number;
  onNavigate?: () => void;
}) {
  const { t } = useTranslation();

  return (
    <VStack align="stretch" gap="1">
      <NavItem to="/" icon={<Home size={18} />} label={t("nav.dashboard")} onClick={onNavigate} />

      {canSee(role, ["platform_admin"]) && (
        <NavItem to="/schools" icon={<School size={18} />} label={t("nav.schools")} onClick={onNavigate} />
      )}

      {canSee(role, ["platform_admin"]) && (
        <NavItem
          to="/playbook-pendientes"
          icon={<Bot size={18} />}
          label={t("nav.playbook_pendientes")}
          onClick={onNavigate}
          right={
            pendingCount > 0 ? (
              <Badge colorScheme="red" borderRadius="full" px={2}>
                {pendingCount}
              </Badge>
            ) : undefined
          }
        />
      )}

      {canSee(role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem to="/students" icon={<Users size={18} />} label={t("nav.students")} onClick={onNavigate} />
      )}

      {/* Nota: tu ruta de reportes actual es /students/:studentId/reports.
          Este link es genérico; lo dejamos si tienes una página /reports real.
          Si NO tienes /reports, quítalo para evitar 404. */}
      <NavItem to="/reports" icon={<FileText size={18} />} label={t("nav.reports")} onClick={onNavigate} />

      <NavItem to="/ai-jobs" icon={<Bot size={18} />} label={t("nav.ai_jobs")} onClick={onNavigate} />

      {/* NEW */}
      {canSee(role, ["platform_admin", "school_admin", "teacher"]) && (
        <NavItem
          to="/admin/classes-board"
          icon={<LayoutGrid size={18} />}
          label={t("nav.classes_board")}
          onClick={onNavigate}
        />
      )}

      {canSee(role, ["platform_admin", "school_admin"]) && (
        <NavItem
          to="/admin/bulk-students"
          icon={<Users size={18} />}
          label={t("nav.bulk_students")}
          onClick={onNavigate}
        />
      )}
    </VStack>
  );
}

export default function AppLayout() {
  const { t } = useTranslation();
  const { isOpen, onOpen, onClose } = useDisclosure();
  const navigate = useNavigate();
  const location = useLocation();

  const { token, me, signOut } = useAuth();

  const [pendingCount, setPendingCount] = React.useState<number>(0);

  const loadPendingCount = React.useCallback(async () => {
    if (me?.role !== "platform_admin") {
      setPendingCount(0);
      return;
    }

    try {
      const data = await api<any[]>(
        `/v1/playbook-fallbacks?status_filter=pending&limit=200`,
        { auth: true }
      );
      const cnt = Array.isArray(data) ? data.filter((r) => !r.resolved_at).length : 0;
      setPendingCount(cnt);
    } catch {
      setPendingCount(0);
    }
  }, [me?.role]);

  React.useEffect(() => {
    if (!token) navigate("/login");
  }, [token, navigate]);

  React.useEffect(() => {
    loadPendingCount();
  }, [loadPendingCount]);

  React.useEffect(() => {
    loadPendingCount();
  }, [location.pathname, loadPendingCount]);

  React.useEffect(() => {
    if (me?.role !== "platform_admin") return;

    const handler = () => loadPendingCount();
    window.addEventListener("playbook:pending-changed", handler);
    return () => window.removeEventListener("playbook:pending-changed", handler);
  }, [me?.role, loadPendingCount]);

  const logout = () => {
    signOut();
    navigate("/login");
  };

  return (
    <Flex minH="100vh">
      {/* Sidebar desktop */}
      <Box display={{ base: "none", md: "block" }} w="260px" borderRightWidth="1px" p="4">
        <Text fontWeight="bold" mb="4">
          JCJ AI Platform
        </Text>

        <SidebarContent role={me?.role} pendingCount={pendingCount} />
      </Box>

      {/* Drawer mobile */}
      <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerBody p="4">
            <Text fontWeight="bold" mb="4">
              JCJ AI Platform
            </Text>
            <SidebarContent
              role={me?.role}
              pendingCount={pendingCount}
              onNavigate={onClose}
            />
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Main */}
      <Flex direction="column" flex="1">
        {/* Header */}
        <HStack justify="space-between" borderBottomWidth="1px" px={{ base: 3, md: 6 }} py="3">
          <HStack gap="2">
            <IconButton
              aria-label={t("shell.menu")}
              display={{ base: "inline-flex", md: "none" }}
              onClick={onOpen}
              variant="outline"
              size="sm"
              icon={<Menu size={18} />}
            />
            <Text fontWeight="semibold">{t("shell.panel")}</Text>
          </HStack>

          <Text fontSize="sm" opacity={0.8}>
            {me?.email} · {me?.role}
          </Text>

          <Button size="sm" variant="outline" leftIcon={<LogOut size={16} />} onClick={logout}>
            {t("shell.sign_out")}
          </Button>
        </HStack>

        {/* Content */}
        <Box p={{ base: 4, md: 6 }}>
          <Outlet />
        </Box>
      </Flex>
    </Flex>
  );
}
