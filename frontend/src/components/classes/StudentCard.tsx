import { Badge, Box, HStack, Text, VStack } from "@chakra-ui/react";

type Props = {
  student: {
    id: string;
    full_name: string;
    age?: number | null;
  };
  showHint?: boolean;
};

export default function StudentCard({ student, showHint }: Props) {
  return (
    <Box
      w="100%"
      bg="white"
      borderWidth="1px"
      borderColor="blackAlpha.100"
      borderRadius="xl"
      p={3}
      boxShadow="sm"
      cursor="grab"
      _hover={{ boxShadow: "md", transform: "translateY(-1px)" }}
      transition="all 0.15s ease"
      _active={{ cursor: "grabbing" }}
    >
      <VStack align="stretch" spacing={2}>
        <HStack justify="space-between" align="start">
          <Text fontWeight="semibold" lineHeight="1.1">
            {student.full_name}
          </Text>
          {typeof student.age === "number" && (
            <Badge borderRadius="md" px={2} py={0.5} colorScheme="purple">
              {student.age} años
            </Badge>
          )}
        </HStack>

        {showHint && (
          <Text fontSize="xs" color="blackAlpha.600">
            Arrastra para inscribir/mover
          </Text>
        )}
      </VStack>
    </Box>
  );
}