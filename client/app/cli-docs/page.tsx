import type { Metadata } from "next";

import { CliDocs } from "@/components/docs/CliDocs";

export const metadata: Metadata = {
  title: "CLI documentation",
  description:
    "Install, link, push, pull, and run with the Secria CLI. A scenario-first guide, full command reference, CI tokens, recipes, and troubleshooting.",
  openGraph: {
    type: "article",
    siteName: "Secria",
    title: "Secria CLI documentation",
    description:
      "The vault, in your terminal. Learn the Secria CLI through a real project, then use the full command reference.",
  },
};

export default function CliDocsPage() {
  return <CliDocs />;
}
