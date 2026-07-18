import json

from django.core.management.base import BaseCommand, CommandError

from hydra_ops.readiness import collect_readiness, readiness_payload


class Command(BaseCommand):
    help = "Fail-closed staging/production readiness verification."

    def add_arguments(self, parser):
        parser.add_argument("--json", action="store_true", dest="as_json")
        parser.add_argument("--skip-filesystem", action="store_true")
        parser.add_argument("--skip-migrations", action="store_true")
        parser.add_argument("--skip-domain-integrity", action="store_true")

    def handle(self, *args, **options):
        results = collect_readiness(
            include_filesystem=not options["skip_filesystem"],
            include_migrations=not options["skip_migrations"],
            include_domain_integrity=not options["skip_domain_integrity"],
        )
        payload = readiness_payload(results)
        if options["as_json"]:
            self.stdout.write(json.dumps(payload, sort_keys=True))
        else:
            for result in results:
                marker = "PASS" if result.ok else "FAIL"
                self.stdout.write(f"[{marker}] {result.name}: {result.detail}")

        failures = [result for result in results if not result.ok]
        if failures:
            raise CommandError(f"Hydra is not ready: {len(failures)} check(s) failed.")
        if not options["as_json"]:
            self.stdout.write(self.style.SUCCESS("Hydra is ready."))
