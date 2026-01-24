#!/bin/bash
set -e

# Configuration
REPO_URL_SSH="git@github.com:jkarenko/.claude-tools.git"
REPO_URL_HTTPS="https://github.com/jkarenko/.claude-tools.git"
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

# Check if running from the repo or needs to clone
if [ -d "$INSTALL_DIR/.git" ]; then
    info "Repository already exists at $INSTALL_DIR"
    cd "$INSTALL_DIR"
    info "Pulling latest changes..."
    if ! git pull; then
        warn "git pull failed. Possible causes:"
        echo "  - Uncommitted local changes: run 'git stash' or 'git commit'"
        echo "  - Merge conflicts: resolve manually in $INSTALL_DIR"
        echo "  - Network issues: check your connection"
        echo ""
        warn "Continuing with existing local version..."
    fi
else
    info "Cloning repository to $INSTALL_DIR..."
    if git clone "$REPO_URL_SSH" "$INSTALL_DIR" 2>/dev/null; then
        info "Cloned via SSH"
    elif git clone "$REPO_URL_HTTPS" "$INSTALL_DIR"; then
        info "Cloned via HTTPS"
    else
        error "Failed to clone repository. Check your network and GitHub access."
    fi
    cd "$INSTALL_DIR"
fi

# Create ~/.claude if it doesn't exist
if [ ! -d "$CLAUDE_DIR" ]; then
    info "Creating $CLAUDE_DIR directory..."
    mkdir -p "$CLAUDE_DIR"
fi

# Ensure target directories exist in repo
mkdir -p "$INSTALL_DIR/skills" "$INSTALL_DIR/agents" "$INSTALL_DIR/templates"

# Copy local skills into repo (if they exist and aren't already symlinks)
if [ -d "$CLAUDE_DIR/skills" ] && [ ! -L "$CLAUDE_DIR/skills" ]; then
    info "Found local skills, copying to repo..."
    for skill in "$CLAUDE_DIR/skills"/*/; do
        if [ -d "$skill" ]; then
            skill_name=$(basename "$skill")
            if [ -d "$INSTALL_DIR/skills/$skill_name" ]; then
                warn "Skill '$skill_name' already exists in repo, skipping"
            else
                cp -r "$skill" "$INSTALL_DIR/skills/"
                info "Copied skill: $skill_name"
            fi
        fi
    done
    info "Backing up skills to skills$BACKUP_SUFFIX"
    mv "$CLAUDE_DIR/skills" "$CLAUDE_DIR/skills$BACKUP_SUFFIX"
fi

# Copy local agents into repo (if they exist and aren't already symlinks)
if [ -d "$CLAUDE_DIR/agents" ] && [ ! -L "$CLAUDE_DIR/agents" ]; then
    info "Found local agents, copying to repo..."
    for agent in "$CLAUDE_DIR/agents"/*.md; do
        if [ -f "$agent" ]; then
            agent_name=$(basename "$agent")
            if [ -f "$INSTALL_DIR/agents/$agent_name" ]; then
                warn "Agent '$agent_name' already exists in repo, skipping"
            else
                cp "$agent" "$INSTALL_DIR/agents/"
                info "Copied agent: $agent_name"
            fi
        fi
    done
    info "Backing up agents to agents$BACKUP_SUFFIX"
    mv "$CLAUDE_DIR/agents" "$CLAUDE_DIR/agents$BACKUP_SUFFIX"
fi

# Copy local templates into repo (if they exist and aren't already symlinks)
if [ -d "$CLAUDE_DIR/templates" ] && [ ! -L "$CLAUDE_DIR/templates" ]; then
    info "Found local templates, copying to repo..."
    # Copy subdirectories
    for template_dir in "$CLAUDE_DIR/templates"/*/; do
        if [ -d "$template_dir" ]; then
            template_name=$(basename "$template_dir")
            if [ -d "$INSTALL_DIR/templates/$template_name" ]; then
                warn "Template dir '$template_name' already exists in repo, skipping"
            else
                cp -r "$template_dir" "$INSTALL_DIR/templates/"
                info "Copied template dir: $template_name"
            fi
        fi
    done
    # Copy loose files
    for template_file in "$CLAUDE_DIR/templates"/*; do
        if [ -f "$template_file" ]; then
            template_name=$(basename "$template_file")
            if [ -f "$INSTALL_DIR/templates/$template_name" ]; then
                warn "Template file '$template_name' already exists in repo, skipping"
            else
                cp "$template_file" "$INSTALL_DIR/templates/"
                info "Copied template file: $template_name"
            fi
        fi
    done
    info "Backing up templates to templates$BACKUP_SUFFIX"
    mv "$CLAUDE_DIR/templates" "$CLAUDE_DIR/templates$BACKUP_SUFFIX"
fi

# Copy local CLAUDE.md into repo (if it exists and isn't already a symlink)
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

# Create symlinks (-n flag prevents creating symlink inside existing symlinked dir)
info "Creating symlinks..."
ln -sfn "$INSTALL_DIR/skills" "$CLAUDE_DIR/skills"
ln -sfn "$INSTALL_DIR/agents" "$CLAUDE_DIR/agents"
ln -sfn "$INSTALL_DIR/templates" "$CLAUDE_DIR/templates"
ln -sfn "$INSTALL_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

echo ""
info "Setup complete!"
echo ""
echo "Installed:"
echo "  - Skills:    $CLAUDE_DIR/skills -> $INSTALL_DIR/skills"
echo "  - Agents:    $CLAUDE_DIR/agents -> $INSTALL_DIR/agents"
echo "  - Templates: $CLAUDE_DIR/templates -> $INSTALL_DIR/templates"
echo "  - Config:    $CLAUDE_DIR/CLAUDE.md -> $INSTALL_DIR/CLAUDE.md"
echo ""

# Check for uncommitted changes
cd "$INSTALL_DIR"
if [ -n "$(git status --porcelain)" ]; then
    warn "New files were copied. Review and commit when ready:"
    echo "  cd $INSTALL_DIR && git status"
fi
