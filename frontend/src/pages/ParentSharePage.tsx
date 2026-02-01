import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Box,
  Container,
  Heading,
  Text,
  Spinner,
  Alert,
  AlertIcon,
  Card,
  CardHeader,
  CardBody,
  Stack,
  List,
  ListItem,
  Divider,
} from "@chakra-ui/react";

type SharePayload = {
  ai_report_id: string;
  student_id: string;
  report_id: string;
  created_at: string | null;
  parent_version: {
    summary?: string;
    signals_detected?: string[];
    recommendations?: { title?: string; steps?: string[]; when_to_use?: string }[];
    home_plan_7_days?: { day?: number; focus?: string; activity?: string; success_criteria?: string }[];
  };
};

const API_URL = import.meta.env.VITE_API_URL;

export default function ParentSharePage() {
  const { token } = useParams();
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<SharePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      if (!token) return;
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(`${API_URL}/v1/share-links/p/${token}`, {
          method: "GET",
        });

        if (!res.ok) {
          const t = await res.text();
          throw new Error(t || `HTTP ${res.status}`);
        }

        const json = (await res.json()) as SharePayload;
        setData(json);
      } catch (e: any) {
        setError(e?.message ?? "Error");
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  return (
    <Container maxW="container.md" py={8}>
      <Heading size="md" mb={2}>
        Apoyo para casa
      </Heading>
      <Text color="gray.600" mb={6}>
        Vista para padres/tutores (link seguro).
      </Text>

      {loading && (
        <Box display="flex" alignItems="center" gap={3}>
          <Spinner />
          <Text>Cargando…</Text>
        </Box>
      )}

      {error && (
        <Alert status="error">
          <AlertIcon />
          {error.includes("410") ? "Este link ya expiró o fue revocado." : error}
        </Alert>
      )}

      {!loading && !error && data && (
        <Stack spacing={4}>
          <Card>
            <CardHeader>
              <Heading size="sm">Resumen</Heading>
            </CardHeader>
            <CardBody>
              <Text>{data.parent_version?.summary ?? "—"}</Text>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <Heading size="sm">Señales observadas</Heading>
            </CardHeader>
            <CardBody>
              <List spacing={2}>
                {(data.parent_version?.signals_detected ?? []).map((s, i) => (
                  <ListItem key={i}>• {s}</ListItem>
                ))}
                {(data.parent_version?.signals_detected ?? []).length === 0 && <Text>—</Text>}
              </List>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <Heading size="sm">Recomendaciones</Heading>
            </CardHeader>
            <CardBody>
              <Stack spacing={3}>
                {(data.parent_version?.recommendations ?? []).map((r, idx) => (
                  <Box key={idx}>
                    <Text fontWeight="semibold">{r.title ?? "Recomendación"}</Text>
                    {r.when_to_use && (
                      <Text fontSize="sm" color="gray.600">
                        Cuándo: {r.when_to_use}
                      </Text>
                    )}
                    {(r.steps ?? []).length > 0 && (
                      <List mt={2} spacing={1}>
                        {(r.steps ?? []).map((st, j) => (
                          <ListItem key={j}>• {st}</ListItem>
                        ))}
                      </List>
                    )}
                    <Divider mt={3} />
                  </Box>
                ))}
                {(data.parent_version?.recommendations ?? []).length === 0 && <Text>—</Text>}
              </Stack>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <Heading size="sm">Plan de 7 días</Heading>
            </CardHeader>
            <CardBody>
              <Stack spacing={3}>
                {(data.parent_version?.home_plan_7_days ?? []).map((d, idx) => (
                  <Box key={idx}>
                    <Text fontWeight="semibold">Día {d.day ?? idx + 1}: {d.focus ?? ""}</Text>
                    {d.activity && <Text>Actividad: {d.activity}</Text>}
                    {d.success_criteria && (
                      <Text fontSize="sm" color="gray.600">
                        Criterio de éxito: {d.success_criteria}
                      </Text>
                    )}
                    <Divider mt={3} />
                  </Box>
                ))}
                {(data.parent_version?.home_plan_7_days ?? []).length === 0 && <Text>—</Text>}
              </Stack>
            </CardBody>
          </Card>

          <Text fontSize="sm" color="gray.500">
            Generado: {data.created_at ? new Date(data.created_at).toLocaleString() : "—"}
          </Text>
        </Stack>
      )}
    </Container>
  );
}
