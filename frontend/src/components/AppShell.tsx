import { useEffect, useState } from "react";
import { Box, Button, Flex, Spacer, Text, Badge, HStack } from "@chakra-ui/react";
import { Link as RouterLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { api } from "../lib/apiClient";

const canSee = (role: string | undefined, allowed: string[]) =>
  !!role && allowed.includes(role);

export default function AppShell() {
  const { me, signOut } = useAuth();
  const location = useLocation();
  const [pendingCount, setPendingCount] = useState<number>(0);

  async function loadPendingCount() {
    // Solo platform_admin
    if (me?.role !== "platform_admin") return;

    try {
      // Si tu endpoint no trae total, contamos rows.
      const data = await api<any[]>(
        `/v1/playbook-fallbacks?status_filter=pending&limit=200`,
        { auth: true }
      );

      const cnt = Array.isArray(data)
        ? data.filter((r) => !r.resolved_at).length
        : 0;

      setPendingCount(cnt);
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

  return (
    <Box minH="100vh">
      <Flex px="6" py="4" borderBottomWidth="1px" align="center">
        <Text fontWeight="bold">IHUI AI</Text>

        <Flex ml="6" gap="4" align="center" wrap="wrap">
          {/* Platform admin links */}
          {me?.role === "platform_admin" && (
            <>
              <Text as={RouterLink} to="/schools">
                Schools
              </Text>

              <HStack as={RouterLink} to="/playbook-pendientes" spacing={2}>
                <Text>Pendientes de Playbook</Text>
                {pendingCount > 0 && (
                  <Badge colorScheme="red" borderRadius="full" px={2}>
                    {pendingCount}
                  </Badge>
                )}
              </HStack>
            </>
          )}

          {/* Shared */}
          {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
            <Text as={RouterLink} to="/students">
              Students
            </Text>
          )}

          {/* NEW: Classes Board */}
          {canSee(me?.role, ["platform_admin", "school_admin", "teacher"]) && (
            <Text as={RouterLink} to="/admin/classes-board">
              Classes Board
            </Text>
          )}

          {/* NEW: Bulk Students */}
          {canSee(me?.role, ["platform_admin", "school_admin"]) && (
            <Text as={RouterLink} to="/admin/bulk-students">
              Bulk Students
            </Text>
          )}
        </Flex>

        <Spacer />

        <Text fontSize="sm" mr="4">
          {me?.email} ({me?.role})
        </Text>

        <Button size="sm" onClick={signOut}>
          Sign out
        </Button>
      </Flex>

      <Box p="6">
        <Outlet />
      </Box>
    </Box>
  );
}

