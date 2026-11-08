import { sha256 } from "@noble/hashes/sha2.js";
import { bytesToHex, utf8ToBytes } from "@noble/hashes/utils.js";

function findClosingQuote(text: string, quote: '"' | "'", start: number): number {
  for (let index = start; index < text.length; index += 1) {
    const char = text[index];
    if (quote === '"' && char === "\\") {
      index += 1;
      continue;
    }
    if (char === quote) return index;
  }
  return -1;
}

function unescapeDoubleQuoted(value: string): string {
  return value.replace(/\\([nrt"\\])/g, (_match, char: string) => {
    if (char === "n") return "\n";
    if (char === "r") return "\r";
    if (char === "t") return "\t";
    if (char === '"') return '"';
    return "\\";
  });
}

function commitValue(
  values: Record<string, string>,
  key: string,
  raw: string,
  quote: '"' | "'",
): void {
  values[key] = quote === '"' ? unescapeDoubleQuoted(raw) : raw;
}

export function parseEnvText(text: string): Record<string, string> {
  const values: Record<string, string> = {};
  const lines = text.replace(/^\uFEFF/, "").replace(/\r\n?/g, "\n").split("\n");
  let pendingKey: string | null = null;
  let pendingQuote: '"' | "'" = '"';
  let pendingValue = "";

  for (const rawLine of lines) {
    if (pendingKey !== null) {
      const closing = findClosingQuote(rawLine, pendingQuote, 0);
      if (closing === -1) {
        pendingValue += `\n${rawLine}`;
      } else {
        pendingValue += `\n${rawLine.slice(0, closing)}`;
        commitValue(values, pendingKey, pendingValue, pendingQuote);
        pendingKey = null;
        pendingValue = "";
      }
      continue;
    }

    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;
    const withoutExport = line.startsWith("export ") ? line.slice(7).trim() : line;
    const equals = withoutExport.indexOf("=");
    if (equals <= 0) continue;
    const key = withoutExport.slice(0, equals).trim();
    if (!key) continue;

    let value = withoutExport.slice(equals + 1).trimStart();
    if (!value) {
      values[key] = "";
      continue;
    }

    const quote = value[0];
    if (quote === '"' || quote === "'") {
      const closing = findClosingQuote(value, quote, 1);
      if (closing === -1) {
        pendingKey = key;
        pendingQuote = quote;
        pendingValue = value.slice(1);
      } else {
        commitValue(values, key, value.slice(1, closing), quote);
      }
      continue;
    }

    const comment = value.search(/\s+#/);
    if (comment >= 0) value = value.slice(0, comment);
    values[key] = value.trimEnd();
  }

  if (pendingKey !== null) {
    // An unterminated quote consumes the rest of the file; keep what was read
    // rather than dropping the key or hanging.
    commitValue(values, pendingKey, pendingValue, pendingQuote);
  }
  return values;
}

export function formatEnvValue(value: string): string {
  if (value === "") return '""';
  if (!value.startsWith("#") && /^[A-Za-z0-9_./:@%+,=-]+$/.test(value)) return value;
  return `"${value
    .replace(/\\/g, "\\\\")
    .replace(/"/g, '\\"')
    .replace(/\n/g, "\\n")
    .replace(/\r/g, "\\r")}"`;
}

export function formatEnvText(values: Record<string, string>): string {
  return (
    Object.keys(values)
      .sort()
      .map((key) => `${key}=${formatEnvValue(values[key])}`)
      .join("\n") + "\n"
  );
}

export function envPayload(values: Record<string, string>): { key: string; value: string }[] {
  return Object.entries(values).map(([key, value]) => ({ key, value }));
}

export function sha256Hex(value: string): string {
  return bytesToHex(sha256(utf8ToBytes(value)));
}

export function sha256Map(values: Record<string, string>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [key, value] of Object.entries(values)) {
    result[key] = sha256Hex(value);
  }
  return result;
}

export async function copyText(value: string): Promise<void> {
  await navigator.clipboard.writeText(value);
}
