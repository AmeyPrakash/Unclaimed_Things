import time
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection
from django.core.cache import cache

class Command(BaseCommand):
    help = "Runs pre-flight pilot readiness diagnostic covering database, pgvector, cache, NIM, and operational queues."

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output diagnostic results in JSON format for automated monitoring systems.'
        )

    def handle(self, *args, **options):
        output_json = options['json']
        diagnostic_results = {}
        all_passed = True

        # 1. Database & pgvector check
        t0 = time.perf_counter()
        db_status = "UNKNOWN"
        vector_version = None
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector';")
                row = cursor.fetchone()
                if row:
                    vector_version = row[0]
                    db_status = "OK"
                else:
                    db_status = "WARNING_NO_VECTOR"
        except Exception as e:
            db_status = f"ERROR: {e}"
            all_passed = False
        db_latency = (time.perf_counter() - t0) * 1000.0

        diagnostic_results["database"] = {
            "status": "PASS" if db_status == "OK" else "FAIL",
            "connection": "CONNECTED" if "ERROR" not in db_status else "FAILED",
            "pgvector_extension": vector_version or "NOT_INSTALLED",
            "latency_ms": round(db_latency, 2)
        }

        # 2. Cache & Rate Limiting Engine check
        cache_status = "FAIL"
        try:
            cache_key = "utn_diagnostic_probe"
            cache.set(cache_key, "probe_ok", timeout=10)
            if cache.get(cache_key) == "probe_ok":
                cache_status = "PASS"
                cache.delete(cache_key)
        except Exception as e:
            cache_status = f"FAIL: {e}"
            all_passed = False

        diagnostic_results["cache_and_throttling"] = {
            "status": cache_status,
            "engine": settings.CACHES['default']['BACKEND'].split('.')[-1]
        }

        # 3. NVIDIA NIM AI Connectivity check
        nim_status = "DISABLED"
        nim_latency = 0.0
        if settings.NIM_ENABLED:
            if not settings.NIM_API_KEY:
                nim_status = "WARN_MISSING_API_KEY"
            else:
                from matching.services import NimEmbeddingAdapter
                t0 = time.perf_counter()
                try:
                    vec = NimEmbeddingAdapter.get_embedding("Campus pilot health check diagnostic probe")
                    nim_latency = (time.perf_counter() - t0) * 1000.0
                    if vec and len(vec) == settings.NIM_EMBEDDING_DIMENSION:
                        nim_status = "PASS"
                    else:
                        nim_status = "FAIL_DIMENSION_MISMATCH"
                        all_passed = False
                except Exception as e:
                    nim_status = f"FAIL: {e}"
                    all_passed = False

        diagnostic_results["nvidia_nim"] = {
            "enabled": settings.NIM_ENABLED,
            "status": nim_status,
            "model": settings.NIM_EMBEDDING_MODEL,
            "expected_dimension": settings.NIM_EMBEDDING_DIMENSION,
            "latency_ms": round(nim_latency, 2) if settings.NIM_ENABLED else None
        }

        # 4. Operational Queues & Backlog
        try:
            from claims.models import Claim, ClaimStatus
            from custody.models import CustodyEvent, CustodyEventType
            from reports.models import ItemReport, ReportStatus, ReportAbuseFlag

            pending_claims = Claim.objects.filter(status=ClaimStatus.PENDING).count()
            open_reports = ItemReport.objects.filter(status=ReportStatus.OPEN).count()
            unacked_transfers = CustodyEvent.objects.filter(
                event_type=CustodyEventType.TRANSFER_REQUESTED
            ).count()
            abuse_flags_count = ReportAbuseFlag.objects.count()

            diagnostic_results["operational_queues"] = {
                "open_reports_active": open_reports,
                "pending_claims_awaiting_review": pending_claims,
                "unacknowledged_custody_transfers": unacked_transfers,
                "community_abuse_flags": abuse_flags_count
            }
        except Exception as e:
            diagnostic_results["operational_queues"] = {"error": str(e)}

        # 5. Media Storage Check
        import os
        media_writable = False
        try:
            os.makedirs(settings.MEDIA_ROOT, exist_ok=True)
            test_file = settings.MEDIA_ROOT / ".probe_write"
            with open(test_file, 'w') as f:
                f.write("probe")
            if test_file.exists():
                media_writable = True
                test_file.unlink()
        except Exception:
            media_writable = False

        diagnostic_results["storage"] = {
            "media_root": str(settings.MEDIA_ROOT),
            "writable": media_writable,
            "status": "PASS" if media_writable else "FAIL"
        }

        # Output formatting
        if output_json:
            self.stdout.write(json.dumps(diagnostic_results, indent=2))
        else:
            self.stdout.write(self.style.MIGRATE_HEADING("=== UTN Pilot Pre-Flight Health Diagnostic ==="))
            self.stdout.write(f"Timestamp: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}\n")

            # DB
            db_res = diagnostic_results["database"]
            db_style = self.style.SUCCESS if db_res["status"] == "PASS" else self.style.ERROR
            self.stdout.write(f"• Database Connection:        {db_style(db_res['connection'])} ({db_res['latency_ms']} ms)")
            self.stdout.write(f"• PostgreSQL pgvector:        {self.style.SUCCESS('INSTALLED (v' + db_res['pgvector_extension'] + ')') if db_res['pgvector_extension'] != 'NOT_INSTALLED' else self.style.ERROR('MISSING')}")

            # Cache
            cache_res = diagnostic_results["cache_and_throttling"]
            c_style = self.style.SUCCESS if cache_res["status"] == "PASS" else self.style.ERROR
            self.stdout.write(f"• Cache & Rate Limiting:      {c_style(cache_res['status'])} ({cache_res['engine']})")

            # NIM
            nim_res = diagnostic_results["nvidia_nim"]
            if nim_res["enabled"]:
                n_style = self.style.SUCCESS if nim_res["status"] == "PASS" else self.style.WARNING
                self.stdout.write(f"• NVIDIA NIM Hybrid AI:       {n_style(nim_res['status'])} (Model: {nim_res['model']}, {nim_res['latency_ms']} ms)")
            else:
                self.stdout.write(f"• NVIDIA NIM Hybrid AI:       {self.style.NOTICE('OFFLINE / KEYWORD FALLBACK MODE')}")

            # Storage
            stor_res = diagnostic_results["storage"]
            s_style = self.style.SUCCESS if stor_res["writable"] else self.style.ERROR
            self.stdout.write(f"• Media Upload Storage:       {s_style('WRITABLE' if stor_res['writable'] else 'NOT WRITABLE')} ({stor_res['media_root']})")

            # Queues
            q = diagnostic_results.get("operational_queues", {})
            self.stdout.write("\n" + self.style.MIGRATE_HEADING("--- Operational Queue Summary ---"))
            self.stdout.write(f"• Open Public Reports:        {q.get('open_reports_active', 0)}")
            self.stdout.write(f"• Pending Student Claims:     {q.get('pending_claims_awaiting_review', 0)}")
            self.stdout.write(f"• Custody Transfers En Route: {q.get('unacknowledged_custody_transfers', 0)}")
            self.stdout.write(f"• Community Abuse Flags:      {q.get('community_abuse_flags', 0)}")
            self.stdout.write("=" * 46 + "\n")

            if all_passed:
                self.stdout.write(self.style.SUCCESS("All systems operational. UTN is ready for campus pilot operations!"))
            else:
                self.stdout.write(self.style.WARNING("One or more non-critical checks reported warnings. Review output above."))
