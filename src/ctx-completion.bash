# Bash completion for ctx
_ctx_completion() {
  local cur prev config_root project_dir archive_dir
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev="${COMP_WORDS[COMP_CWORD-1]}"
  config_root="${XDG_CONFIG_HOME:-$HOME/.config}/ctx"
  project_dir="$config_root/projects"
  archive_dir="$config_root/archived"

  _ctx_active_contexts() {
    local file
    [[ -d "$project_dir" ]] || return 0
    for file in "$project_dir"/*.conf; do
      [[ -e "$file" ]] || continue
      basename "$file" .conf
    done
  }

  _ctx_archived_contexts() {
    local file
    [[ -d "$archive_dir" ]] || return 0
    for file in "$archive_dir"/*.conf; do
      [[ -e "$file" ]] || continue
      basename "$file" .conf
    done
  }

  _ctx_extensions() {
    local dir path name
    local -A seen=()
    local -a dirs=()
    IFS=: read -r -a dirs <<< "$PATH"
    for dir in "${dirs[@]}"; do
      [[ -n "$dir" && -d "$dir" ]] || continue
      for path in "$dir"/ctx-ext-*; do
        [[ -f "$path" && -x "$path" ]] || continue
        name="${path##*/}"
        name="${name#ctx-ext-}"
        [[ "$name" =~ ^[a-z][a-z0-9-]{0,47}$ ]] || continue
        seen["$name"]=1
      done
    done
    printf '%s\n' "${!seen[@]}"
  }

  local first="${COMP_WORDS[1]:-}"
  case "$COMP_CWORD" in
    1)
      local commands="n new s switch use x exit leave l list d delete rm arc archive unarc unarchive current show edit service extensions a agent"
      local extensions
      extensions="$(_ctx_extensions)"
      COMPREPLY=( $(compgen -W "$commands $extensions" -- "$cur") )
      return 0
      ;;
  esac

  case "$first" in
    s|switch|use)
      COMPREPLY=( $(compgen -W "$(_ctx_active_contexts)" -- "$cur") )
      ;;
    d|delete|rm)
      COMPREPLY=( $(compgen -W "$(_ctx_active_contexts; _ctx_archived_contexts)" -- "$cur") )
      ;;
    arc|archive)
      COMPREPLY=( $(compgen -W "$(_ctx_active_contexts)" -- "$cur") )
      ;;
    unarc|unarchive)
      COMPREPLY=( $(compgen -W "$(_ctx_archived_contexts)" -- "$cur") )
      ;;
    show|edit)
      COMPREPLY=( $(compgen -W "$(_ctx_active_contexts; _ctx_archived_contexts)" -- "$cur") )
      ;;
    l|list)
      COMPREPLY=( $(compgen -W "--archived --all archived all" -- "$cur") )
      ;;
    a)
      if [[ "$COMP_CWORD" -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "p g d a x plan progress deviation approve reject" -- "$cur") )
      fi
      ;;
    agent)
      if [[ "$COMP_CWORD" -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "plan progress deviation approve reject" -- "$cur") )
      fi
      ;;
    service)
      if [[ "$COMP_CWORD" -eq 2 ]]; then
        COMPREPLY=( $(compgen -W "$(_ctx_active_contexts)" -- "$cur") )
      fi
      ;;
  esac
}

complete -F _ctx_completion ctx
