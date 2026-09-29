#!/usr/bin/env bash
# foci/install.sh — bootstrap entry point for the klipper-foci installer.
# curl -sL https://raw.githubusercontent.com/foci-rs/foci/main/install.sh | bash

foci_bootstrap() {
    local version="" args=()
    while [ $# -gt 0 ]; do
        case "$1" in
            --version)
                if [ $# -lt 2 ]; then
                    echo "--version requires a value" >&2
                    return 1
                fi
                version="$2"; shift 2 ;;
            *) args+=("$1"); shift ;;
        esac
    done

    local api_url="https://api.github.com/repos/foci-rs/klipper-foci/releases/latest"
    [ -n "$version" ] && api_url="https://api.github.com/repos/foci-rs/klipper-foci/releases/tags/$version"

    local release_json
    if ! release_json="$(curl -fsSL "$api_url")"; then
        echo "Could not reach the GitHub API to resolve a klipper-foci release." >&2
        return 1
    fi

    local installer_url sha_url
    installer_url="$(printf '%s' "$release_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next(a["browser_download_url"] for a in d["assets"] if a["name"]=="klipper-foci-installer.sh"))')"
    sha_url="$(printf '%s' "$release_json" | python3 -c 'import json,sys; d=json.load(sys.stdin); print(next(a["browser_download_url"] for a in d["assets"] if a["name"]=="klipper-foci-installer.sh.sha256"))')"

    local tmp_dir installer_path sha_path
    tmp_dir="$(mktemp -d)"
    installer_path="$tmp_dir/klipper-foci-installer.sh"
    sha_path="$tmp_dir/klipper-foci-installer.sh.sha256"

    curl -fsSL "$installer_url" -o "$installer_path"
    curl -fsSL "$sha_url" -o "$sha_path"

    if ! (cd "$tmp_dir" && shasum -a 256 -c klipper-foci-installer.sh.sha256 >/dev/null 2>&1); then
        echo "checksum verification failed for the downloaded installer" >&2
        return 1
    fi

    exec bash "$installer_path" "${args[@]}"
}

# Not sourced under bats: invoke directly when run standalone.
if [ "${BATS_TEST_FILENAME:-}" = "" ] && [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    foci_bootstrap "$@"
fi
