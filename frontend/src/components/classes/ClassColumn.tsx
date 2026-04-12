import { Box, HStack, Heading, Text, VStack } from "@chakra-ui/react";
import { useDroppable } from "@dnd-kit/core";

type Props = {
  classId: string;
  name: string;
  count: number;
  children: React.ReactNode;
};

export default function ClassColumn({ classId, name, count, children }: Props) {
  const { isOver, setNodeRef } = useDroppable({ id: classId });

  return (
    <Box
      ref={setNodeRef}
      minW="340px"
      w="340px"
      minH="600px"
      borderRadius="2rem"
      bg={isOver ? "#dbe1ff" : "#f3f4f5"} // Primary-fixed vs surface-container-low
      overflow="hidden"
      transition="all 0.2s ease"
    >
      <Box px={6} pt={6} pb={4}>
        <HStack justify="space-between" align="center" mb="1">
          <Heading size="md" fontFamily="'Plus Jakarta Sans', sans-serif" color="#191c1d">
            {name}
          </Heading>
          <Box
            px={3}
            py={1}
            borderRadius="full"
            bg="#e1e3e4"
            color="#434654"
            fontSize="sm"
            fontWeight="bold"
          >
            {count}
          </Box>
        </HStack>
        <Text fontSize="sm" color="#737686" fontFamily="'Manrope', sans-serif">
          Arrastra alumnos aquí
        </Text>
      </Box>

      <VStack align="stretch" spacing={4} p={6} pt={0}>
        {children}
      </VStack>
    </Box>
  );
}