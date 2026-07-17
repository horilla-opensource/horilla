#!/bin/sh
set -eu

archive="${1:-}"
label="${2:-backup archive}"

if [ -z "$archive" ] || [ ! -f "$archive" ]; then
    echo "Missing $label." >&2
    exit 2
fi

members="$(mktemp "${TMPDIR:-/tmp}/hydra-archive-members.XXXXXX")"
verbose="$(mktemp "${TMPDIR:-/tmp}/hydra-archive-types.XXXXXX")"
cleanup() {
    rm -f -- "$members" "$verbose"
}
trap cleanup EXIT HUP INT TERM

if ! tar --list --gzip --file "$archive" --quoting-style=escape > "$members"; then
    echo "$label is not a readable gzip-compressed tar archive." >&2
    exit 3
fi

if ! awk '
    {
        name = $0
        while (sub(/^\.\//, "", name)) { }
        sub(/\/$/, "", name)
        if (name == "" || name == ".") {
            next
        }
        if (name ~ /^\// || name ~ /(^|\/)\.\.(\/|$)/ || name !~ /^[A-Za-z0-9._\/-]+$/) {
            print "Archive contains an unsafe member path." > "/dev/stderr"
            exit 1
        }
        if (seen[name]++) {
            print "Archive contains a duplicate normalized member path." > "/dev/stderr"
            exit 1
        }
    }
' "$members"; then
    echo "$label failed member-path validation." >&2
    exit 4
fi

if ! tar --list --verbose --gzip --file "$archive" --quoting-style=escape > "$verbose"; then
    echo "$label member types could not be read." >&2
    exit 5
fi

if ! awk '
    substr($1, 1, 1) != "-" && substr($1, 1, 1) != "d" {
        print "Archive contains a link, device, FIFO, or another unsupported member type." > "/dev/stderr"
        exit 1
    }
' "$verbose"; then
    echo "$label failed member-type validation." >&2
    exit 6
fi

trap - EXIT HUP INT TERM
cleanup
