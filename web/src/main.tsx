import "@fontsource/ibm-plex-sans/400.css";
import "@fontsource/ibm-plex-sans/500.css";
import "@fontsource/ibm-plex-sans/600.css";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource/noto-sans-telugu/400.css";
import "@fontsource/noto-sans-telugu/500.css";
import "@fontsource/noto-sans-telugu/600.css";
import "./styles.css";
import "./i18n";
import { applyTheme, savedTheme } from "./theme";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { MotionConfig } from "motion/react";
import { App } from "./App";
import { AuthProvider } from "./auth";

applyTheme(savedTheme());

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <MotionConfig reducedMotion="user">
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </MotionConfig>
  </StrictMode>,
);
