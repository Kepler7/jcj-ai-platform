import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

import esTranslation from '../locales/es.json';
import enTranslation from '../locales/en.json';

const resources = {
  es: esTranslation,
  en: enTranslation
};

i18n
  // Detecta lenguaje desde el navegador o local storage
  .use(LanguageDetector)
  // Pasa i18n a react-i18next
  .use(initReactI18next)
  // Configuración de inicialización
  .init({
    resources,
    fallbackLng: 'es',
    interpolation: {
      escapeValue: false // React ya hace validación segura (XSS escape)
    }
  });

export default i18n;
