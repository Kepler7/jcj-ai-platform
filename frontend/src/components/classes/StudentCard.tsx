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
      bg="#ffffff"
      borderRadius="xl"
      p={4}
      boxShadow="0px 4px 12px rgba(25, 28, 29, 0.04)"
      cursor="grab"
      _hover={{ boxShadow: "0px 12px 24px rgba(25, 28, 29, 0.08)", transform: "translateY(-2px)" }}
      transition="all 0.2s ease"
      _active={{ cursor: "grabbing", boxShadow: "0px 4px 12px rgba(25, 28, 29, 0.04)", transform: "scale(0.98)" }}
    >
      <VStack align="stretch" spacing={2}>
        <HStack justify="space-between" align="start">
          <Text fontWeight="semibold" lineHeight="1.2" color="#191c1d" fontFamily="'Manrope', sans-serif">
            {student.full_name}
          </Text>
          {typeof student.age === "number" && (
            <Badge borderRadius="md" px={2} py={0.5} bg="#e8edff" color="#003597" fontSize="xs">
              {student.age} años
            </Badge>
          )}
        </HStack>

        {showHint && (
          <Text fontSize="xs" color="#737686" fontFamily="'Manrope', sans-serif">
            Arrastra para inscribir/mover
          </Text>
        )}
      </VStack>
    </Box>
  );
}