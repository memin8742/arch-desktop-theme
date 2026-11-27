# Loaded only by Arch Terminal; does not change the account's login shell.
[[ -o interactive ]] || return
autoload -Uz add-zsh-hook
setopt prompt_percent hist_ignore_dups hist_reduce_blanks inc_append_history
unsetopt prompt_subst
HISTFILE=${HISTFILE:-$HOME/.zsh_history}
HISTSIZE=${HISTSIZE:-10000}
SAVEHIST=${SAVEHIST:-10000}
bindkey -e

PROMPT=$'%F{#49AEE6}┌──(%B%n@%m%b)-[%F{#FFFFFF}%B%~%b%F{#49AEE6}]\n└─%# %f'
RPROMPT=''
ZSH_AUTOSUGGEST_HIGHLIGHT_STYLE='fg=#57758A'
[[ -r /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh ]] && source /usr/share/zsh/plugins/zsh-autosuggestions/zsh-autosuggestions.zsh
[[ -r /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh ]] && source /usr/share/zsh/plugins/zsh-syntax-highlighting/zsh-syntax-highlighting.zsh
typeset -gA ZSH_HIGHLIGHT_STYLES
ZSH_HIGHLIGHT_STYLES[default]='fg=white'
ZSH_HIGHLIGHT_STYLES[unknown-token]='fg=white,underline'
for _arch_key in command builtin function alias hashed-command; do
  ZSH_HIGHLIGHT_STYLES[$_arch_key]='fg=#80CAEA,bold'
done
ZSH_HIGHLIGHT_STYLES[path]='fg=#49AEE6,bold'
ZSH_HIGHLIGHT_STYLES[single-hyphen-option]='fg=#5EBDAB'
ZSH_HIGHLIGHT_STYLES[double-hyphen-option]='fg=#5EBDAB'
unset _arch_key
export LS_COLORS='di=01;34:ln=01;36:ex=01;32:or=33:mi=33'
alias ls='ls --color=auto'
alias grep='grep --color=auto'

# OSC 7 is a percent-encoded local URI. CWD never comes from a screenshot.
_arch_cwd() {
  local uri
  uri=$(python3 -c 'import pathlib; print(pathlib.Path.cwd().as_uri())')
  printf '\e]7;%s\a' "$uri"
}
_arch_started() { typeset -g _arch_start=$SECONDS; }
_arch_finished() {
  if [[ -n ${_arch_start-} && $((SECONDS - _arch_start)) -ge 15 ]]; then
    "$HOME/.local/bin/arch-theme" notify "${ARCH_THEME_WINDOW_PID:-}" &!
  fi
  unset _arch_start
  _arch_cwd
}
add-zsh-hook preexec _arch_started
add-zsh-hook precmd _arch_finished

# Selection belongs to the editable command buffer, not old terminal output.
# MARK stays anchored when the direction reverses, so the region contracts.
_arch_select() {
  (( REGION_ACTIVE )) || MARK=$CURSOR
  REGION_ACTIVE=1
  case $WIDGET in
    arch-select-left) zle .backward-char;;
    arch-select-right) zle .forward-char;;
    arch-select-word-left) zle .backward-word;;
    arch-select-word-right) zle .forward-word;;
    arch-select-up) zle .up-line;;
    arch-select-down) zle .down-line;;
    arch-select-top) CURSOR=0;;
    arch-select-bottom) CURSOR=${#BUFFER};;
  esac
  REGION_ACTIVE=1
}
for _arch_widget in left right word-left word-right up down top bottom; do
  zle -N arch-select-$_arch_widget _arch_select
done
bindkey '^[[1;2D' arch-select-left
bindkey '^[[1;2C' arch-select-right
bindkey '^[[1;6D' arch-select-word-left
bindkey '^[[1;6C' arch-select-word-right
bindkey '^[[1;2A' arch-select-up
bindkey '^[[1;2B' arch-select-down
bindkey '^[[1;6A' arch-select-top
bindkey '^[[1;6B' arch-select-bottom
bindkey '^[[1;5D' backward-word
bindkey '^[[1;5C' forward-word
_arch_copy_region() {
  (( REGION_ACTIVE && CURSOR != MARK )) || return 0
  local start=$((CURSOR < MARK ? CURSOR : MARK))
  local end=$((CURSOR > MARK ? CURSOR : MARK))
  print -rn -- "${BUFFER[$((start+1)),$end]}" | xclip -selection clipboard
}
zle -N arch-copy-region _arch_copy_region
bindkey '^[[99;5u' arch-copy-region
_arch_replace() {
  if (( REGION_ACTIVE && CURSOR != MARK )); then
    zle .kill-region
    REGION_ACTIVE=0
    [[ $WIDGET == arch-backspace || $WIDGET == arch-delete ]] && return
  fi
  case $WIDGET in
    arch-insert) zle .self-insert;;
    arch-backspace) zle .backward-delete-char;;
    arch-delete) zle .delete-char;;
    arch-paste) zle .bracketed-paste;;
  esac
}
zle -N arch-insert _arch_replace
zle -N arch-backspace _arch_replace
zle -N arch-delete _arch_replace
zle -N arch-paste _arch_replace
bindkey -R ' '-'~' arch-insert
bindkey '^?' arch-backspace
bindkey '^[[3~' arch-delete
bindkey '^[[200~' arch-paste
bindkey '^V' quoted-insert
bindkey '^R' history-incremental-search-backward
unset _arch_widget
