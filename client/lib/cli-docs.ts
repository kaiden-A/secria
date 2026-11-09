export type DocSection = {
  id: string;
  label: string;
};

export const DOC_SECTIONS: DocSection[] = [
  { id: "quick-start", label: "Quick start" },
  { id: "mental-model", label: "Mental model" },
  { id: "scenario", label: "Full scenario" },
  { id: "linking", label: "Linking a project" },
  { id: "daily-workflow", label: "Daily workflow" },
  { id: "authentication", label: "Authentication" },
  { id: "configuration", label: "Configuration" },
  { id: "commands", label: "Command reference" },
  { id: "ci", label: "CI and tokens" },
  { id: "recipes", label: "Recipes" },
  { id: "troubleshooting", label: "Troubleshooting" },
  { id: "faq", label: "FAQ" },
];

export type CommandRow = {
  command: string;
  purpose: string;
  flags: string[];
  example: string;
};

export type CommandGroup = {
  id: string;
  title: string;
  blurb: string;
  rows: CommandRow[];
};

export const COMMAND_GROUPS: CommandGroup[] = [
  {
    id: "setup",
    title: "Setup and identity",
    blurb:
      "Install, sign in, check your connection, and see which account or token the CLI is using.",
    rows: [
      {
        command: "secria login",
        purpose: "Sign in with the Zitadel device flow.",
        flags: ["--server <url>", "--no-browser"],
        example: "secria login --server https://secria.example.com",
      },
      {
        command: "secria logout",
        purpose: "Remove the stored session for the current server.",
        flags: [],
        example: "secria logout",
      },
      {
        command: "secria whoami",
        purpose: "Show the signed-in user, or the current service-token scope.",
        flags: [],
        example: "secria whoami",
      },
      {
        command: "secria doctor",
        purpose: "Check config, auth, keyring, link file, API health, and discovery.",
        flags: ["--offline"],
        example: "secria doctor --offline",
      },
      {
        command: "secria init",
        purpose: "Link the current directory to a workspace/project/environment.",
        flags: ["--workspace <slug>", "--project <slug>", "--env <slug>"],
        example:
          "secria init --workspace elysiaa --project mits-warden-system --env dev",
      },
      {
        command: "secria version",
        purpose: "Print the CLI version. `secria --version` does the same.",
        flags: [],
        example: "secria version",
      },
    ],
  },
  {
    id: "browse",
    title: "Browse and create",
    blurb:
      "Find your way around the vault. Slugs and names are both accepted, case-insensitively.",
    rows: [
      {
        command: "secria workspace list",
        purpose: "List workspaces, your role, member count, and project count.",
        flags: [],
        example: "secria workspace list",
      },
      {
        command: "secria workspace use <slug>",
        purpose: "Set the machine-wide default workspace.",
        flags: [],
        example: "secria workspace use elysiaa",
      },
      {
        command: "secria project list",
        purpose: "List projects in the resolved workspace.",
        flags: ["--workspace <slug>"],
        example: "secria project list --workspace elysiaa",
      },
      {
        command: "secria project create <name>",
        purpose:
          "Create a project. It gets dev/staging/prod automatically. It does not link the directory unless --from-env is used.",
        flags: [
          "--workspace <slug>",
          "--slug <slug>",
          "--description <text>",
          "--from-env <file>",
          "--env <slug>",
        ],
        example:
          "secria project create mits-warden-system --workspace elysiaa",
      },
      {
        command: "secria env list",
        purpose: "List the environments in a project.",
        flags: ["--workspace <slug>", "--project <slug>"],
        example: "secria env list --workspace elysiaa --project mits-warden-system",
      },
      {
        command: "secria env create <name>",
        purpose: "Add an environment beyond dev/staging/prod.",
        flags: ["--workspace <slug>", "--project <slug>", "--slug <slug>"],
        example:
          "secria env create preview --workspace elysiaa --project mits-warden-system",
      },
    ],
  },
  {
    id: "daily",
    title: "Daily workflow",
    blurb:
      "These four commands cover almost everything: upload, download, compare, and run.",
    rows: [
      {
        command: "secria push [FILE]",
        purpose:
          "Compare a local env file by hash, then upload it. Merge by default; --replace removes remote keys missing locally.",
        flags: [
          "--env <slug>",
          "--project <slug>",
          "--workspace <slug>",
          "--replace",
          "--dry-run",
          "-y, --yes",
        ],
        example: "secria push .env --env prod --dry-run",
      },
      {
        command: "secria pull",
        purpose:
          "Write secrets to a local file. Refuses to overwrite without --force.",
        flags: [
          "-o, --out <file>",
          "--format env|json|yaml",
          "--force",
          "--env <slug>",
          "--project <slug>",
          "--workspace <slug>",
        ],
        example: "secria pull --env prod --out .env.prod --force",
      },
      {
        command: "secria diff [FILE]",
        purpose:
          "Show added, changed, removed, and unchanged keys without writing anything.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria diff .env --env staging",
      },
      {
        command: "secria run -- <command>",
        purpose:
          "Run a command with secrets injected in memory. Nothing is written to disk.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria run --env prod -- npm start",
      },
    ],
  },
  {
    id: "secrets",
    title: "One-off secret operations",
    blurb:
      "For quick reads and edits. For bulk work, use push, pull, or diff instead.",
    rows: [
      {
        command: "secria secrets list",
        purpose: "List key names, versions, timestamps, and comments. Values stay masked.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria secrets list --env dev",
      },
      {
        command: "secria secrets get <KEY>",
        purpose: "Print one value. This is a reveal and is audited.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria secrets get DATABASE_URL --env dev",
      },
      {
        command: "secria secrets set <KEY=VALUE>",
        purpose: "Create or update one key. Values with '=' work because only the first '=' splits.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria secrets set STRIPE_SECRET_KEY=sk_live_new --env prod",
      },
      {
        command: "secria secrets unset <KEY>",
        purpose: "Delete one key from the environment.",
        flags: ["--env <slug>", "--project <slug>", "--workspace <slug>"],
        example: "secria secrets unset OLD_API_KEY --env dev",
      },
    ],
  },
  {
    id: "tokens",
    title: "Service tokens",
    blurb:
      "Machine credentials for CI and automation. A token has exactly one workspace/project/environment scope.",
    rows: [
      {
        command: "secria token create",
        purpose:
          "Create a read or read_write service token for the resolved project and environment. The token is shown once.",
        flags: [
          "--name <name>",
          "--access read|read_write",
          "--expires-in-days <n>",
          "--env <slug>",
          "--project <slug>",
          "--workspace <slug>",
        ],
        example:
          "secria token create --name github-actions --access read --env prod --expires-in-days 90",
      },
    ],
  },
  {
    id: "config",
    title: "Configuration",
    blurb:
      "The CLI resolves settings from flags, environment variables, saved config, the link file, then the built-in default.",
    rows: [
      {
        command: "secria config show",
        purpose: "Show the resolved server and identity-provider settings, including each source.",
        flags: [],
        example: "secria config show",
      },
      {
        command: "secria config set <key> <value>",
        purpose:
          "Save one setting. Keys: api-url, zitadel-issuer, zitadel-client-id.",
        flags: [],
        example: "secria config set api-url https://secria.example.com",
      },
      {
        command: "secria config path",
        purpose: "Print the directory that holds config.json and fallback credentials.",
        flags: [],
        example: "secria config path",
      },
    ],
  },
];

export type TroubleshootingRow = {
  symptom: string;
  meaning: string;
  fix: string;
};

export const TROUBLESHOOTING: TroubleshootingRow[] = [
  {
    symptom: "Not signed in. Run `secria login`.",
    meaning: "There is no stored session, the session expired, or the API rejected the token.",
    fix: "Run `secria login` again. In CI, check that `SECRIA_TOKEN` is set and valid.",
  },
  {
    symptom: "Choose a workspace with `--workspace` or `secria workspace use <slug>`.",
    meaning: "You belong to more than one workspace and the CLI could not resolve one.",
    fix: "Run `secria workspace use elysiaa`, or pass `--workspace elysiaa` to the command.",
  },
  {
    symptom: "Environment 'prod' not found. Available: dev, staging.",
    meaning: "The environment slug is wrong or the environment does not exist yet.",
    fix: "Run `secria env list --workspace <ws> --project <project>`, then use a listed slug.",
  },
  {
    symptom: "That project slug is already in use.",
    meaning: "Another project in the same workspace already has that slug.",
    fix: "Use the existing project, choose a different `--slug`, or create it in another workspace.",
  },
  {
    symptom: "This service token is scoped to environment 'dev', not 'prod'.",
    meaning: "A service token has exactly one scope; it cannot be widened with flags.",
    fix: "Omit workspace/project/env flags, or create a token for the environment you need.",
  },
  {
    symptom: "Could not reach the Secria API at ...",
    meaning: "The server URL is wrong, the server is down, or the network blocked the request.",
    fix: "Run `secria doctor` to check the URL, API health, and discovery document.",
  },
  {
    symptom: ".env already exists. Use --force to overwrite.",
    meaning: "`pull` protects existing files by default.",
    fix: "Pass `--force`, or write to a different file with `--out .env.local`.",
  },
  {
    symptom: "No secrets found in the file.",
    meaning: "The env file is empty, missing, or could not be parsed.",
    fix: "Check the path and contents. `push` reads `.env` by default; pass the file explicitly.",
  },
  {
    symptom: "The device login expired or was denied.",
    meaning: "The browser approval timed out or was rejected.",
    fix: "Run `secria login` again. Use `--no-browser` if the browser did not open.",
  },
  {
    symptom: "Your role does not allow that action.",
    meaning: "You are authenticated, but your workspace or project role cannot perform the action.",
    fix: "Ask a workspace owner/admin for the right role, or use an appropriately scoped token.",
  },
  {
    symptom: "The Envs column shows 3, but I never created an environment.",
    meaning:
      "This is expected. Every new project is created with dev, staging, and prod. Envs counts environments, not secrets.",
    fix: "Nothing. Run `secria env list --workspace <ws> --project <project>` to see them.",
  },
  {
    symptom: "`secria init` linked the wrong project.",
    meaning: "An existing `.secria.yaml` was found and used before the CLI asked you anything.",
    fix: "Pass all three flags: `secria init --workspace <ws> --project <project> --env <env>`.",
  },
  {
    symptom: "`secria project create` succeeded, but there is no `.secria.yaml`.",
    meaning: "Project creation does not link the directory by default.",
    fix: "Run `secria init --workspace <ws> --project <project> --env <env>`, or use `--from-env` next time.",
  },
  {
    symptom: "Service tokens cannot create other service tokens.",
    meaning: "Token creation is a user-only action.",
    fix: "Run `secria token create` from your own logged-in session, not from a CI token.",
  },
];

export type FaqItem = {
  question: string;
  answer: string;
};

export const FAQ: FaqItem[] = [
  {
    question: "What is `.secria.yaml`, and is it safe to commit?",
    answer:
      "It is the link file written by `secria init`. It contains the workspace slug, project slug, environment slug, and optionally the server URL. It contains no secrets, so it is safe to commit and share with teammates.",
  },
  {
    question: "Why does `--env` mean environment, not the `.env` file?",
    answer:
      "`--env` selects a Secria environment such as dev, staging, or prod. The local file is the positional `FILE` argument for `push` and `diff`, or `--out` for `pull`. So `secria push .env --env prod` means 'read the file .env and upload it to the prod environment'.",
  },
  {
    question: "Does `secria run` write secrets to disk?",
    answer:
      "No. It fetches the values, merges them into the child process environment, and runs the command. Nothing is written to a file.",
  },
  {
    question: "Where does decryption happen?",
    answer:
      "Only the Secria API decrypts. The CLI receives plaintext values for authorized pull/run/get responses, but it never holds the server master key or project data keys.",
  },
  {
    question: "Can I use the CLI in CI without a browser?",
    answer:
      "Yes. Create a service token with `secria token create`, store it as a masked CI secret, and set `SECRIA_TOKEN`. The token's scope defines the workspace, project, and environment, so you do not pass those flags.",
  },
  {
    question: "Can I connect to more than one Secria server?",
    answer:
      "Yes. Sessions are stored per server host. Use `secria login --server https://secria.example.com` for each instance. The saved server URL and token are keyed by host, so they do not overwrite each other.",
  },
  {
    question: "How do I switch the project for this folder?",
    answer:
      "Run `secria init` again with explicit flags: `secria init --workspace <ws> --project <project> --env <env>`. It overwrites the local `.secria.yaml`.",
  },
  {
    question: "How do I delete a project?",
    answer:
      "The CLI does not currently expose project deletion. Use the web app, or call `DELETE /api/v1/projects/{project_id}` with a workspace owner/admin session.",
  },
  {
    question: "Why does a new project already have three environments?",
    answer:
      "Secria creates dev, staging, and prod for every new project in the same transaction as the project and its wrapped key. They are empty until you push secrets. The Envs column counts environments, not secrets.",
  },
  {
    question: "What is the difference between merge and replace?",
    answer:
      "Merge uploads the keys in your file and leaves other remote keys alone. Replace makes the remote environment match the file exactly, so keys missing locally are removed. Replace asks for an extra confirmation.",
  },
  {
    question: "How do I see a secret value?",
    answer:
      "Use `secria secrets get KEY --env <env>`. It prints only the value and records an audited reveal. `secria secrets list` intentionally shows keys and metadata without values.",
  },
  {
    question: "Is `pull` safe on a shared machine?",
    answer:
      "`pull` writes the file with owner-only permissions and warns when the file is not in `.gitignore`. On a shared machine, prefer `secria run` so no file is written, or pull to a short-lived path and delete it.",
  },
];

export type Recipe = {
  title: string;
  body: string;
  code: string;
  codeTitle?: string;
};

export const RECIPES: Recipe[] = [
  {
    title: "Link once at the monorepo root",
    body:
      "Run `init` at the repository root. Every package below it inherits the link because the CLI searches parent directories.",
    code: "cd repo-root\nsecria init --workspace elysiaa --project mits-warden-system --env dev\ncd apps/web\nsecria diff .env",
    codeTitle: "monorepo",
  },
  {
    title: "Give one package its own project",
    body:
      "Create a closer `.secria.yaml` inside that package. The nearest link wins over the root link.",
    code: "cd apps/billing\nsecria init --workspace elysiaa --project billing --env dev",
    codeTitle: "per-package override",
  },
  {
    title: "Export JSON or YAML for another tool",
    body:
      "Pull into a different format when a framework or deploy tool needs structured config.",
    code: "secria pull --env prod --out secrets.json --format json --force\nsecria pull --env prod --out secrets.yaml --format yaml --force",
    codeTitle: "exports",
  },
  {
    title: "Rotate one secret",
    body:
      "Set the new value, then restart or redeploy. The old version stays in history; the next read gets the new value.",
    code: "secria secrets set STRIPE_SECRET_KEY=sk_live_new --env prod\nsecria run --env prod -- ./deploy.sh",
    codeTitle: "rotation",
  },
  {
    title: "Check what will change before deploying",
    body:
      "Run a read-only diff against the target environment. It never writes.",
    code: "secria diff .env.prod --env prod",
    codeTitle: "pre-deploy check",
  },
  {
    title: "Create a project from an existing .env",
    body:
      "One command creates the project, pushes the file, and links the current directory. This is the only form of `project create` that links automatically.",
    code: "secria project create mits-warden-system --workspace elysiaa --from-env .env --env dev",
    codeTitle: "create and seed",
  },
  {
    title: "Use two self-hosted servers",
    body:
      "Log in once per server. Sessions are keyed by host, so the tokens do not overwrite each other.",
    code: "secria login --server https://secria.one.example.com\nsecria login --server https://secria.two.example.com\nsecria config show",
    codeTitle: "multiple servers",
  },
  {
    title: "Set a CI token in PowerShell",
    body:
      "The token lasts for the current shell session. Use your CI provider's masked-secret mechanism in a real pipeline.",
    code: "$env:SECRIA_API_URL = \"https://secria.example.com\"\n$env:SECRIA_TOKEN = \"secria_st_...\"\nsecria whoami",
    codeTitle: "windows / powershell",
  },
];
