import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

export function Page({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={cn("sc-page", className)}>{children}</div>;
}

export function PageHeader({
  eyebrow,
  title,
  description,
  actions,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <header className="sc-page-head">
      <div className="sc-page-headcopy">
        {eyebrow ? <p className="sc-eyebrow">{eyebrow}</p> : null}
        <h1 className="sc-page-title">{title}</h1>
        {description ? <p className="sc-page-sub">{description}</p> : null}
      </div>
      {actions ? <div className="sc-page-actions">{actions}</div> : null}
    </header>
  );
}

export function Breadcrumbs({
  items,
}: {
  items: { label: string; href?: string }[];
}) {
  return (
    <nav className="sc-breadcrumbs" aria-label="Breadcrumb">
      {items.map((item, index) => (
        <span className="sc-breadcrumb" key={`${item.label}-${index}`}>
          {index > 0 ? <span className="sc-breadcrumb-sep">/</span> : null}
          {item.href ? (
            <Link href={item.href}>{item.label}</Link>
          ) : (
            <span aria-current="page">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}

export function SectionCard({
  title,
  description,
  actions,
  children,
  className,
}: {
  title?: string;
  description?: string;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cn("sc-card", className)}>
      {title || actions ? (
        <header className="sc-card-head">
          <div>
            {title ? <h2 className="sc-card-title">{title}</h2> : null}
            {description ? <p className="sc-card-sub">{description}</p> : null}
          </div>
          {actions ? <div className="sc-card-actions">{actions}</div> : null}
        </header>
      ) : null}
      <div className="sc-card-body">{children}</div>
    </section>
  );
}
