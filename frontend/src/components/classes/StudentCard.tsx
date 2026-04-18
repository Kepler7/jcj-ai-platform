import { Badge, Box, HStack, Text, VStack, useColorModeValue } from "@chakra-ui/react";
import { useTranslation } from "react-i18next";

type Props = {
  student: {
    id: string;
    full_name: string;
    age?: number | null;
  };
  showHint?: boolean;
};

export default function StudentCard({ student, showHint }: Props) {
  const { t } = useTranslation();
  const bg = useColorModeValue("#ffffff", "gray.700");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const badgeBg = useColorModeValue("#e8edff", "whiteAlpha.200");
  const badgeColor = useColorModeValue("#003597", "blue.200");
  const hintColor = useColorModeValue("#737686", "whiteAlpha.500");
  const shadowIdle = useColorModeValue("0px 4px 12px rgba(25, 28, 29, 0.04)", "0px 4px 12px rgba(0, 0, 0, 0.5)");
  const shadowHover = useColorModeValue("0px 12px 24px rgba(25, 28, 29, 0.08)", "0px 12px 24px rgba(0, 0, 0, 0.8)");

  return (
    <Box
      w="100%"
      bg={bg}
      borderRadius="xl"
      p={4}
      boxShadow={shadowIdle}
      cursor="grab"
      _hover={{ boxShadow: shadowHover, transform: "translateY(-2px)" }}
      transition="all 0.2s ease"
      _active={{ cursor: "grabbing", boxShadow: shadowIdle, transform: "scale(0.98)" }}
    >
      <VStack align="stretch" spacing={2}>
        <HStack justify="space-between" align="start">
          <Text fontWeight="semibold" lineHeight="1.2" color={textColor} fontFamily="'Manrope', sans-serif">
            {student.full_name}
          </Text>
          {typeof student.age === "number" && (
            <Badge borderRadius="md" px={2} py={0.5} bg={badgeBg} color={badgeColor} fontSize="xs">
              {t("classes_board_page.student_card.age", { age: student.age })}
            </Badge>
          )}
        </HStack>

        {showHint && (
          <Text fontSize="xs" color={hintColor} fontFamily="'Manrope', sans-serif">
            {t("classes_board_page.student_card.drag_hint")}
          </Text>
        )}
      </VStack>
    </Box>
  );
}
