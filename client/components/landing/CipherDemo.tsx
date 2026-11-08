"use client";

import { useState } from "react";

import { Eye, Lock } from "@/components/Icons";

const CIPHERTEXT = [
  "v1:9f2c8a71d4b6e3a0c5f8",
  "2b7d1e9a4c6f0b3d8e5a",
  "7c1f4b9e2d6a8c3f5e0b",
].join("\n");

export function CipherDemo() {
  const [revealed, setRevealed] = useState(false);

  return (
    <section
      className={`sc-l-cipher${revealed ? " is-revealed" : ""}`}
      aria-label="Ciphertext and authorized reveal demonstration"
    >
      <header className="sc-l-cipher-head">
        <div className="sc-l-cipher-title">
          <span className="sc-l-tag">Sample record</span>
          <span className="sc-l-cipher-version">v42</span>
        </div>
        <div className="sc-l-switch" role="group" aria-label="Record state">
          <button
            type="button"
            aria-pressed={!revealed}
            onClick={() => setRevealed(false)}
          >
            <Lock size={12} />
            Ciphertext
          </button>
          <button
            type="button"
            aria-pressed={revealed}
            onClick={() => setRevealed(true)}
          >
            <Eye size={12} />
            Reveal
          </button>
        </div>
      </header>

      <div className="sc-l-cipher-body">
        {revealed ? (
          <dl className="sc-l-secret-list" translate="no">
            <div>
              <dt>STRIPE_SECRET_KEY</dt>
              <dd>sk_live_51N7••••••••••</dd>
            </div>
            <div>
              <dt>DATABASE_URL</dt>
              <dd>postgres://secria:••••@db</dd>
            </div>
            <div>
              <dt>RESEND_API_KEY</dt>
              <dd>re_••••••••••••••</dd>
            </div>
          </dl>
        ) : (
          <pre className="sc-l-ciphertext" translate="no">{CIPHERTEXT}</pre>
        )}

        <dl className="sc-l-cipher-record">
          <div>
            <dt>workspace</dt>
            <dd>acme</dd>
          </div>
          <div>
            <dt>project</dt>
            <dd>api</dd>
          </div>
          <div>
            <dt>environment</dt>
            <dd>prod</dd>
          </div>
          <div>
            <dt>key</dt>
            <dd>STRIPE_SECRET_KEY</dd>
          </div>
        </dl>

        <p className="sc-l-cipher-meta">Nonce 12B / Tag 16B / AAD ws:pr:env:key</p>
      </div>

      <footer className="sc-l-cipher-foot" aria-live="polite">
        {revealed ? (
          <>
            <i className="sc-l-dot" aria-hidden="true" />
            Reveal written to the audit log / just now
          </>
        ) : (
          <>
            <Lock size={12} />
            Decrypted only for an authorized reveal
          </>
        )}
      </footer>
    </section>
  );
}
