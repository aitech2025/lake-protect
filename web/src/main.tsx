import "@fontsource/noto-sans/400.css";
import "@fontsource/noto-sans/600.css";
import "@fontsource/noto-sans/700.css";
import "@fontsource/noto-sans-telugu/400.css";
import "@fontsource/noto-sans-telugu/600.css";
import "@fontsource/noto-sans-telugu/700.css";
import "@fontsource/noto-nastaliq-urdu/400.css";
import "./styles.css";
import "./i18n";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AuthProvider } from "./auth";
import { DatasetProvider } from "./dataset";
import { DemoProvider } from "./demo";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <DemoProvider>
          <DatasetProvider>
            <App />
          </DatasetProvider>
        </DemoProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
);
