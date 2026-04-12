import {
  Box,
  Button,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
} from "@chakra-ui/react";
import { Search } from "lucide-react";

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
  return (
    <Box
      bg="#ffffff"
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
              placeholder="Buscar alumno…"
              bg="#f8f9fa"
              border="1px solid rgba(195, 197, 215, 0.15)"
              borderRadius="xl"
              _focus={{ bg: "#ffffff", borderColor: "rgba(0, 53, 151, 0.3)", boxShadow: "0 0 0 1px rgba(0, 53, 151, 0.3)" }}
              _hover={{ bg: "#f3f4f5" }}
              fontFamily="'Manrope', sans-serif"
              color="#191c1d"
            />
          </InputGroup>
        </HStack>

        <HStack spacing={{ base: 4, md: 6 }} wrap="wrap">
          <HStack spacing={3}>
            <Text fontSize="sm" color="#434654" fontFamily="'Manrope', sans-serif">
              Modo:
            </Text>

            <HStack
              bg="#f3f4f5"
              borderRadius="full"
              p={1.5}
            >
              <Button
                size="sm"
                borderRadius="full"
                variant={mode === "add" ? "solid" : "ghost"}
                bg={mode === "add" ? "#ffffff" : "transparent"}
                color={mode === "add" ? "#003597" : "#737686"}
                boxShadow={mode === "add" ? "0px 2px 8px rgba(25, 28, 29, 0.06)" : "none"}
                _hover={{ bg: mode === "add" ? "#ffffff" : "rgba(195, 197, 215, 0.2)" }}
                onClick={() => onMode("add")}
                px={4}
                fontFamily="'Manrope', sans-serif"
              >
                Agregar
              </Button>
              <Button
                size="sm"
                borderRadius="full"
                variant={mode === "move" ? "solid" : "ghost"}
                bg={mode === "move" ? "#ffffff" : "transparent"}
                color={mode === "move" ? "#003597" : "#737686"}
                boxShadow={mode === "move" ? "0px 2px 8px rgba(25, 28, 29, 0.06)" : "none"}
                _hover={{ bg: mode === "move" ? "#ffffff" : "rgba(195, 197, 215, 0.2)" }}
                onClick={() => onMode("move")}
                px={4}
                fontFamily="'Manrope', sans-serif"
              >
                Mover
              </Button>
            </HStack>
          </HStack>

          <Button
            size="md"
            variant="outline"
            borderRadius="full"
            onClick={onRefresh}
            isLoading={isRefreshing}
            color="#003597"
            borderColor="rgba(0, 53, 151, 0.3)"
            _hover={{ bg: "#e8edff" }}
            fontFamily="'Manrope', sans-serif"
            px={6}
          >
            Refrescar
          </Button>
        </HStack>
      </HStack>
    </Box>
  );
}