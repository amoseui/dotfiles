#!/bin/bash

DOTFILES_PATH=$(cd "$(dirname "$0")" && pwd)

GITCONFIG_PATH="$DOTFILES_PATH/git/gitconfig"
GITIGNORE_PATH="$DOTFILES_PATH/git/gitignore"
VIMRC_PATH="$DOTFILES_PATH/vim/vimrc"
ZSHRC_PATH="$DOTFILES_PATH/zsh/zshrc"

ln -sf $GITCONFIG_PATH ~/.gitconfig
ln -sf $GITIGNORE_PATH ~/.gitignore
ln -sf $ZSHRC_PATH ~/.zshrc

mv -v ~/.vimrc ~/.vimrc.old 2> /dev/null
ln -sf $VIMRC_PATH ~/.vimrc

vim +PlugInstall +qall

# antigen for zsh
curl -L git.io/antigen > ~/.antigen.zsh
