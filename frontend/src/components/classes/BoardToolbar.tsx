import {
  Box,
  Button,
  HStack,
  Input,
  InputGroup,
  InputLeftElement,
  Text,
} from "@chakra-ui/react";
import { SearchIcon } from "@chakra-ui/icons";

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
      bg="white"
      borderWidth="1px"
      borderColor="blackAlpha.100"
      borderRadius="2xl"
      p={4}
      boxShadow="sm"
    >
      <HStack justify="space-between" spacing={4} wrap="wrap">
        <HStack spacing={3} flex="1" minW="280px">
          <InputGroup>
            <InputLeftElement pointerEvents="none">
              <SearchIcon color="blackAlpha.500" />
            </InputLeftElement>
            <Input
              value={search}
              onChange={(e) => onSearch(e.target.value)}
              placeholder="Buscar alumno…"
              borderRadius="xl"
            />
          </InputGroup>
        </HStack>

        <HStack spacing={3}>
          <HStack spacing={2}>
            <Text fontSize="sm" color="blackAlpha.700">
              Modo:
            </Text>

            {/* Chakra no trae un segmented oficial; usamos botones simples */}
            <HStack
              bg="gray.50"
              borderWidth="1px"
              borderColor="blackAlpha.100"
              borderRadius="xl"
              p={1}
            >
              <Button
                size="sm"
                borderRadius="lg"
                variant={mode === "add" ? "solid" : "ghost"}
                colorScheme={mode === "add" ? "blue" : undefined}
                onClick={() => onMode("add")}
              >
                Agregar
              </Button>
              <Button
                size="sm"
                borderRadius="lg"
                variant={mode === "move" ? "solid" : "ghost"}
                colorScheme={mode === "move" ? "orange" : undefined}
                onClick={() => onMode("move")}
              >
                Mover
              </Button>
            </HStack>
          </HStack>

          <Button
            size="sm"
            variant="outline"
            borderRadius="xl"
            onClick={onRefresh}
            isLoading={isRefreshing}
          >
            Refrescar
          </Button>
        </HStack>
      </HStack>
    </Box>
  );
}