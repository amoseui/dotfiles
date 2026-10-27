# Show handoff availability without reading files or scanning repository status.
_dotfiles_handoff_precmd() {
  local handoff_root
  typeset -g _dotfiles_handoff_prompt=''
  handoff_root=$(command git rev-parse --show-toplevel 2>/dev/null) || handoff_root=$PWD

  if [[ -f "$handoff_root/HANDOFF.amoseui.md" || -f "$handoff_root/HANDOFF.md" ]]; then
    _dotfiles_handoff_prompt='%F{yellow}[handoff]%f'
  fi
  return 0
}

autoload -Uz add-zsh-hook
add-zsh-hook precmd _dotfiles_handoff_precmd
setopt prompt_subst

# Preserve the theme's right prompt and avoid duplication when re-sourced.
if [[ "$RPROMPT" != *'${_dotfiles_handoff_prompt}'* ]]; then
  RPROMPT+='${_dotfiles_handoff_prompt:+ }${_dotfiles_handoff_prompt}'
fi
