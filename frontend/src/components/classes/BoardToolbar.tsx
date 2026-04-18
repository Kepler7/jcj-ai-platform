import {
  Box,
  Button,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
  useColorModeValue,
} from "@chakra-ui/react";
import { Search } from "lucide-react";
import { useTranslation } from "react-i18next";

type Props = {
  search: string;
  onSearch: (v: string) => void;
  mode: "add" | "move";
  onMode: (m: "add" | "move") => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
};

export default function BoardToolbar({
  search,
  onSearch,
  mode,
  onMode,
  onRefresh,
  isRefreshing,
}: Props) {
  const { t } = useTranslation();
  const panelBg = useColorModeValue("#ffffff", "gray.800");
  const inputBg = useColorModeValue("#f8f9fa", "whiteAlpha.50");
  const inputBorder = useColorModeValue("rgba(195, 197, 215, 0.15)", "whiteAlpha.100");
  const inputHover = useColorModeValue("#f3f4f5", "whiteAlpha.200");
  const inputFocusBorder = useColorModeValue("rgba(0, 53, 151, 0.3)", "blue.300");
  const textColor = useColorModeValue("#191c1d", "whiteAlpha.900");
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
        <HStack spacing={4} flex="1" minW={{ base: "100%", md: "360px" }}>
          <InputGroup size="lg">
            <InputLeftElement pointerEvents="none">
              <Search size={20} color="#737686" />
            </InputLeftElement>
            <Input
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              placeholder={t("classes_board_page.toolbar.search_placeholder")}
              bg={inputBg}
              border="1px solid"
              borderColor={inputBorder}
              borderRadius="xl"
              _focus={{ bg: panelBg, borderColor: inputFocusBorder, boxShadow: `0 0 0 1px ${inputFocusBorder}` }}
              _hover={{ bg: inputHover }}
              fontFamily="'Manrope', sans-serif"
              color={textColor}
            />
          </InputGroup>
        </HStack>

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
