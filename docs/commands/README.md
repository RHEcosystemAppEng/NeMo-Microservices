# NeMo Operational Runbooks

AI-assisted runbooks for installing and uninstalling NeMo Microservices on OpenShift.
These are plain Markdown files with structured instructions that any AI coding assistant
can follow. They inspect the cluster, detect conflicts, and adapt automatically.

## Available Runbooks

| Runbook | Description |
|---------|-------------|
| [install-nemo.md](install-nemo.md) | Full install with CRD conflict detection, orphaned resource cleanup, and optional component selection |
| [uninstall-nemo.md](uninstall-nemo.md) | Full uninstall including Helm releases, stuck finalizers, and cluster-scoped orphan cleanup |

## Usage

### Claude Code

Symlinks in `.claude/commands/` register these as slash commands. To set them up:

```bash
mkdir -p .claude/commands
ln -s ../../docs/commands/install-nemo.md .claude/commands/install-nemo.md
ln -s ../../docs/commands/uninstall-nemo.md .claude/commands/uninstall-nemo.md
```

Then use them as slash commands:

```
/install-nemo
/uninstall-nemo
```

### Cursor

Reference the runbook in chat with `@`:

```
@docs/commands/install-nemo.md run this on my cluster
@docs/commands/uninstall-nemo.md clean up the hacohen-nemo namespace
```

### Other AI Tools (OpenCode, Windsurf, Copilot Chat, etc.)

Attach or paste the Markdown file as context, then ask the tool to follow the instructions.
The runbooks are self-contained and have no tool-specific syntax.

## Prerequisites

All runbooks expect:
- `oc`, `helm`, and `jq` on PATH
- An active `oc login` session to the target cluster
- A `.env` file at the repository root with `NAMESPACE`, `NGC_API_KEY`, `NVIDIA_API_KEY`, and `HF_TOKEN`
