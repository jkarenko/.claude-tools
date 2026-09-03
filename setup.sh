#!/bin/bash
set -e

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
REPO_URL_SSH="git@github.com:jkarenko/.claude-tools.git"
REPO_URL_HTTPS="https://github.com/jkarenko/.claude-tools.git"

# Private companion repo (private skills/scripts/CLAUDE.md rules). Optional: if it can't
# be cloned (no access / no network) setup continues with public content only.
# Skip it entirely with CLAUDE_TOOLS_PRIVATE=0.
PRIVATE_REPO_URL_SSH="git@github.com:jkarenko/.claude-tools-gofore.git"
PRIVATE_REPO_URL_HTTPS="https://github.com/jkarenko/.claude-tools-gofore.git"
PRIVATE_DIR="${CLAUDE_TOOLS_PRIVATE_DIR:-$HOME/.claude-tools-gofore}"
USE_PRIVATE="${CLAUDE_TOOLS_PRIVATE:-1}"

CLAUDE_DIR="$HOME/.claude"
BACKUP_SUFFIX=".bak.$(date +%Y%m%d_%H%M%S)"

# Detect install directory: use script's repo location if running from repo, else default
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
if [ -n "$SCRIPT_DIR" ] && [ -d "$SCRIPT_DIR/.git" ]; then
    INSTALL_DIR="$SCRIPT_DIR"
else
    INSTALL_DIR="$HOME/.claude-tools"
fi

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

info() { echo -e "${GREEN}[INFO]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# clone_or_pull <dir> <ssh-url> <https-url> <label>
# Returns 0 if the repo is present afterwards, 1 if it could not be obtained.
clone_or_pull() {
    local dir="$1" ssh="$2" https="$3" label="$4"
    if [ -d "$dir/.git" ]; then
        info "$label repo already exists at $dir"
        if ! git -C "$dir" pull; then
            warn "git pull failed in $dir. Possible causes:"
            echo "  - Uncommitted local changes: run 'git stash' or 'git commit'"
            echo "  - Merge conflicts: resolve manually in $dir"
            echo "  - Network issues: check your connection"
            echo ""
            warn "Continuing with existing local version..."
        fi
        return 0
    fi
    info "Cloning $label repo to $dir..."
    if git clone "$ssh" "$dir" 2>/dev/null; then
        info "Cloned via SSH"
    elif git clone "$https" "$dir" 2>/dev/null; then
        info "Cloned via HTTPS"
    else
        return 1
    fi
    return 0
}

# link_union <target-dir> <kind> <source-dir>...
#
# Makes <target-dir> a real directory whose entries are symlinks to the
# entries of each <source-dir> (first source wins on name clashes).
# Handles migration from older layouts:
#   - <target-dir> is a symlink to a single repo dir  -> replaced by a union dir
#   - <target-dir> is a real dir with real (non-symlink) entries -> those are
#     copied into the first source dir (unless already present) and the
#     originals backed up, so nothing local is lost
# Dangling symlinks left over from removed sources are pruned.
link_union() {
    local target="$1" kind="$2"; shift 2
    local sources=("$@")
    local primary="${sources[0]}"

    if [ -L "$target" ]; then
        info "Replacing legacy $kind symlink with a union directory"
        rm "$target"
    fi
    mkdir -p "$target"

    # Adopt local non-symlink entries into the primary source
    local entry name src moved=0
    for entry in "$target"/*; do
        [ -e "$entry" ] || continue
        [ -L "$entry" ] && continue
        name=$(basename "$entry")
        case "$name" in *.bak.*|.DS_Store|__pycache__) continue ;; esac
        local exists=0
        for src in "${sources[@]}"; do
            [ -e "$src/$name" ] && exists=1
        done
        if [ "$exists" -eq 1 ]; then
            warn "Local $kind '$name' also exists in a repo; keeping local copy as $name$BACKUP_SUFFIX"
        else
            cp -R "$entry" "$primary/$name"
            info "Adopted local $kind '$name' into $primary"
        fi
        mv "$entry" "$target/$name$BACKUP_SUFFIX"
        moved=1
    done
    [ "$moved" -eq 1 ] && warn "Local $kind entries were backed up with suffix $BACKUP_SUFFIX (safe to delete once you've checked the repo copy)"

    # Prune dangling symlinks
    for entry in "$target"/*; do
        [ -L "$entry" ] || continue
        if [ ! -e "$entry" ]; then
            rm "$entry"
            info "Removed dangling $kind link: $(basename "$entry")"
        fi
    done

    # Create/refresh symlinks, first source wins
    for src in "${sources[@]}"; do
        [ -d "$src" ] || continue
        for entry in "$src"/*; do
            [ -e "$entry" ] || continue
            name=$(basename "$entry")
            case "$name" in *.bak.*|.DS_Store|__pycache__) continue ;; esac
            if [ -L "$target/$name" ]; then
                local current prior from_prior=0
                current=$(readlink "$target/$name")
                for prior in "${sources[@]}"; do
                    [ "$prior" = "$src" ] && break
                    [ "$current" = "$prior/$name" ] && from_prior=1
                done
                if [ "$from_prior" -eq 1 ]; then
                    warn "$kind '$name' exists in both repos; using $(dirname "$current")"
                    continue
                fi
            fi
            ln -sfn "$entry" "$target/$name"
        done
    done
}

# ---------------------------------------------------------------------------
# 1. Public repo
# ---------------------------------------------------------------------------
if ! clone_or_pull "$INSTALL_DIR" "$REPO_URL_SSH" "$REPO_URL_HTTPS" "Public"; then
    error "Failed to clone repository. Check your network and GitHub access."
fi
cd "$INSTALL_DIR"

# ---------------------------------------------------------------------------
# 2. Private repo (optional)
# ---------------------------------------------------------------------------
HAVE_PRIVATE=0
if [ "$USE_PRIVATE" = "1" ]; then
    if clone_or_pull "$PRIVATE_DIR" "$PRIVATE_REPO_URL_SSH" "$PRIVATE_REPO_URL_HTTPS" "Private"; then
        HAVE_PRIVATE=1
    else
        warn "Private repo not available (no access or offline) — continuing with public content only."
        warn "Retry later with: $INSTALL_DIR/setup.sh"
    fi
else
    info "CLAUDE_TOOLS_PRIVATE=0 — skipping private repo"
fi

# ---------------------------------------------------------------------------
# 3. Layout
# ---------------------------------------------------------------------------
if [ ! -d "$CLAUDE_DIR" ]; then
    info "Creating $CLAUDE_DIR directory..."
    mkdir -p "$CLAUDE_DIR"
fi
mkdir -p "$INSTALL_DIR/skills" "$INSTALL_DIR/agents" "$INSTALL_DIR/scripts"

# skills + scripts: union of public and private repos
SKILL_SOURCES=("$INSTALL_DIR/skills")
SCRIPT_SOURCES=("$INSTALL_DIR/scripts")
if [ "$HAVE_PRIVATE" -eq 1 ]; then
    SKILL_SOURCES+=("$PRIVATE_DIR/skills")
    SCRIPT_SOURCES+=("$PRIVATE_DIR/scripts")
fi
info "Linking skills..."
link_union "$CLAUDE_DIR/skills" "skill" "${SKILL_SOURCES[@]}"
info "Linking scripts..."
link_union "$CLAUDE_DIR/scripts" "script" "${SCRIPT_SOURCES[@]}"

# agents / CLAUDE.md: public repo only, whole-dir symlinks
# (adopt any pre-existing local copies first)
adopt_dir() {
    local local_dir="$1" repo_dir="$2" label="$3"
    if [ -d "$local_dir" ] && [ ! -L "$local_dir" ]; then
        info "Found local $label, copying to repo..."
        local item name
        for item in "$local_dir"/*; do
            [ -e "$item" ] || continue
            name=$(basename "$item")
            if [ -e "$repo_dir/$name" ]; then
                warn "$label '$name' already exists in repo, skipping"
            else
                cp -R "$item" "$repo_dir/"
                info "Copied $label: $name"
            fi
        done
        info "Backing up $label to $(basename "$local_dir")$BACKUP_SUFFIX"
        mv "$local_dir" "$local_dir$BACKUP_SUFFIX"
    fi
}
adopt_dir "$CLAUDE_DIR/agents" "$INSTALL_DIR/agents" "agents"

if [ -f "$CLAUDE_DIR/CLAUDE.md" ] && [ ! -L "$CLAUDE_DIR/CLAUDE.md" ]; then
    if [ -f "$INSTALL_DIR/CLAUDE.md" ]; then
        warn "CLAUDE.md already exists in repo, skipping (local version backed up)"
    else
        cp "$CLAUDE_DIR/CLAUDE.md" "$INSTALL_DIR/"
        info "Copied CLAUDE.md"
    fi
    info "Backing up CLAUDE.md to CLAUDE.md$BACKUP_SUFFIX"
    mv "$CLAUDE_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md$BACKUP_SUFFIX"
fi

info "Creating symlinks..."
ln -sfn "$INSTALL_DIR/agents" "$CLAUDE_DIR/agents"
ln -sfn "$INSTALL_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

# The public CLAUDE.md imports ~/.claude/CLAUDE.private.md. Point it at the
# private repo's CLAUDE.md when available; otherwise make sure an empty
# placeholder exists so the import always resolves. A hand-written regular
# file is left alone.
PRIVATE_CLAUDE_MD="$CLAUDE_DIR/CLAUDE.private.md"
if [ "$HAVE_PRIVATE" -eq 1 ] && [ -f "$PRIVATE_DIR/CLAUDE.md" ]; then
    ln -sfn "$PRIVATE_DIR/CLAUDE.md" "$PRIVATE_CLAUDE_MD"
elif [ -L "$PRIVATE_CLAUDE_MD" ] || [ ! -e "$PRIVATE_CLAUDE_MD" ]; then
    rm -f "$PRIVATE_CLAUDE_MD"
    : > "$PRIVATE_CLAUDE_MD"
fi

# ---------------------------------------------------------------------------
# 4. settings.json
# ---------------------------------------------------------------------------
# Claude Code rewrites settings.json itself, so it's copied (not linked) from
# the template on first install only. Afterwards, diff against the template
# by hand when you want to pick up changes.
SETTINGS_FILE="$CLAUDE_DIR/settings.json"
SETTINGS_TEMPLATE="$INSTALL_DIR/settings.template.json"
if [ ! -f "$SETTINGS_FILE" ]; then
    cp "$SETTINGS_TEMPLATE" "$SETTINGS_FILE"
    info "Created $SETTINGS_FILE from template"
else
    # Compare ignoring .mcpServers, which is machine-specific.
    if command -v jq &> /dev/null; then
        settings_differ=$(diff -q <(jq -S 'del(.mcpServers)' "$SETTINGS_TEMPLATE") <(jq -S 'del(.mcpServers)' "$SETTINGS_FILE") > /dev/null 2>&1 && echo 0 || echo 1)
    else
        settings_differ=$(diff -q "$SETTINGS_TEMPLATE" "$SETTINGS_FILE" > /dev/null 2>&1 && echo 0 || echo 1)
    fi
    if [ "$settings_differ" = "1" ]; then
        warn "settings.json differs from the repo template — review with:"
        echo "  diff <(jq -S . $SETTINGS_TEMPLATE) <(jq -S 'del(.mcpServers)' $SETTINGS_FILE)"
    fi
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
info "Setup complete!"
echo ""
echo "Installed:"
echo "  - Skills:    $CLAUDE_DIR/skills/<name> -> $INSTALL_DIR/skills/<name>"
[ "$HAVE_PRIVATE" -eq 1 ] && echo "                                    + $PRIVATE_DIR/skills/<name>"
echo "  - Scripts:   $CLAUDE_DIR/scripts/<file> -> $INSTALL_DIR/scripts/<file>"
[ "$HAVE_PRIVATE" -eq 1 ] && echo "                                    + $PRIVATE_DIR/scripts/<file>"
echo "  - Agents:    $CLAUDE_DIR/agents -> $INSTALL_DIR/agents"
echo "  - Config:    $CLAUDE_DIR/CLAUDE.md -> $INSTALL_DIR/CLAUDE.md"
if [ "$HAVE_PRIVATE" -eq 1 ] && [ -f "$PRIVATE_DIR/CLAUDE.md" ]; then
    echo "  - Private:   $PRIVATE_CLAUDE_MD -> $PRIVATE_DIR/CLAUDE.md"
else
    echo "  - Private:   $PRIVATE_CLAUDE_MD (empty placeholder)"
fi
echo "  - Settings:  $SETTINGS_FILE (from settings.template.json on first install)"
echo ""

# Check for uncommitted changes
REPOS=("$INSTALL_DIR")
[ "$HAVE_PRIVATE" -eq 1 ] && REPOS+=("$PRIVATE_DIR")
for repo in "${REPOS[@]}"; do
    if [ -n "$(git -C "$repo" status --porcelain)" ]; then
        warn "Uncommitted changes in $repo — review and commit when ready:"
        echo "  cd $repo && git status"
    fi
done
