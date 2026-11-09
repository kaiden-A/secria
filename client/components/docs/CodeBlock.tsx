import { CopyCommand } from "@/components/landing/CopyCommand";

export function CodeBlock({
  code,
  title = "shell",
  copyable = true,
}: {
  code: string;
  title?: string;
  copyable?: boolean;
}) {
  return (
    <div className="sc-docs-code">
      <div className="sc-docs-code-head">
        <span>{title}</span>
        {copyable ? (
          <CopyCommand command={code} label={`Copy ${title}`} />
        ) : null}
      </div>
      <pre translate="no">
        <code>{code}</code>
      </pre>
    </div>
  );
}
