# Keep HEAD display independent of the expensive working-tree scan.
autoload -Uz add-zsh-hook
(( $+functions[_dotfiles_git_cleanup] )) && _dotfiles_git_cleanup

typeset -g _dotfiles_git_repo='' _dotfiles_git_head='' _dotfiles_git_ref=''
typeset -g _dotfiles_git_root=''
typeset -g _dotfiles_git_dirty='?'
typeset -gi _dotfiles_git_fd=-1
typeset -gi _dotfiles_git_request=${_dotfiles_git_request:-0}
typeset -gi _dotfiles_git_epoch=0 _dotfiles_git_job_epoch=0 _dotfiles_git_running=0
typeset -g _dotfiles_git_buffer=''
zmodload zsh/zpty
zmodload zsh/system

_dotfiles_git_context() {
  emulate -L zsh
  local gitdir root ref head
  _dotfiles_git_repo='' _dotfiles_git_head='' _dotfiles_git_ref='' _dotfiles_git_root=''
  gitdir=$(GIT_OPTIONAL_LOCKS=0 command git rev-parse --absolute-git-dir 2>/dev/null) || return 1
  root=$(GIT_OPTIONAL_LOCKS=0 command git rev-parse --show-toplevel 2>/dev/null) || return 1
  ref=$(GIT_OPTIONAL_LOCKS=0 command git symbolic-ref --quiet --short HEAD 2>/dev/null)
  head=$(GIT_OPTIONAL_LOCKS=0 command git rev-parse --verify HEAD 2>/dev/null)
  [[ -n $ref ]] || ref=${head[1,10]}
  [[ -n $ref ]] || ref='?'
  _dotfiles_git_repo="${gitdir:A}:${root:A}"
  _dotfiles_git_head=$head
  _dotfiles_git_ref=$ref
  _dotfiles_git_root=$root
}

_dotfiles_git_refresh() {
  emulate -L zsh
  local repo=$_dotfiles_git_repo head=$_dotfiles_git_head ref=$_dotfiles_git_ref
  _dotfiles_git_context
  if [[ $repo != $_dotfiles_git_repo || $head != $_dotfiles_git_head || $ref != $_dotfiles_git_ref ]]; then
    _dotfiles_git_cleanup
    _dotfiles_git_dirty='?'
  fi
  return 0
}

_dotfiles_git_precmd() {
  emulate -L zsh
  _dotfiles_git_running=0
  _dotfiles_git_refresh
  [[ -n $_dotfiles_git_repo ]] || return 0
  # Empty Enter must never cancel a scan that is still making progress.
  (( _dotfiles_git_fd >= 0 )) && return 0
  _dotfiles_git_dirty='?'
  _dotfiles_git_start
  return 0
}

_dotfiles_git_preexec() {
  emulate -L zsh
  # Any command may mutate files (including aliases, functions and redirects).
  # Compare epochs instead of guessing from the command text. Many commands
  # during one scan coalesce into one followup at the newest epoch.
  (( ++_dotfiles_git_epoch ))
  _dotfiles_git_running=1
  _dotfiles_git_dirty='?'
  return 0
}

_dotfiles_git_chpwd() {
  _dotfiles_git_refresh
}

_dotfiles_git_worker() {
  emulate -L zsh
  unsetopt monitor
  # zpty owns a new session/process group. Kill the whole group on teardown,
  # including git's descendants, even when the parent closes us mid-scan.
  trap 'kill -KILL -- -$sysparams[pid] 2>/dev/null' HUP TERM
  local output result='?' answer
  output=$(GIT_OPTIONAL_LOCKS=0 command git -C "$_dotfiles_git_root" status --porcelain --ignore-submodules=dirty 2>/dev/null)
  if (( $? == 0 )); then
    result=o
    [[ -n $output ]] && result=x
  fi
  print -r -- "$_dotfiles_git_request $result"
  # Keep the session leader alive until the parent consumes the result.
  read -r answer
}

_dotfiles_git_start() {
  emulate -L zsh
  (( ++_dotfiles_git_request ))
  _dotfiles_git_job_epoch=$_dotfiles_git_epoch
  _dotfiles_git_buffer=''
  if zpty -b _dotfiles_git_worker _dotfiles_git_worker; then
    _dotfiles_git_fd=$REPLY
    [[ -o interactive ]] && zle -F $_dotfiles_git_fd _dotfiles_git_callback
  fi
  return 0
}

_dotfiles_git_callback() {
  emulate -L zsh
  [[ $1 == $_dotfiles_git_fd ]] || return 0
  local part result
  local -i request=$_dotfiles_git_request epoch=$_dotfiles_git_job_epoch rc
  if zpty -r _dotfiles_git_worker part; then
    _dotfiles_git_buffer+=$part
    [[ $_dotfiles_git_buffer == *$'\n' ]] || return 0
    result=${_dotfiles_git_buffer//$'\r'/}
    result=${result%$'\n'}
  else
    rc=$?
    # A live nonblocking PTY may simply have no complete data yet.
    (( rc == 1 )) && [[ -z $2 ]] && return 0
  fi
  _dotfiles_git_refresh
  (( request == _dotfiles_git_request )) || return 0
  _dotfiles_git_cleanup
  _dotfiles_git_dirty='?'
  if (( epoch == _dotfiles_git_epoch && ! _dotfiles_git_running )); then
    case $result in
      "$request o") _dotfiles_git_dirty=o ;;
      "$request x") _dotfiles_git_dirty=x ;;
    esac
  elif (( ! _dotfiles_git_running )); then
    _dotfiles_git_start
  fi
  if [[ -o interactive ]]; then
    zle .reset-prompt 2>/dev/null
    zle -R 2>/dev/null
  fi
  return 0
}

git_prompt_info() {
  emulate -L zsh
  [[ -n $_dotfiles_git_repo ]] || return 0
  local mark=' ?'
  case $_dotfiles_git_dirty in
    o) mark=${ZSH_THEME_GIT_PROMPT_CLEAN:-' o'} ;;
    x) mark=${ZSH_THEME_GIT_PROMPT_DIRTY:-' x'} ;;
  esac
  print -rn -- "${ZSH_THEME_GIT_PROMPT_PREFIX}${_dotfiles_git_ref//\%/%%}${mark}${ZSH_THEME_GIT_PROMPT_SUFFIX}"
}

_dotfiles_git_cleanup() {
  emulate -L zsh
  if (( _dotfiles_git_fd >= 0 )); then
    [[ -o interactive ]] && zle -F $_dotfiles_git_fd 2>/dev/null
    zpty -d _dotfiles_git_worker 2>/dev/null
    _dotfiles_git_fd=-1
  fi
  (( ++_dotfiles_git_request ))
  return 0
}

_dotfiles_git_detach_omz() {
  emulate -L zsh
  # Resolve OMZ's one-shot deferred registration while the final theme is
  # available, then remove only the handler replaced by this helper.
  (( $+functions[_defer_async_git_register] )) && _defer_async_git_register
  if (( ${+_omz_async_functions} )); then
    _omz_async_functions=( ${_omz_async_functions:#_omz_git_prompt_info} )
  fi
  local -i fd=-1 pid=-1
  (( ${+_OMZ_ASYNC_FDS} )) && fd=${_OMZ_ASYNC_FDS[_omz_git_prompt_info]:--1}
  (( ${+_OMZ_ASYNC_PIDS} )) && pid=${_OMZ_ASYNC_PIDS[_omz_git_prompt_info]:--1}
  if (( fd >= 0 && pid > 1 )) && { true <&$fd } 2>/dev/null; then
    [[ -o interactive ]] && zle -F $fd 2>/dev/null
    exec {fd}<&-
    # Match OMZ's process ownership contract for a pre-existing request.
    if [[ -o monitor ]]; then
      kill -TERM -- -$pid 2>/dev/null
    else
      kill -TERM -- $pid 2>/dev/null
    fi
  fi
  unset '_OMZ_ASYNC_FDS[_omz_git_prompt_info]' \
      '_OMZ_ASYNC_PIDS[_omz_git_prompt_info]' \
      '_OMZ_ASYNC_OUTPUT[_omz_git_prompt_info]'
  return 0
}

_dotfiles_git_detach_omz

add-zsh-hook -d precmd _dotfiles_git_precmd
add-zsh-hook precmd _dotfiles_git_precmd
add-zsh-hook -d preexec _dotfiles_git_preexec
add-zsh-hook preexec _dotfiles_git_preexec
add-zsh-hook -d chpwd _dotfiles_git_chpwd
add-zsh-hook chpwd _dotfiles_git_chpwd
add-zsh-hook -d zshexit _dotfiles_git_cleanup
add-zsh-hook zshexit _dotfiles_git_cleanup
