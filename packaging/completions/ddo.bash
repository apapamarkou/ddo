# Bash completion for ddo
_ddo() {
    local cur prev words cword
    _init_completion || return

    local commands="analyze cleanup dry-run restore update list-languages"

    case "${prev}" in
        ddo)
            COMPREPLY=( $(compgen -W "${commands}" -- "${cur}") )
            return 0
            ;;
        --config)
            COMPREPLY=( $(compgen -f -- "${cur}") )
            return 0
            ;;
    esac

    case "${words[1]}" in
        cleanup|dry-run|analyze|list-languages|update|restore)
            COMPREPLY=( $(compgen -W "--config --verbose --yes --dry-run --help" -- "${cur}") )
            ;;
        *)
            COMPREPLY=( $(compgen -W "${commands} --help" -- "${cur}") )
            ;;
    esac
}

complete -F _ddo ddo
