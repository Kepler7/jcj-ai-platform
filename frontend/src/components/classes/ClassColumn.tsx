import { Badge, Box, HStack, Heading, Text, VStack, useColorModeValue } from "@chakra-ui/react";
import { useDroppable } from "@dnd-kit/core";
import { useTranslation } from "react-i18next";

type Props = {
  classId: string;
  name: string;
  count: number;
  teachers?: string[];
  children: React.ReactNode;
};

export default function ClassColumn({ classId, name, count, teachers = [], children }: Props) {
  const { t } = useTranslation();
  const { isOver, setNodeRef } = useDroppable({ id: classId });
  const bgIdle = useColorModeValue("#f3f4f5", "whiteAlpha.50");
  const bgOver = useColorModeValue("#dbe1ff", "blue.900");
  const headingColor = useColorModeValue("#191c1d", "whiteAlpha.900");
  const countBg = useColorModeValue("#e1e3e4", "whiteAlpha.200");
  const countColor = useColorModeValue("#434654", "whiteAlpha.800");
  const hintColor = useColorModeValue("#737686", "whiteAlpha.500");
  const teacherBg = useColorModeValue("#e8edff", "whiteAlpha.200");
  const teacherColor = useColorModeValue("#003597", "blue.200");

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
          {t("classes_board_page.class_column.drag_hint")}
        </Text>
        {teachers.length > 0 && (
          <HStack mt={3} spacing={2} wrap="wrap">
            {teachers.map((teacher) => (
              <Badge
                key={teacher}
                bg={teacherBg}
                color={teacherColor}
                borderRadius="full"
                px={3}
                py={1}
                textTransform="none"
                maxW="100%"
                whiteSpace="normal"
                wordBreak="break-word"
              >
                {teacher}
              </Badge>
            ))}
          </HStack>
        )}
      </Box>

      <VStack align="stretch" spacing={4} p={6} pt={0}>
        {children}
      </VStack>
    </Box>
  );
}
