#!/bin/bash
set -e

# Configuration
REPO_URL="git@github.com:jkarenko/claude-tools.git"
INSTALL_DIR="$HOME/.claude-tools"
CLAUDE_DIR="$HOME/.claude"

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
    git pull
else
    info "Cloning repository to $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Create ~/.claude if it doesn't exist
if [ ! -d "$CLAUDE_DIR" ]; then
    info "Creating $CLAUDE_DIR directory..."
    mkdir -p "$CLAUDE_DIR"
fi

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
    rm -rf "$CLAUDE_DIR/skills"
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
    rm -rf "$CLAUDE_DIR/agents"
fi

# Copy local CLAUDE.md into repo (if it exists and isn't already a symlink)
if [ -f "$CLAUDE_DIR/CLAUDE.md" ] && [ ! -L "$CLAUDE_DIR/CLAUDE.md" ]; then
    if [ -f "$INSTALL_DIR/CLAUDE.md" ]; then
        warn "CLAUDE.md already exists in repo, skipping (local version removed)"
    else
        cp "$CLAUDE_DIR/CLAUDE.md" "$INSTALL_DIR/"
        info "Copied CLAUDE.md"
    fi
    rm "$CLAUDE_DIR/CLAUDE.md"
fi

# Create symlinks
info "Creating symlinks..."
ln -sf "$INSTALL_DIR/skills" "$CLAUDE_DIR/skills"
ln -sf "$INSTALL_DIR/agents" "$CLAUDE_DIR/agents"
ln -sf "$INSTALL_DIR/CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"

echo ""
info "Setup complete!"
echo ""
echo "Installed:"
echo "  - Skills:   $CLAUDE_DIR/skills -> $INSTALL_DIR/skills"
echo "  - Agents:   $CLAUDE_DIR/agents -> $INSTALL_DIR/agents"
echo "  - Config:   $CLAUDE_DIR/CLAUDE.md -> $INSTALL_DIR/CLAUDE.md"
echo ""

# Check for uncommitted changes
cd "$INSTALL_DIR"
if [ -n "$(git status --porcelain)" ]; then
    warn "New files were copied. Review and commit when ready:"
    echo "  cd $INSTALL_DIR && git status"
fi
