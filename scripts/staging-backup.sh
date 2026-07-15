#!/bin/sh
set -eu

umask 077

backup_id="${1:-hydra-$(date -u +%Y%m%dT%H%M%SZ)}"
case "$backup_id" in
    *[!A-Za-z0-9._-]*|"")
        echo "Backup id contains unsupported characters." >&2
        exit 2
        ;;
esac

partial="/backups/${backup_id}.partial"
final="/backups/${backup_id}"

if [ -e "$partial" ] || [ -e "$final" ]; then
    echo "Backup destination already exists: $backup_id" >&2
    exit 3
fi

cleanup() {
    rm -rf -- "$partial"
}
trap cleanup EXIT HUP INT TERM

mkdir -m 0700 "$partial"

pg_dump \
    --format=custom \
    --compress=6 \
    --no-owner \
    --no-acl \
    --file="$partial/database.dump"

tar -C /data/media -czf "$partial/media.tar.gz" .
tar -C /data/private -czf "$partial/private-media.tar.gz" .

migration_count="$(psql --no-psqlrc --tuples-only --no-align -c 'SELECT COUNT(*) FROM django_migrations')"
private_document_count="$(psql --no-psqlrc --tuples-only --no-align -c 'SELECT COUNT(*) FROM hydra_documents_privatedocument')"

cat > "$partial/manifest.json" <<EOF
{"format_version":1,"backup_id":"$backup_id","created_at_utc":"$(date -u +%Y-%m-%dT%H:%M:%SZ)","database":"$PGDATABASE","migration_count":$migration_count,"private_document_count":$private_document_count}
EOF

(
    cd "$partial"
    sha256sum database.dump media.tar.gz private-media.tar.gz manifest.json > SHA256SUMS
)

mv "$partial" "$final"
trap - EXIT HUP INT TERM

echo "$backup_id"
