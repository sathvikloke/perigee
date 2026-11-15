import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
// Styling layer: tokens.css holds every visual value; app.css only references
// tokens. Codex's design/HANDOFF.md replaces tokens.css (and refines app.css).
import "./styles/tokens.css";
import "./styles/app.css";
import "./styles/orbital.css";

createRoot(document.getElementById("root") as HTMLElement).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
