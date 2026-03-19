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
      w="320px"
      minH="520px"
      borderRadius="2xl"
      borderWidth="1px"
      borderColor={isOver ? "blue.300" : "blackAlpha.100"}
      bg={isOver ? "blue.50" : "gray.50"}
      boxShadow="sm"
      overflow="hidden"
      transition="all 0.12s ease"
    >
      <Box px={4} pt={4} pb={3} bg="white" borderBottomWidth="1px" borderColor="blackAlpha.100">
        <HStack justify="space-between" align="center">
          <Heading size="sm">{name}</Heading>
          <Box
            px={2}
            py={0.5}
            borderRadius="full"
            bg="blackAlpha.100"
            fontSize="sm"
            fontWeight="semibold"
          >
            {count}
          </Box>
        </HStack>
        <Text fontSize="xs" color="blackAlpha.600" mt={1}>
          Arrastra alumnos aquí
        </Text>
      </Box>

      <VStack align="stretch" spacing={3} p={4}>
        {children}
      </VStack>
    </Box>
  );
}