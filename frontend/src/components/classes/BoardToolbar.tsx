import {
  Box,
  Button,
  HStack,
  Text,
  useColorModeValue,
} from "@chakra-ui/react";
import { useTranslation } from "react-i18next";

type Props = {
  mode: "add" | "move";
  onMode: (m: "add" | "move") => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
};

export default function BoardToolbar({
  mode,
  onMode,
  onRefresh,
  isRefreshing,
}: Props) {
  const { t } = useTranslation();
  const panelBg = useColorModeValue("#ffffff", "gray.800");
  const inputFocusBorder = useColorModeValue("rgba(0, 53, 151, 0.3)", "blue.300");
  const textMuted = useColorModeValue("#737686", "whiteAlpha.600");
  const modeContainerBg = useColorModeValue("#f3f4f5", "whiteAlpha.100");
  const btnActiveBg = useColorModeValue("#ffffff", "gray.600");
  const primaryColor = useColorModeValue("#003597", "blue.300");
  const hoverActiveBtn = useColorModeValue("#ffffff", "gray.500");
  const hoverInactiveBtn = useColorModeValue("rgba(195, 197, 215, 0.2)", "whiteAlpha.200");

  return (
    <Box
      bg={panelBg}
      borderRadius="2rem"
      p={6}
      boxShadow="0px 12px 24px rgba(25, 28, 29, 0.04)"
    >
      <HStack justify="space-between" spacing={6} wrap="wrap">
        <Text
          flex="1"
          minW={{ base: "100%", md: "360px" }}
          color={textMuted}
          fontFamily="'Manrope', sans-serif"
          fontSize={{ base: "sm", md: "md" }}
        >
          {t("classes_board_page.toolbar.assignment_desc")}
        </Text>

        <HStack spacing={{ base: 4, md: 6 }} wrap="wrap">
          <HStack spacing={3}>
            <Text fontSize="sm" color={textMuted} fontFamily="'Manrope', sans-serif">
              {t("classes_board_page.toolbar.mode_label")}
            </Text>

            <HStack
              bg={modeContainerBg}
              borderRadius="full"
              p={1.5}
            >
              <Button
                size="sm"
                borderRadius="full"
                variant={mode === "add" ? "solid" : "ghost"}
                bg={mode === "add" ? btnActiveBg : "transparent"}
                color={mode === "add" ? primaryColor : textMuted}
                boxShadow={mode === "add" ? "0px 2px 8px rgba(25, 28, 29, 0.06)" : "none"}
                _hover={{ bg: mode === "add" ? hoverActiveBtn : hoverInactiveBtn }}
                onClick={() => onMode("add")}
                px={4}
                fontFamily="'Manrope', sans-serif"
              >
                {t("classes_board_page.toolbar.add")}
              </Button>
              <Button
                size="sm"
                borderRadius="full"
                variant={mode === "move" ? "solid" : "ghost"}
                bg={mode === "move" ? btnActiveBg : "transparent"}
                color={mode === "move" ? primaryColor : textMuted}
                boxShadow={mode === "move" ? "0px 2px 8px rgba(25, 28, 29, 0.06)" : "none"}
                _hover={{ bg: mode === "move" ? hoverActiveBtn : hoverInactiveBtn }}
                onClick={() => onMode("move")}
                px={4}
                fontFamily="'Manrope', sans-serif"
              >
                {t("classes_board_page.toolbar.move")}
              </Button>
            </HStack>
          </HStack>

          <Button
            size="md"
            variant="outline"
            borderRadius="full"
            onClick={onRefresh}
            isLoading={isRefreshing}
            color={primaryColor}
            borderColor={inputFocusBorder}
            _hover={{ bg: useColorModeValue("#e8edff", "whiteAlpha.200") }}
            fontFamily="'Manrope', sans-serif"
            px={6}
          >
            {t("classes_board_page.toolbar.refresh")}
          </Button>
        </HStack>
      </HStack>
    </Box>
  );
}
