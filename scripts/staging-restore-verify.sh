#!/bin/sh
set -eu

umask 077

backup_id="${1:-}"
case "$backup_id" in
    *[!A-Za-z0-9._-]*|"")
        echo "Pass a valid backup id as the only argument." >&2
        exit 2
        ;;
esac

backup_dir="/backups/$backup_id"
if [ ! -d "$backup_dir" ]; then
    echo "Backup does not exist: $backup_id" >&2
    exit 3
fi

(
    cd "$backup_dir"
    sha256sum --check SHA256SUMS
)

restore_db="hydra_restore_$(date -u +%Y%m%d%H%M%S)_$$"
private_tmp="/tmp/private-restore-$$"
private_records="/tmp/private-records-$$"

cleanup() {
    dropdb --if-exists "$restore_db" >/dev/null 2>&1 || true
    rm -rf -- "$private_tmp"
    rm -f -- "$private_records"
}
trap cleanup EXIT HUP INT TERM

createdb "$restore_db"
pg_restore \
    --dbname="$restore_db" \
    --exit-on-error \
    --no-owner \
    --no-acl \
    "$backup_dir/database.dump"

migration_count="$(psql --no-psqlrc --dbname="$restore_db" --tuples-only --no-align -c 'SELECT COUNT(*) FROM django_migrations')"
if [ "$migration_count" -le 0 ]; then
    echo "Restored database has no migration history." >&2
    exit 4
fi

mkdir -m 0700 "$private_tmp"
tar -C "$private_tmp" -xzf "$backup_dir/private-media.tar.gz"

tab="$(printf '\t')"
psql --no-psqlrc --dbname="$restore_db" --tuples-only --no-align --field-separator="$tab" \
    -c 'SELECT file, sha256 FROM hydra_documents_privatedocument ORDER BY id' > "$private_records"
verified=0
while IFS="$tab" read -r storage_key expected_hash; do
    [ -n "$storage_key" ] || continue
    case "$storage_key" in
        /*|*..*|*[!A-Za-z0-9._/-]*)
            echo "Unsafe private storage key in restored database." >&2
            exit 5
            ;;
    esac
    restored_file="$private_tmp/$storage_key"
    if [ ! -f "$restored_file" ]; then
        echo "Missing private object after restore: $storage_key" >&2
        exit 6
    fi
    actual_hash="$(sha256sum "$restored_file" | awk '{print $1}')"
    if [ "$actual_hash" != "$expected_hash" ]; then
        echo "Private object checksum mismatch: $storage_key" >&2
        exit 7
    fi
    verified=$((verified + 1))
done < "$private_records"

dropdb "$restore_db"
rm -rf -- "$private_tmp"
rm -f -- "$private_records"
trap - EXIT HUP INT TERM

echo "Restore verification passed for $backup_id ($migration_count migrations, $verified private objects)."
