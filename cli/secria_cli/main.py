import inspect
import json
import os
import subprocess
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any

import httpx
import typer
import yaml
from rich.console import Console
from rich.table import Table

from . import __version__, auth, config, envfile
from .api import SecriaAPI
from .errors import CliError

config.load_environment()

console = Console()
err_console = Console(stderr=True)

app = typer.Typer(
    name="secria",
    help="Secria secrets manager CLI: push, pull, diff, and run with secrets.",
    no_args_is_help=True,
    add_completion=False,
)
workspace_app = typer.Typer(help="Workspaces.", no_args_is_help=True)
project_app = typer.Typer(help="Projects.", no_args_is_help=True)
env_app = typer.Typer(help="Environments.", no_args_is_help=True)
secrets_app = typer.Typer(help="Secrets.", no_args_is_help=True)
token_app = typer.Typer(help="Service tokens.", no_args_is_help=True)

app.add_typer(workspace_app, name="workspace")
app.add_typer(project_app, name="project")
app.add_typer(env_app, name="env")
app.add_typer(secrets_app, name="secrets")
app.add_typer(token_app, name="token")


@dataclass
class LinkContext:
    workspace: dict[str, Any]
    project: dict[str, Any] | None = None
    environment: dict[str, Any] | None = None


def handle_errors(func: Callable) -> Callable:
    signature = inspect.signature(func)

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except typer.Exit:
            raise
        except KeyboardInterrupt:
            raise typer.Exit(130) from None
        except CliError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(exc.exit_code) from None
        except httpx.HTTPError as exc:
            err_console.print(
                f"[red]Could not reach the Secria API at {config.api_url()} "
                f"({type(exc).__name__}).[/red]"
            )
            raise typer.Exit(1) from None
        except OSError as exc:
            err_console.print(f"[red]{exc}[/red]")
            raise typer.Exit(1) from None

    wrapper.__signature__ = signature  # type: ignore[attr-defined]
    return wrapper


def _api() -> SecriaAPI:
    return SecriaAPI(config.api_url(), auth.get_token())


def _link() -> dict[str, Any]:
    _path, data = config.find_link()
    return data


def _find_named(items: list[dict[str, Any]], desired: str, kind: str) -> dict[str, Any]:
    needle = desired.strip().lower()
    for item in items:
        if str(item.get("slug", "")).lower() == needle:
            return item
        if str(item.get("name", "")).lower() == needle:
            return item
    raise CliError(f"{kind} '{desired}' not found.")


def _prompt_workspace(workspaces: list[dict[str, Any]]) -> dict[str, Any]:
    console.print("Available workspaces:")
    for item in workspaces:
        console.print(f"  [bold]{item['slug']}[/bold]  {item['name']}  ({item['role']})")
    return _find_named(workspaces, typer.prompt("Workspace slug"), "Workspace")


def _prompt_project(projects: list[dict[str, Any]]) -> dict[str, Any]:
    console.print("Available projects:")
    for item in projects:
        console.print(f"  [bold]{item['slug']}[/bold]  {item['name']}  ({item['role']})")
    return _find_named(projects, typer.prompt("Project slug"), "Project")


def _resolve_workspace(
    api: SecriaAPI,
    option: str | None,
    *,
    interactive: bool = False,
) -> dict[str, Any]:
    workspaces = api.request("GET", "/api/v1/workspaces")
    if not isinstance(workspaces, list) or not workspaces:
        raise CliError("You are not a member of any workspace yet.")
    desired = option or _link().get("workspace") or config.load_settings().get("default_workspace")
    if desired:
        return _find_named(workspaces, str(desired), "Workspace")
    if len(workspaces) == 1:
        return workspaces[0]
    if interactive:
        return _prompt_workspace(workspaces)
    raise CliError("Choose a workspace with --workspace or `secria workspace use <slug>`.")


def _resolve_project(
    api: SecriaAPI,
    workspace: dict[str, Any],
    option: str | None,
    *,
    interactive: bool = False,
) -> dict[str, Any]:
    projects = api.request("GET", f"/api/v1/workspaces/{workspace['id']}/projects")
    if not isinstance(projects, list) or not projects:
        raise CliError("No projects are available in that workspace.")
    desired = option or _link().get("project")
    if desired:
        return _find_named(projects, str(desired), "Project")
    if len(projects) == 1:
        return projects[0]
    if interactive:
        return _prompt_project(projects)
    raise CliError("Choose a project with --project.")


def _resolve_project_context(
    api: SecriaAPI,
    workspace_option: str | None,
    project_option: str | None,
    *,
    interactive: bool = False,
) -> LinkContext:
    workspace = _resolve_workspace(api, workspace_option, interactive=interactive)
    project_summary = _resolve_project(
        api, workspace, project_option, interactive=interactive
    )
    project = api.request("GET", f"/api/v1/projects/{project_summary['id']}")
    return LinkContext(workspace=workspace, project=project)


def _resolve_environment(
    project: dict[str, Any],
    option: str | None,
    *,
    interactive: bool = False,
) -> dict[str, Any]:
    environments = project.get("environments") or []
    if not environments:
        raise CliError("That project has no environments.")
    desired = option or _link().get("environment") or "dev"
    needle = str(desired).lower()
    for environment in environments:
        if str(environment.get("slug", "")).lower() == needle:
            return environment
        if str(environment.get("name", "")).lower() == needle:
            return environment
    if len(environments) == 1:
        return environments[0]
    if interactive:
        console.print("Available environments:")
        for environment in environments:
            console.print(f"  [bold]{environment['slug']}[/bold]  {environment['name']}")
        return _find_named(environments, typer.prompt("Environment slug"), "Environment")
    available = ", ".join(environment["slug"] for environment in environments)
    raise CliError(f"Environment '{desired}' not found. Available: {available}.")


def _resolve_context(
    api: SecriaAPI,
    workspace_option: str | None,
    project_option: str | None,
    env_option: str | None,
    *,
    interactive: bool = False,
) -> LinkContext:
    if auth.is_service_token():
        return _resolve_service_context(
            api,
            workspace_option,
            project_option,
            env_option,
        )
    context = _resolve_project_context(
        api, workspace_option, project_option, interactive=interactive
    )
    if context.project is None:
        raise CliError("No project selected.")
    context.environment = _resolve_environment(
        context.project, env_option, interactive=interactive
    )
    return context


def _matches(item: dict[str, Any], option: str) -> bool:
    needle = option.strip().lower()
    return needle in {
        str(item.get("slug", "")).lower(),
        str(item.get("name", "")).lower(),
    }


def _check_scope_option(
    option: str | None,
    item: dict[str, Any],
    kind: str,
) -> None:
    if option and not _matches(item, option):
        raise CliError(
            f"This service token is scoped to {kind} '{item.get('slug')}', "
            f"not '{option}'."
        )


def _resolve_service_context(
    api: SecriaAPI,
    workspace_option: str | None,
    project_option: str | None,
    env_option: str | None,
) -> LinkContext:
    """A service token has exactly one scope; never ask the user endpoints."""
    scope = api.request("GET", "/api/v1/service-tokens/current")
    if not isinstance(scope, dict):
        raise CliError("The API did not return a service-token scope.")
    workspace = {
        "id": scope["workspaceId"],
        "slug": scope["workspaceSlug"],
        "name": scope["workspaceName"],
    }
    environment = {
        "id": scope["environmentId"],
        "slug": scope["environmentSlug"],
        "name": scope["environmentName"],
        "position": 0,
    }
    project = {
        "id": scope["projectId"],
        "slug": scope["projectSlug"],
        "name": scope["projectName"],
        "environments": [environment],
    }
    _check_scope_option(workspace_option, workspace, "workspace")
    _check_scope_option(project_option, project, "project")
    _check_scope_option(env_option, environment, "environment")
    return LinkContext(workspace=workspace, project=project, environment=environment)


def _secrets_path(context: LinkContext) -> str:
    if context.project is None or context.environment is None:
        raise CliError("No project/environment selected.")
    return (
        f"/api/v1/projects/{context.project['id']}"
        f"/environments/{context.environment['id']}/secrets"
    )


def _short_keys(keys: list[str]) -> str:
    if not keys:
        return ""
    shown = ", ".join(keys[:25])
    return shown + (f" … +{len(keys) - 25}" if len(keys) > 25 else "")


def _print_diff(diff: dict[str, Any]) -> None:
    table = Table(title="Secret diff", header_style="bold")
    table.add_column("Change")
    table.add_column("Count", justify="right")
    table.add_column("Keys", overflow="fold")
    table.add_row("[green]+ added[/green]", str(len(diff["added"])), _short_keys(diff["added"]))
    table.add_row("[yellow]~ changed[/yellow]", str(len(diff["changed"])), _short_keys(diff["changed"]))
    table.add_row("[red]- removed[/red]", str(len(diff["removed"])), _short_keys(diff["removed"]))
    table.add_row("[dim]= unchanged[/dim]", str(len(diff["unchanged"])), _short_keys(diff["unchanged"]))
    console.print(table)


def _print_counts(result: dict[str, Any]) -> None:
    console.print(
        f"[green]+{result.get('added', 0)}[/green] "
        f"[yellow]~{result.get('updated', 0)}[/yellow] "
        f"[red]-{result.get('removed', 0)}[/red] "
        f"[dim]={result.get('unchanged', 0)}[/dim]"
    )


def _diff(api: SecriaAPI, context: LinkContext, values: dict[str, str]) -> dict[str, Any]:
    digest = envfile.hashes(values)
    return api.request(
        "POST",
        f"{_secrets_path(context)}/diff",
        json_body={
            "secrets": [
                {"key": key, "valueSha256": value} for key, value in digest.items()
            ]
        },
    )


def _push_values(
    api: SecriaAPI,
    context: LinkContext,
    values: dict[str, str],
    *,
    mode: str,
    dry_run: bool,
    yes: bool,
) -> None:
    if not values:
        raise CliError("No secrets found in the file.")
    diff = _diff(api, context, values)
    _print_diff(diff)
    if dry_run:
        console.print("[dim]Dry run: nothing was written.[/dim]")
        return
    if not diff["added"] and not diff["changed"] and not diff["removed"]:
        console.print("Already in sync.")
        return

    workspace = context.workspace["slug"]
    project = context.project["slug"] if context.project else "?"
    environment = context.environment["slug"] if context.environment else "?"
    if not yes:
        typer.confirm(
            f"Push {len(values)} secrets to {workspace}/{project}/{environment}?",
            abort=True,
        )
    if mode == "replace" and not yes:
        typer.confirm(
            "Replace will remove remote keys that are not in the file. Continue?",
            abort=True,
        )
    result = api.request(
        "PUT",
        _secrets_path(context),
        json_body={"secrets": envfile.payload(values), "mode": mode},
    )
    _print_counts(result)


def _warn_gitignore(path: Path) -> None:
    if path.exists() and not envfile.is_gitignored(path):
        err_console.print(
            f"[yellow]Warning: {path} is not in .gitignore. Secrets can leak if committed.[/yellow]"
        )


def _fmt_ms(value: int | None) -> str:
    if not value:
        return "-"
    return datetime.fromtimestamp(value / 1000).strftime("%Y-%m-%d %H:%M")


@app.command()
def version() -> None:
    """Print the CLI version."""
    console.print(f"secria [bold]{__version__}[/bold]")


@app.command()
@handle_errors
def login(
    browser: bool = typer.Option(
        True, "--browser/--no-browser", help="Open the verification page."
    ),
) -> None:
    """Sign in with the Zitadel device flow."""
    auth.device_login(open_browser=browser)


@app.command()
@handle_errors
def logout() -> None:
    """Remove the stored CLI session."""
    auth.logout()
    console.print("Signed out.")


@app.command()
@handle_errors
def whoami() -> None:
    """Show the signed-in user or the current service-token scope."""
    api = _api()
    if auth.is_service_token():
        scope = api.request("GET", "/api/v1/service-tokens/current")
        console.print(
            f"[bold]Service token[/bold] {scope.get('name', '')} "
            f"({scope.get('access', 'read')})"
        )
        console.print(
            f"Scope: {scope.get('workspaceSlug')}/"
            f"{scope.get('projectSlug')}/{scope.get('environmentSlug')}"
        )
        return
    me = api.request("GET", "/api/v1/me")
    console.print(f"[bold]{me.get('name', 'User')}[/bold] <{me.get('email', '')}>")


@app.command()
@handle_errors
def init(
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace slug or name."),
    project: str | None = typer.Option(None, "--project", help="Project slug or name."),
    environment: str | None = typer.Option(None, "--env", help="Environment slug or name."),
) -> None:
    """Link the current directory to a workspace/project/environment."""
    api = _api()
    context = _resolve_context(
        api,
        workspace,
        project,
        environment,
        interactive=True,
    )
    path = Path.cwd() / config.LINK_NAME
    config.save_link(
        path,
        workspace=context.workspace["slug"],
        project=context.project["slug"] if context.project else "",
        environment=context.environment["slug"] if context.environment else "",
    )
    console.print(
        f"Linked [bold]{path}[/bold] → "
        f"{context.workspace['slug']}/"
        f"{context.project['slug'] if context.project else '?'}/"
        f"{context.environment['slug'] if context.environment else '?'}"
    )


@app.command()
@handle_errors
def push(
    file: str = typer.Argument(".env", metavar="FILE", help="Local env file."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
    replace: bool = typer.Option(False, "--replace", help="Remove remote keys missing locally."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show the diff only."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmations."),
) -> None:
    """Push a local env file to Secria."""
    path = Path(file)
    values = envfile.parse_env(path)
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    _push_values(
        api,
        context,
        values,
        mode="replace" if replace else "merge",
        dry_run=dry_run,
        yes=yes,
    )
    _warn_gitignore(path)


@app.command()
@handle_errors
def pull(
    out: str = typer.Option(".env", "--out", "-o", help="Output file."),
    format: str = typer.Option("env", "--format", help="env, json or yaml."),
    force: bool = typer.Option(False, "--force", help="Overwrite an existing file."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Pull secrets into a local file."""
    fmt = format.strip().lower()
    if fmt not in {"env", "json", "yaml"}:
        raise CliError("--format must be env, json or yaml.")
    path = Path(out)
    if path.exists() and not force:
        raise CliError(f"{path} already exists. Use --force to overwrite.")
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    if context.project is None or context.environment is None:
        raise CliError("No project/environment selected.")
    base = (
        f"/api/v1/projects/{context.project['id']}"
        f"/environments/{context.environment['id']}/secrets/download"
    )
    if fmt == "env":
        text = api.request_text("GET", base, params={"format": "env"})
    else:
        data = api.request("GET", base, params={"format": "json"})
        if fmt == "json":
            text = json.dumps(data, indent=2, sort_keys=True) + "\n"
        else:
            text = yaml.safe_dump(data, sort_keys=True)
    envfile.write_env(path, text)
    console.print(f"Wrote [bold]{path}[/bold].")
    _warn_gitignore(path)


@app.command()
@handle_errors
def diff(
    file: str = typer.Argument(".env", metavar="FILE", help="Local env file."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Compare a local env file with Secria."""
    values = envfile.parse_env(Path(file))
    if not values:
        raise CliError("No secrets found in the file.")
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    _print_diff(_diff(api, context, values))


@app.command(context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
@handle_errors
def run(
    ctx: typer.Context,
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Run a command with secrets injected into its environment."""
    command = list(ctx.args)
    if not command:
        raise CliError("Provide a command after --, e.g. secria run -- npm start.")
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    if context.project is None or context.environment is None:
        raise CliError("No project/environment selected.")
    base = (
        f"/api/v1/projects/{context.project['id']}"
        f"/environments/{context.environment['id']}/secrets/download"
    )
    secrets = api.request("GET", base, params={"format": "json"})
    child_env = {key: value for key, value in os.environ.items() if key != "SECRIA_TOKEN"}
    child_env.update({str(key): str(value) for key, value in secrets.items()})
    result = subprocess.run(command, env=child_env)
    raise typer.Exit(result.returncode)


@workspace_app.command("list")
@handle_errors
def workspace_list() -> None:
    """List workspaces."""
    workspaces = _api().request("GET", "/api/v1/workspaces")
    table = Table(title="Workspaces", header_style="bold")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Members", justify="right")
    table.add_column("Projects", justify="right")
    for workspace in workspaces:
        table.add_row(
            workspace["slug"],
            workspace["name"],
            workspace["role"],
            str(workspace["memberCount"]),
            str(workspace["projectCount"]),
        )
    console.print(table)


@workspace_app.command("use")
@handle_errors
def workspace_use(slug: str = typer.Argument(..., help="Workspace slug or name.")) -> None:
    """Set the default workspace for this machine."""
    workspaces = _api().request("GET", "/api/v1/workspaces")
    workspace = _find_named(workspaces, slug, "Workspace")
    settings = config.load_settings()
    settings["default_workspace"] = workspace["slug"]
    config.save_settings(settings)
    console.print(f"Default workspace: [bold]{workspace['slug']}[/bold].")


@project_app.command("list")
@handle_errors
def project_list(
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """List projects in a workspace."""
    api = _api()
    ws = _resolve_workspace(api, workspace)
    projects = api.request("GET", f"/api/v1/workspaces/{ws['id']}/projects")
    table = Table(title=f"Projects in {ws['slug']}", header_style="bold")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Envs", justify="right")
    table.add_column("Members", justify="right")
    for project in projects:
        table.add_row(
            project["slug"],
            project["name"],
            project["role"],
            str(project["environmentCount"]),
            str(project["memberCount"]),
        )
    console.print(table)


@project_app.command("create")
@handle_errors
def project_create(
    name: str = typer.Argument(..., help="Project name."),
    slug: str | None = typer.Option(None, "--slug", help="Project slug."),
    description: str = typer.Option("", "--description", help="Project description."),
    from_env: str | None = typer.Option(None, "--from-env", help="Upload this env file."),
    env: str | None = typer.Option(None, "--env", help="Target environment."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Create a project, optionally seeding it from an env file."""
    api = _api()
    ws = _resolve_workspace(api, workspace, interactive=True)
    project = api.request(
        "POST",
        f"/api/v1/workspaces/{ws['id']}/projects",
        json_body={"name": name, "slug": slug, "description": description},
    )
    console.print(f"Created project [bold]{project['slug']}[/bold].")
    if not from_env:
        return
    path = Path(from_env)
    values = envfile.parse_env(path)
    environment = _resolve_environment(
        project, env or "dev", interactive=False
    )
    context = LinkContext(workspace=ws, project=project, environment=environment)
    _push_values(api, context, values, mode="merge", dry_run=False, yes=False)
    config.save_link(
        Path.cwd() / config.LINK_NAME,
        workspace=ws["slug"],
        project=project["slug"],
        environment=environment["slug"],
    )
    console.print(
        f"Linked this directory to {ws['slug']}/{project['slug']}/{environment['slug']}."
    )
    _warn_gitignore(path)


@env_app.command("list")
@handle_errors
def env_list(
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
    project: str | None = typer.Option(None, "--project", help="Project."),
) -> None:
    """List environments in a project."""
    api = _api()
    context = _resolve_project_context(api, workspace, project)
    if context.project is None:
        raise CliError("No project selected.")
    environments = api.request(
        "GET", f"/api/v1/projects/{context.project['id']}/environments"
    )
    table = Table(title=f"Environments in {context.project['slug']}", header_style="bold")
    table.add_column("Slug")
    table.add_column("Name")
    table.add_column("Position", justify="right")
    for environment in environments:
        table.add_row(
            environment["slug"], environment["name"], str(environment["position"])
        )
    console.print(table)


@env_app.command("create")
@handle_errors
def env_create(
    name: str = typer.Argument(..., help="Environment name."),
    slug: str | None = typer.Option(None, "--slug", help="Environment slug."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
    project: str | None = typer.Option(None, "--project", help="Project."),
) -> None:
    """Create an environment."""
    api = _api()
    context = _resolve_project_context(api, workspace, project)
    if context.project is None:
        raise CliError("No project selected.")
    environment = api.request(
        "POST",
        f"/api/v1/projects/{context.project['id']}/environments",
        json_body={"name": name, "slug": slug},
    )
    console.print(f"Created environment [bold]{environment['slug']}[/bold].")


@secrets_app.command("list")
@handle_errors
def secrets_list(
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """List secret keys (values stay masked)."""
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    rows = api.request("GET", _secrets_path(context))
    table = Table(title="Secrets", header_style="bold")
    table.add_column("Key")
    table.add_column("Version", justify="right")
    table.add_column("Updated")
    table.add_column("Comment")
    for row in rows:
        table.add_row(
            row["key"],
            str(row.get("version") or "-"),
            _fmt_ms(row.get("updatedAt")),
            row.get("comment") or "",
        )
    console.print(table)


@secrets_app.command("get")
@handle_errors
def secrets_get(
    key: str = typer.Argument(..., help="Secret key."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Print one secret value."""
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    result = api.request("GET", f"{_secrets_path(context)}/{key}")
    typer.echo(result.get("value", ""))


@secrets_app.command("set")
@handle_errors
def secrets_set(
    assignment: str = typer.Argument(..., metavar="KEY=VALUE", help="Secret assignment."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Create or update one secret."""
    key, sep, value = assignment.partition("=")
    if not sep or not key.strip():
        raise CliError("Use KEY=VALUE.")
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    api.request(
        "PUT",
        _secrets_path(context),
        json_body={"mode": "merge", "secrets": [{"key": key.strip(), "value": value}]},
    )
    console.print(f"Saved [bold]{key.strip()}[/bold].")


@secrets_app.command("unset")
@handle_errors
def secrets_unset(
    key: str = typer.Argument(..., help="Secret key."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
) -> None:
    """Delete one secret."""
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    api.request("DELETE", f"{_secrets_path(context)}/{key}")
    console.print(f"Deleted [bold]{key}[/bold].")


@token_app.command("create")
@handle_errors
def token_create(
    name: str = typer.Option(..., "--name", prompt=True, help="Token name."),
    access: str = typer.Option("read", "--access", help="read or read_write."),
    env: str | None = typer.Option(None, "--env", help="Environment."),
    project: str | None = typer.Option(None, "--project", help="Project."),
    workspace: str | None = typer.Option(None, "--workspace", help="Workspace."),
    expires_in_days: int | None = typer.Option(
        None, "--expires-in-days", help="Optional expiry in days."
    ),
) -> None:
    """Create a project/environment service token."""
    if auth.is_service_token():
        raise CliError("Service tokens cannot create other service tokens.")
    access = access.strip().lower()
    if access not in {"read", "read_write"}:
        raise CliError("--access must be read or read_write.")
    if expires_in_days is not None and expires_in_days <= 0:
        raise CliError("--expires-in-days must be positive.")
    api = _api()
    context = _resolve_context(api, workspace, project, env)
    if context.project is None or context.environment is None:
        raise CliError("No project/environment selected.")
    body: dict[str, Any] = {"name": name, "access": access}
    if expires_in_days is not None:
        body["expiresAt"] = int((time.time() + expires_in_days * 86400) * 1000)
    result = api.request(
        "POST",
        f"/api/v1/projects/{context.project['id']}"
        f"/environments/{context.environment['id']}/service-tokens",
        json_body=body,
    )
    console.print("[bold]Token (shown once):[/bold]")
    console.print(str(result["token"]), markup=False, highlight=False)
