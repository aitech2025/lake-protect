import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./en.json";
import te from "./te.json";
import ur from "./ur.json";

function savedLanguage(): string {
  try {
    return localStorage.getItem("lp.lang") ?? "en";
  } catch {
    return "en";
  }
}

i18n.use(initReactI18next).init({
  // Urdu covers the citizen portal only (D-062); the desk stays in English and Telugu.
  resources: { en: { translation: en }, te: { translation: te }, ur: { translation: ur } },
  lng: savedLanguage(),
  fallbackLng: "en",
  interpolation: { escapeValue: false },
});

i18n.on("languageChanged", (lng) => {
  document.documentElement.lang = lng;
  try {
    localStorage.setItem("lp.lang", lng);
  } catch {
    /* language choice is a convenience only */
  }
});
document.documentElement.lang = i18n.language;

export default i18n;
