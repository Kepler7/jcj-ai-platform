import { extendTheme, type ThemeConfig } from '@chakra-ui/react';

const config: ThemeConfig = {
  initialColorMode: 'light',
  useSystemColorMode: false,
};

const theme = extendTheme({ 
  config,
  fonts: {
    heading: "'Plus Jakarta Sans', sans-serif",
    body: "'Manrope', sans-serif",
  }
});

export default theme;
