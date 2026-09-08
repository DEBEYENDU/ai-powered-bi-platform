import { createContext, useContext, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { createTheme, ThemeProvider, CssBaseline } from "@mui/material";

const ColorModeContext = createContext({ toggle: () => {}, mode: "light" as string });

export function useColorMode() {
  return useContext(ColorModeContext);
}

export function AppTheme({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<"light" | "dark">("light");
  const value = useMemo(
    () => ({
      toggle: () => setMode((m) => (m === "light" ? "dark" : "light")),
      mode,
    }),
    [mode]
  );
  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode,
          primary: { main: "#1e3a5f" },
          secondary: { main: "#0288d1" },
        },
      }),
    [mode]
  );
  return (
    <ColorModeContext.Provider value={value}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ColorModeContext.Provider>
  );
}
