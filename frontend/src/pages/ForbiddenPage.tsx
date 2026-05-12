import { Box, Heading, Text } from '@chakra-ui/react';
import { useTranslation } from 'react-i18next';

export default function ForbiddenPage() {
  const { t } = useTranslation();

  return (
    <Box p="6">
      <Heading size="md">{t('forbidden.title')}</Heading>
      <Text mt="2">{t('forbidden.message')}</Text>
    </Box>
  );
}
