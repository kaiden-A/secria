import Link from "next/link";

import { Logo } from "@/components/Logo";

export default function NotFound() {
  return (
    <main className="sc-notfound">
      <div className="sc-notfound-card">
        <Logo size={38} />
        <p className="sc-eyebrow">404 · not in the ledger</p>
        <h1>This page doesn&rsquo;t have a key.</h1>
        <p>
          The address may be old, mistyped, or belong to a workspace you can&rsquo;t see.
          Head back to safe ground.
        </p>
        <Link className="sc-btn sc-btn--primary" href="/">
          Back to Secria
        </Link>
      </div>
    </main>
  );
}
