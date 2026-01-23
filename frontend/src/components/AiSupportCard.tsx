import {
  Box,
  Heading,
  ListItem,
  OrderedList,
  Stack,
  Text,
  UnorderedList,
} from '@chakra-ui/react';

type Recommendation = {
  title: string;
  when_to_use?: string;
  steps?: string[];
};

type PlanDay = {
  day: number;
  focus: string;
  activity: string;
  success_criteria: string;
};

type Version = {
  summary: string;
  signals_detected: string[];
  recommendations: Recommendation[];
  classroom_plan_7_days?: PlanDay[];
  home_plan_7_days?: PlanDay[];
};

export function AiSupportCard({
  title,
  version,
}: {
  title: string;
  version: Version;
}) {
  const plan = version.classroom_plan_7_days ?? version.home_plan_7_days ?? [];

  return (
    <Box borderWidth="1px" borderRadius="lg" p="4">
      <Heading size="sm" mb="2">
        {title}
      </Heading>

      <Text mb="3">{version.summary}</Text>

      <Stack gap="4">
        <Box>
          <Text fontWeight="semibold" mb="1">
            Señales observadas
          </Text>
          <UnorderedList>
            {version.signals_detected?.map((s, idx) => (
              <ListItem key={idx}>{s}</ListItem>
            ))}
          </UnorderedList>
        </Box>

        <Box>
          <Text fontWeight="semibold" mb="2">
            Recomendaciones
          </Text>

          <Stack gap="3">
            {version.recommendations?.map((r, idx) => (
              <Box key={idx} borderWidth="1px" borderRadius="md" p="3">
                <Text fontWeight="bold">{r.title}</Text>

                {r.when_to_use && (
                  <Text fontSize="sm" opacity={0.85}>
                    Cuándo usar: {r.when_to_use}
                  </Text>
                )}

                {r.steps?.length ? (
                  <OrderedList mt="2">
                    {r.steps.map((st, i) => (
                      <ListItem key={i}>{st}</ListItem>
                    ))}
                  </OrderedList>
                ) : null}
              </Box>
            ))}
          </Stack>
        </Box>

        <Box>
          <Text fontWeight="semibold" mb="2">
            Plan 7 días
          </Text>

          <Stack gap="2">
            {plan.map((d, idx) => (
              <Box key={idx} borderWidth="1px" borderRadius="md" p="3">
                <Text fontWeight="bold">
                  Día {d.day}: {d.focus}
                </Text>
                <Text fontSize="sm">Actividad: {d.activity}</Text>
                <Text fontSize="sm" opacity={0.85}>
                  Criterio de éxito: {d.success_criteria}
                </Text>
              </Box>
            ))}
          </Stack>
        </Box>
      </Stack>
    </Box>
  );
}
