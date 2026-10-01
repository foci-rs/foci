setup() {
  export TEST_DIR="$BATS_TMPDIR/foci-bootstrap-$$"
  mkdir -p "$TEST_DIR"

  # Stub curl and exec so the test never touches the network or replaces
  # the bats process.
  curl() {
    case "$*" in
      *api.github.com*releases/latest*)
        cat "$TEST_DIR/latest_release.json" ;;
      *api.github.com*releases/tags/*)
        cat "$TEST_DIR/tagged_release.json" ;;
      *installer.sh.sha256*)
        cp "$TEST_DIR/installer.sh.sha256" "$(_curl_output_arg "$@")" ;;
      *installer.sh*)
        cp "$TEST_DIR/installer.sh" "$(_curl_output_arg "$@")" ;;
      *) echo "unexpected curl: $*" >&2; return 1 ;;
    esac
  }
  _curl_output_arg() {
    while [ $# -gt 0 ]; do
      if [ "$1" = "-o" ]; then echo "$2"; return; fi
      shift
    done
  }
  # Only intercept the real "exec bash <installer>" call this script makes.
  # A bare override would also swallow exec calls made deep inside python3's
  # asdf shim (its dispatch script itself calls `exec asdf exec ...`),
  # polluting exec.log with unrelated noise.
  exec() {
    case "$1" in
      bash) echo "exec:$*" >> "$TEST_DIR/exec.log" ;;
      *) command exec "$@" ;;
    esac
  }
  export -f curl _curl_output_arg exec

  printf 'echo real installer ran\n' > "$TEST_DIR/installer.sh"
  shasum -a 256 "$TEST_DIR/installer.sh" | awk '{print $1"  klipper-foci-installer.sh"}' > "$TEST_DIR/installer.sh.sha256"
  cat > "$TEST_DIR/latest_release.json" <<EOF
{"tag_name": "v0.3.0", "assets": [
  {"name": "klipper-foci-installer.sh", "browser_download_url": "https://example.test/installer.sh"},
  {"name": "klipper-foci-installer.sh.sha256", "browser_download_url": "https://example.test/installer.sh.sha256"}
]}
EOF
  cp "$TEST_DIR/latest_release.json" "$TEST_DIR/tagged_release.json"

  source "$BATS_TEST_DIRNAME/install.sh"
}
teardown() { rm -rf "$TEST_DIR"; }

@test "foci_bootstrap resolves latest and execs the verified installer with forwarded args" {
  run foci_bootstrap --diagnostics
  [ "$status" -eq 0 ]
  grep -q 'exec:bash .*installer.sh --diagnostics' "$TEST_DIR/exec.log"
}

@test "foci_bootstrap consumes --version and does not forward it" {
  run foci_bootstrap --version v0.2.0 --force
  [ "$status" -eq 0 ]
  grep -q -- '--force' "$TEST_DIR/exec.log"
  ! grep -q -- '--version' "$TEST_DIR/exec.log"
}

@test "foci_bootstrap aborts on a checksum mismatch" {
  printf 'tampered\n' >> "$TEST_DIR/installer.sh"
  run foci_bootstrap
  [ "$status" -eq 1 ]
  [[ "$output" == *"checksum"* ]]
  [ ! -f "$TEST_DIR/exec.log" ]
}

@test "foci_bootstrap fails with a clear error when --version has no value" {
  run timeout 5 bash -c "source $BATS_TEST_DIRNAME/install.sh; foci_bootstrap --version"
  [ "$status" -eq 1 ]
  [[ "$output" == *"--version requires a value"* ]]
}

@test "foci_bootstrap fails clearly when the GitHub API is unreachable" {
  curl() {
    case "$*" in
      *api.github.com*) return 7 ;;  # curl's connection-failed exit code
      *) echo "unexpected curl: $*" >&2; return 1 ;;
    esac
  }
  export -f curl
  run foci_bootstrap
  [ "$status" -eq 1 ]
  [[ "$output" == *"GitHub API"* ]]
  [ ! -f "$TEST_DIR/exec.log" ]
}

@test "piping install.sh into bash runs the bootstrap and forwards args" {
  run env -u BATS_TEST_FILENAME bash -c "cat $BATS_TEST_DIRNAME/install.sh | bash -s -- --diagnostics"
  [ "$status" -eq 0 ]
  grep -q 'exec:bash .*installer.sh --diagnostics' "$TEST_DIR/exec.log"
}
