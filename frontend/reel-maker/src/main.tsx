import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles/main.css";

ReactDOM.createRoot(document.getElementById("reel-maker-root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
