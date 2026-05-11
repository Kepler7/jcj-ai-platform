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
import { useTranslation } from "react-i18next";

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
  const { t } = useTranslation();
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
        setError(e?.message ?? t("common.error"));
      } finally {
        setLoading(false);
      }
    })();
  }, [token]);

  return (
    <Container maxW="container.md" py={8}>
      <Heading size="md" mb={2}>
        {t("parent_share.title")}
      </Heading>
      <Text color="gray.600" mb={6}>
        {t("parent_share.subtitle")}
      </Text>

      {loading && (
        <Box display="flex" alignItems="center" gap={3}>
          <Spinner />
          <Text>{t("common.loading")}</Text>
        </Box>
      )}

      {error && (
        <Alert status="error">
          <AlertIcon />
          {error.includes("410") ? t("parent_share.expired_link") : error}
        </Alert>
      )}

      {!loading && !error && data && (
        <Stack spacing={4}>
          <Card>
            <CardHeader>
              <Heading size="sm">{t("parent_share.summary")}</Heading>
            </CardHeader>
            <CardBody>
              <Text>{data.parent_version?.summary ?? "—"}</Text>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <Heading size="sm">{t("parent_share.observed_signals")}</Heading>
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
              <Heading size="sm">{t("parent_share.recommendations")}</Heading>
            </CardHeader>
            <CardBody>
              <Stack spacing={3}>
                {(data.parent_version?.recommendations ?? []).map((r, idx) => (
                  <Box key={idx}>
                    <Text fontWeight="semibold">{r.title ?? t("parent_share.recommendation")}</Text>
                    {r.when_to_use && (
                      <Text fontSize="sm" color="gray.600">
                        {t("parent_share.when")} {r.when_to_use}
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
              <Heading size="sm">{t("parent_share.seven_day_plan")}</Heading>
            </CardHeader>
            <CardBody>
              <Stack spacing={3}>
                {(data.parent_version?.home_plan_7_days ?? []).map((d, idx) => (
                  <Box key={idx}>
                    <Text fontWeight="semibold">{t("parent_share.day", { day: d.day ?? idx + 1 })}: {d.focus ?? ""}</Text>
                    {d.activity && <Text>{t("parent_share.activity")} {d.activity}</Text>}
                    {d.success_criteria && (
                      <Text fontSize="sm" color="gray.600">
                        {t("parent_share.success_criteria")} {d.success_criteria}
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
            {t("parent_share.generated")} {data.created_at ? new Date(data.created_at).toLocaleString() : "—"}
          </Text>
        </Stack>
      )}
    </Container>
  );
}
