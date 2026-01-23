import { Box, Button, Flex, Spacer, Text } from '@chakra-ui/react';
import { Link as RouterLink, Outlet } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';

export default function AppShell() {
  const { me, signOut } = useAuth();

  return (
    <Box minH="100vh">
      <Flex px="6" py="4" borderBottomWidth="1px" align="center">
        <Text fontWeight="bold">JCJ AI Platform</Text>

        <Flex ml="6" gap="4">
          {me?.role === 'platform_admin' && (
            <Text as={RouterLink} to="/schools">
              Schools
            </Text>
          )}
          <Text as={RouterLink} to="/students">
            Students
          </Text>
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
