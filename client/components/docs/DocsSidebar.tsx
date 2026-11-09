"use client";

import { useEffect, useState } from "react";

import { DOC_SECTIONS } from "@/lib/cli-docs";

export function DocsSidebar() {
  const [active, setActive] = useState(DOC_SECTIONS[0].id);

  useEffect(() => {
    const elements = DOC_SECTIONS.map((section) =>
      document.getElementById(section.id),
    ).filter((element): element is HTMLElement => element !== null);

    if (elements.length === 0) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort(
            (a, b) => a.boundingClientRect.top - b.boundingClientRect.top,
          );

        if (visible[0]) {
          setActive(visible[0].target.id);
        }
      },
      { rootMargin: "-18% 0px -68% 0px", threshold: [0, 1] },
    );

    elements.forEach((element) => observer.observe(element));
    return () => observer.disconnect();
  }, []);

  return (
    <aside className="sc-docs-sidebar">
      <p className="sc-docs-sidebar-title">On this page</p>
      <nav className="sc-docs-nav" aria-label="On this page">
        {DOC_SECTIONS.map((section) => (
          <a
            key={section.id}
            href={`#${section.id}`}
            className={active === section.id ? "is-active" : undefined}
            aria-current={active === section.id ? "location" : undefined}
          >
            {section.label}
          </a>
        ))}
      </nav>
      <div className="sc-docs-sidebar-note">
        <span>Verified against</span>
        <strong>CLI 0.1.0</strong>
      </div>
    </aside>
  );
}
