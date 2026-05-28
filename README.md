# dotfiles

Personal dotfiles configuration for Git, Vim, Tmux, and Zsh.

## Contents

- **git/** - Git configuration and global gitignore
- **vim/** - Vim configuration with plugin support
- **tmux/** - Tmux configuration
- **zsh/** - Zsh configuration
- **claude/** - Claude Code settings, global memory, custom agents and commands

## Prerequisites

Before installation, ensure you have the following installed:

- Git
- Vim
- Tmux
- Zsh
- curl (for downloading antigen)

## Installation

1. Clone this repository:
```bash
git clone <repository-url> ~/dotfiles
cd ~/dotfiles
```

2. Run the installation script:
```bash
chmod +x link.sh
./link.sh
```

The installation script will:
- Create symbolic links for all configuration files in your home directory
- Backup existing `.vimrc` to `.vimrc.old` (if exists)
- Install Vim plugins automatically
- Download and install Antigen for Zsh plugin management

## What Gets Installed

The script creates the following symbolic links:
- `~/.gitconfig` → `~/dotfiles/git/gitconfig`
- `~/.gitignore` → `~/dotfiles/git/gitignore`
- `~/.tmux.conf` → `~/dotfiles/tmux/tmux.conf`
- `~/.vimrc` → `~/dotfiles/vim/vimrc`
- `~/.zshrc` → `~/dotfiles/zsh/zshrc`

Claude Code configs (per-file links, parent dirs created if missing):
- `~/.claude/settings.json` → `~/dotfiles/claude/settings.json`
- `~/.claude/CLAUDE.md` → `~/dotfiles/claude/CLAUDE.md`
- `~/.claude/agents/*` → `~/dotfiles/claude/agents/*`
- `~/.claude/commands/*` → `~/dotfiles/claude/commands/*`

Drop new agent or command files into `claude/agents/` or `claude/commands/`
and re-run `./link.sh` to pick them up.

Additionally:
- `~/.antigen.zsh` - Antigen plugin manager for Zsh

## Post-Installation

After installation:
1. Restart your terminal or run `source ~/.zshrc` to apply Zsh changes
2. Start a new Tmux session to use the new configuration
3. Open Vim to verify plugins are installed correctly

## Updating

To update your dotfiles:
```bash
cd ~/dotfiles
git pull
./link.sh
```

## Uninstallation

To remove the dotfiles, simply delete the symbolic links:
```bash
rm ~/.gitconfig ~/.gitignore ~/.tmux.conf ~/.vimrc ~/.zshrc ~/.antigen.zsh
rm ~/.claude/settings.json ~/.claude/CLAUDE.md
# also remove any symlinks under ~/.claude/agents, ~/.claude/commands
```

And restore your backups if needed:
```bash
mv ~/.vimrc.old ~/.vimrc
```
