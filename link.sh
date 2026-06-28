#!/bin/bash

DOTFILES_PATH=$(cd "$(dirname "$0")" && pwd)

GITCONFIG_PATH="$DOTFILES_PATH/git/gitconfig"
GITIGNORE_PATH="$DOTFILES_PATH/git/gitignore"
TMUX_PATH="$DOTFILES_PATH/tmux/tmux.conf"
VIMRC_PATH="$DOTFILES_PATH/vim/vimrc"
ZSHRC_PATH="$DOTFILES_PATH/zsh/zshrc"

ln -sf $GITCONFIG_PATH ~/.gitconfig
ln -sf $GITIGNORE_PATH ~/.gitignore
ln -sf $TMUX_PATH ~/.tmux.conf
ln -sf $ZSHRC_PATH ~/.zshrc

mv -v ~/.vimrc ~/.vimrc.old 2> /dev/null
ln -sf $VIMRC_PATH ~/.vimrc

vim +PlugInstall +qall

# antigen for zsh
curl -L git.io/antigen > ~/.antigen.zsh

# ---- AI agent configs ----

link_file() {
    # link_file <src> <dst>
    local src="$1"
    local dst="$2"
    [ -e "$src" ] || return 0
    mkdir -p "$(dirname "$dst")"
    if [ -e "$dst" ] && [ ! -L "$dst" ]; then
        mv -v "$dst" "$dst.old"
    fi
    ln -sfn "$src" "$dst"
}

link_dir_contents() {
    # link every file/subdir inside <src> into <dst>
    local src="$1"
    local dst="$2"
    [ -d "$src" ] || return 0
    mkdir -p "$dst"
    for entry in "$src"/* "$src"/.[!.]*; do
        [ -e "$entry" ] || continue
        local name
        name=$(basename "$entry")
        [ "$name" = ".gitkeep" ] && continue
        link_file "$entry" "$dst/$name"
    done
}

# Claude Code
link_file "$DOTFILES_PATH/claude/settings.json" ~/.claude/settings.json
link_file "$DOTFILES_PATH/claude/CLAUDE.md" ~/.claude/CLAUDE.md
link_file "$DOTFILES_PATH/claude/statusline-command.sh" ~/.claude/statusline-command.sh
link_dir_contents "$DOTFILES_PATH/claude/agents" ~/.claude/agents
link_dir_contents "$DOTFILES_PATH/claude/commands" ~/.claude/commands
link_dir_contents "$DOTFILES_PATH/claude/skills" ~/.claude/skills
link_dir_contents "$DOTFILES_PATH/claude/hooks" ~/.claude/hooks

# Hermes (custom skills only — bundled skills are managed by Hermes itself)
# Link individual skills, not whole category dirs, since custom skills live
# inside bundled categories (e.g. note-taking/).
link_file "$DOTFILES_PATH/hermes/skills/note-taking/brief-morning"          ~/.hermes/skills/note-taking/brief-morning
link_file "$DOTFILES_PATH/hermes/skills/note-taking/daily-notes-automation" ~/.hermes/skills/note-taking/daily-notes-automation
link_file "$DOTFILES_PATH/hermes/skills/note-taking/hermes"                 ~/.hermes/skills/note-taking/hermes
link_file "$DOTFILES_PATH/hermes/skills/note-taking/pkm-collect"            ~/.hermes/skills/note-taking/pkm-collect

# Ghostty
link_file "$DOTFILES_PATH/ghostty/config" ~/.config/ghostty/config

# cmux
link_file "$DOTFILES_PATH/cmux/cmux.json" ~/.config/cmux/cmux.json
