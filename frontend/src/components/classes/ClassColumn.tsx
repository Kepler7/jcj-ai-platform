import { Box, HStack, Heading, Text, VStack, useColorModeValue } from "@chakra-ui/react";
import { useDroppable } from "@dnd-kit/core";

type Props = {
  classId: string;
  name: string;
  count: number;
  children: React.ReactNode;
};

export default function ClassColumn({ classId, name, count, children }: Props) {
  const { isOver, setNodeRef } = useDroppable({ id: classId });
  const bgIdle = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const bgOver = useColorModeValue("#dbe1ff", "blue.900");
  const headingColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const countBg = useColorModeValue("#e1e3e4", "whiteAlpha.200");
  const countColor = useColorModeValue("#434654", "whiteAlpha.800");
  const hintColor = useColorModeValue("#737686", "whiteAlpha.500");

  return (
    <Box
      ref={setNodeRef}
      minW="340px"
      w="340px"
      minH="600px"
      borderRadius="2rem"
      bg={isOver ? bgOver : bgIdle}
      overflow="hidden"
      transition="all 0.2s ease"
    >
      <Box px={6} pt={6} pb={4}>
        <HStack justify="space-between" align="center" mb="1">
          <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color={headingColor}>
            {name}
          </Heading>
          <Box
            px={3}
            py={1}
            borderRadius="full"
            bg={countBg}
            color={countColor}
            fontSize="sm"
            fontWeight="bold"
          >
            {count}
          </Box>
        </HStack>
        <Text fontSize="sm" color={hintColor} fontFamily="'Manrope', sans-serif">
          Arrastra alumnos aquí
        </Text>
      </Box>

      <VStack align="stretch" spacing={4} p={6} pt={0}>
        {children}
      </VStack>
    </Box>
  );
}