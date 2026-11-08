"use client";

import { useEffect, useRef, useState } from "react";

import { Check, Copy } from "@/components/Icons";

export function CopyCommand({ command }: { command: string }) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, []);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(() => setCopied(false), 1600);
    } catch {
      // Clipboard access can be denied; the command is still selectable.
    }
  }

  return (
    <button
      type="button"
      className="sc-l-copy"
      onClick={handleCopy}
      aria-label={copied ? "Command copied" : "Copy the CLI command"}
    >
      {copied ? <Check size={13} /> : <Copy size={13} />}
      <span aria-live="polite">{copied ? "Copied" : "Copy"}</span>
    </button>
  );
}
