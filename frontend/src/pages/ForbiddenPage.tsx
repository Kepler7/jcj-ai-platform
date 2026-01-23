import { Box, Heading, Text } from '@chakra-ui/react';

export default function ForbiddenPage() {
  return (
    <Box p="6">
      <Heading size="md">403 Forbidden</Heading>
      <Text mt="2">No tienes permisos para ver esta pantalla.</Text>
    </Box>
  );
}
