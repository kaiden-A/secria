"use client";

import { Moon, Sun } from "lucide-react";
import { useEffect } from "react";

const STORAGE_KEY = "secria-theme";

type Theme = "light" | "dark";

function isTheme(value: string | null): value is Theme {
  return value === "light" || value === "dark";
}

function applyTheme(theme: Theme, persist: boolean): void {
  const root = document.documentElement;
  root.dataset.theme = theme;
  root.style.colorScheme = theme;
  if (persist) {
    try {
      localStorage.setItem(STORAGE_KEY, theme);
    } catch {
      // Private browsing can reject storage writes; the theme still applies.
    }
  }
}

function currentTheme(): Theme {
  return document.documentElement.dataset.theme === "dark" ? "dark" : "light";
}

export function ThemeToggle({ className }: { className?: string }) {
  function toggle() {
    applyTheme(currentTheme() === "dark" ? "light" : "dark", true);
  }

  return (
    <button
      type="button"
      className={`sc-theme-toggle${className ? ` ${className}` : ""}`}
      onClick={toggle}
      aria-label="Toggle dark mode"
      title="Toggle dark mode"
    >
      <Sun size={16} className="sc-theme-sun" aria-hidden="true" />
      <Moon size={16} className="sc-theme-moon" aria-hidden="true" />
    </button>
  );
}

/** Keeps the theme in sync with the OS and with other open tabs. */
export function ThemeSync() {
  useEffect(() => {
    const media = window.matchMedia("(prefers-color-scheme: dark)");
    const stored = () => {
      try {
        return localStorage.getItem(STORAGE_KEY);
      } catch {
        return null;
      }
    };
    const followSystem = () => {
      const value = stored();
      if (!isTheme(value)) {
        applyTheme(media.matches ? "dark" : "light", false);
      }
    };
    const onStorage = (event: StorageEvent) => {
      if (event.key !== STORAGE_KEY) return;
      applyTheme(event.newValue === "dark" ? "dark" : "light", false);
    };

    followSystem();
    media.addEventListener("change", followSystem);
    window.addEventListener("storage", onStorage);
    return () => {
      media.removeEventListener("change", followSystem);
      window.removeEventListener("storage", onStorage);
    };
  }, []);

  return null;
}
