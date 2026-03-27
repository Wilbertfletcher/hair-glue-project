#!/usr/bin/env bash
# bootstrap.sh — Initialize AI session planning documents in a target repository.
#
# Usage:
#   ./bootstrap.sh [--sub-project] [--force] <ProjectName> <DestinationPath>
#
# Modes:
#   Default (repo root)  — destination IS or contains the repo root;
#                          copilot-instructions.md is placed at the repo root
#                          and also copied to .github/ if that folder exists.
#   --sub-project        — destination is a subdirectory inside a larger repo;
#                          copilot-instructions.md is scoped inside the subdir;
#                          no .github/ copy is attempted.
#
# --force: overwrite any files that already exist (default is to skip them).
#
# Examples:
#   # Fresh repo
#   ./bootstrap.sh MyWebApp /home/user/repos/my-web-app
#
#   # Sub-directory of an existing repo
#   ./bootstrap.sh --sub-project DataPipeline /home/user/repos/monorepo/packages/data-pipeline
#
#   # Re-run to add missing files (existing files untouched)
#   ./bootstrap.sh MyWebApp /home/user/repos/my-web-app
#
#   # Re-run and overwrite everything
#   ./bootstrap.sh --force MyWebApp /home/user/repos/my-web-app

set -euo pipefail

# -- Parse flags --------------------------------------------------------------
SUB_PROJECT=false
FORCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        --sub-project) SUB_PROJECT=true; shift ;;
        --force)       FORCE=true;       shift ;;
        --)            shift; break ;;
        -*) echo "Unknown flag: $1" >&2; exit 1 ;;
        *)  break ;;
    esac
done

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 [--sub-project] [--force] <ProjectName> <DestinationPath>"
    echo "Example: $0 MyWebApp /home/user/repos/my-web-app"
    exit 1
fi

PROJECT_NAME="$1"
DEST="$(cd "$2" && pwd)"   # resolve to absolute path
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEMPLATE_DIR="$SCRIPT_DIR/templates"

# -- Validate -----------------------------------------------------------------
if [[ ! -d "$DEST" ]]; then
    echo "Error: Destination directory does not exist: $DEST"
    echo "    Create it first or pass an existing repo path."
    exit 1
fi

if [[ ! -d "$TEMPLATE_DIR" ]]; then
    echo "Error: Template directory not found: $TEMPLATE_DIR"
    echo "    Run this script from inside the ai-session-planning/ folder."
    exit 1
fi

# -- Auto-detect git root -----------------------------------------------------
find_git_root() {
    local current="$1"
    while [[ "$current" != "/" ]]; do
        if [[ -d "$current/.git" ]]; then
            echo "$current"
            return
        fi
        current="$(dirname "$current")"
    done
    echo ""
}

GIT_ROOT="$(find_git_root "$DEST")"

if [[ -n "$GIT_ROOT" && "$GIT_ROOT" != "$DEST" ]] && [[ "$SUB_PROJECT" == false ]]; then
    echo ""
    echo "  NOTICE  '$DEST' is inside a git repo rooted at:"
    echo "            $GIT_ROOT"
    echo "          Add --sub-project to scope docs to this subdirectory,"
    echo "          or omit it to treat the destination as the planning root anyway."
    echo ""
fi
if [[ -z "$GIT_ROOT" ]]; then
    echo ""
    echo "  NOTICE  No git repository found at or above the destination."
    echo "          Proceeding anyway — run 'git init' in the repo root when ready."
    echo ""
fi

# -- Counters -----------------------------------------------------------------
WRITTEN=0
SKIPPED=0

# -- Helper -------------------------------------------------------------------
copy_and_sub() {
    local src="$1"
    local dst="$2"
    local leaf
    leaf="$(basename "$dst")"
    if [[ -f "$dst" && "$FORCE" == false ]]; then
        echo "  SKIP  $leaf  (already exists; use --force to overwrite)"
        SKIPPED=$((SKIPPED + 1))
        return
    fi
    mkdir -p "$(dirname "$dst")"
    sed "s/{{ProjectName}}/${PROJECT_NAME}/g; s/{{FeatureName}}/${PROJECT_NAME} Feature/g; s/{{N}}/0/g" \
        "$src" > "$dst"
    echo "  OK    $leaf"
    WRITTEN=$((WRITTEN + 1))
}

# -- Print header -------------------------------------------------------------
echo ""
MODE_LABEL="repo root"
[[ "$SUB_PROJECT" == true ]] && MODE_LABEL="sub-project"
echo "Bootstrapping AI session planning for: $PROJECT_NAME  (mode: $MODE_LABEL)"
echo "    Destination: $DEST"
echo ""

# -- Copy TODO/ templates -----------------------------------------------------
echo "Creating TODO/ documents..."
copy_and_sub "$TEMPLATE_DIR/TODO/STATUS.md"           "$DEST/TODO/STATUS.md"
copy_and_sub "$TEMPLATE_DIR/TODO/TODO.md"             "$DEST/TODO/TODO.md"
copy_and_sub "$TEMPLATE_DIR/TODO/DECISIONS.md"        "$DEST/TODO/DECISIONS.md"
copy_and_sub "$TEMPLATE_DIR/TODO/GOTCHAS.md"          "$DEST/TODO/GOTCHAS.md"
copy_and_sub "$TEMPLATE_DIR/TODO/ROADMAP-TEMPLATE.md" "$DEST/TODO/ROADMAP-M0.md"

# -- copilot-instructions.md --------------------------------------------------
echo ""
echo "Creating copilot-instructions.md..."
copy_and_sub "$TEMPLATE_DIR/copilot-instructions.md"  "$DEST/copilot-instructions.md"

# -- .github/ copy (repo-root mode only) --------------------------------------
if [[ "$SUB_PROJECT" == false ]]; then
    # Resolve root: prefer detected git root, otherwise the destination itself.
    REPO_ROOT="${GIT_ROOT:-$DEST}"
    echo ""
    echo "Checking for .github/ (GitHub Copilot auto-injection)..."
    if [[ -d "$REPO_ROOT/.github" ]]; then
        copy_and_sub "$TEMPLATE_DIR/copilot-instructions.md" "$REPO_ROOT/.github/copilot-instructions.md"
    else
        echo "  --    No .github/ folder found at: $REPO_ROOT"
        echo "        To enable auto-injection, run:"
        echo "          mkdir -p \"$REPO_ROOT/.github\""
        echo "          cp \"$DEST/copilot-instructions.md\" \"$REPO_ROOT/.github/copilot-instructions.md\""
    fi
else
    echo ""
    echo "  --    Sub-project mode: skipping .github/ copy."
    echo "        The repo-level .github/copilot-instructions.md (if any) is unchanged."
    echo "        Attach '$DEST/copilot-instructions.md' manually when opening a session."
fi

# -- Summary ------------------------------------------------------------------
echo ""
echo "Bootstrap complete.  Written: $WRITTEN   Skipped: $SKIPPED"
if [[ $SKIPPED -gt 0 ]]; then
    echo "    (Re-run with --force to overwrite skipped files.)"
fi
echo ""
echo "Next steps:"
echo "  1. Edit TODO/STATUS.md          — fill in 'Where to Start Next Session'"
echo "  2. Edit TODO/TODO.md            — define your Milestone 0 tasks"
echo "  3. Edit copilot-instructions.md — fill in project architecture and key files"
echo "  4. Edit TODO/ROADMAP-M0.md      — fill in task details, phases, and acceptance criteria"
if [[ "$SUB_PROJECT" == false ]]; then
    echo "  5. Commit: git add TODO/ copilot-instructions.md && git commit -m 'chore: add AI session planning docs'"
else
    REL_PATH="${DEST#${GIT_ROOT:-}/}"
    echo "  5. Commit: git add \"$REL_PATH/TODO\" \"$REL_PATH/copilot-instructions.md\" && git commit -m 'chore: add AI session planning for $PROJECT_NAME'"
fi
echo ""
echo "Framework guide: $SCRIPT_DIR/README.md"
