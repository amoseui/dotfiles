#!/bin/bash

DOTFILES_PATH=$(cd "$(dirname "$0")" && pwd)

GITCONFIG_PATH="$DOTFILES_PATH/git/gitconfig"
GITIGNORE_PATH="$DOTFILES_PATH/git/gitignore"
VIMRC_PATH="$DOTFILES_PATH/vim/vimrc"
ZSHRC_PATH="$DOTFILES_PATH/zsh/zshrc"

ln -fs $GITCONFIG_PATH $HOME/.gitconfig
ln -fs $GITIGNORE_PATH $HOME/.gitignore
ln -fs $VIMRC_PATH $HOME/.vimrc
ln -fs $ZSHRC_PATH $HOME/.zshrc
