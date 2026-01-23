import React from 'react';
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
} from '@chakra-ui/react';
import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import { Menu, LogOut, Home, School, Users, FileText, Bot } from 'lucide-react';

import { useAuth } from '../auth/AuthContext';

function NavItem({
  to,
  icon,
  label,
  onClick,
}: {
  to: string;
  icon: React.ReactNode;
  label: string;
  onClick?: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      style={({ isActive }) => ({
        width: '100%',
        textDecoration: 'none',
      })}
    >
      {({ isActive }) => (
        <HStack
          w="100%"
          px="3"
          py="2"
          borderRadius="md"
          bg={isActive ? 'gray.100' : 'transparent'}
          _hover={{ bg: 'gray.50' }}
          gap="3"
        >
          <Box>{icon}</Box>
          <Text fontSize="sm" fontWeight={isActive ? 'semibold' : 'normal'}>
            {label}
          </Text>
        </HStack>
      )}
    </NavLink>
  );
}

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <VStack align="stretch" gap="1">
      <NavItem
        to="/"
        icon={<Home size={18} />}
        label="Dashboard"
        onClick={onNavigate}
      />
      <NavItem
        to="/schools"
        icon={<School size={18} />}
        label="Escuelas"
        onClick={onNavigate}
      />
      <NavItem
        to="/students"
        icon={<Users size={18} />}
        label="Alumnos"
        onClick={onNavigate}
      />
      <NavItem
        to="/reports"
        icon={<FileText size={18} />}
        label="Reportes"
        onClick={onNavigate}
      />
      <NavItem
        to="/ai-jobs"
        icon={<Bot size={18} />}
        label="Trabajos IA"
        onClick={onNavigate}
      />
    </VStack>
  );
}

export default function AppLayout() {
  const { isOpen, onOpen, onClose } = useDisclosure();
  const navigate = useNavigate();

  const { token, me, signOut } = useAuth();

  React.useEffect(() => {
    if (!token) navigate('/login');
  }, [token, navigate]);

  const logout = () => {
    signOut();
    navigate('/login');
  };

  return (
    <Flex minH="100vh">
      {/* Sidebar desktop */}
      <Box
        display={{ base: 'none', md: 'block' }}
        w="260px"
        borderRightWidth="1px"
        p="4"
      >
        <Text fontWeight="bold" mb="4">
          JCJ AI Platform
        </Text>
        <SidebarContent />
      </Box>

      {/* Drawer mobile */}
      <Drawer isOpen={isOpen} placement="left" onClose={onClose}>
        <DrawerOverlay />
        <DrawerContent>
          <DrawerBody p="4">
            <Text fontWeight="bold" mb="4">
              JCJ AI Platform
            </Text>
            <SidebarContent onNavigate={onClose} />
          </DrawerBody>
        </DrawerContent>
      </Drawer>

      {/* Main */}
      <Flex direction="column" flex="1">
        {/* Header */}
        <HStack
          justify="space-between"
          borderBottomWidth="1px"
          px={{ base: 3, md: 6 }}
          py="3"
        >
          <HStack gap="2">
            <IconButton
              aria-label="menu"
              display={{ base: 'inline-flex', md: 'none' }}
              onClick={onOpen}
              variant="outline"
              size="sm"
              icon={<Menu size={18} />}
            />
            <Text fontWeight="semibold">Panel</Text>
          </HStack>
          <Text fontSize="sm" opacity={0.8}>
            {me?.email} · {me?.role}
          </Text>

          <Button
            size="sm"
            variant="outline"
            leftIcon={<LogOut size={16} />}
            onClick={logout}
          >
            Salir
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
