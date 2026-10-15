from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from reports.models import ItemReport, ReportPrivateDetail, ReportStatus, ReportVisibility
from claims.models import Claim, ClaimStatus, ClaimEvidence
from audit.models import AuditEvent

class Command(BaseCommand):
    help = "Enforces the UTN Data Retention & Privacy Schedule per PILOT_RUNBOOK.md Section 3."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Simulate retention actions without modifying the database.'
        )
        parser.add_argument(
            '--days-returned',
            type=int,
            default=90,
            help='Retention days for returned items before anonymization (default: 90).'
        )
        parser.add_argument(
            '--days-withdrawn',
            type=int,
            default=30,
            help='Retention days for withdrawn reports before permanent deletion (default: 30).'
        )
        parser.add_argument(
            '--days-claim-evidence',
            type=int,
            default=180,
            help='Retention days for completed/rejected claim evidence before purge (default: 180).'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        days_returned = options['days_returned']
        days_withdrawn = options['days_withdrawn']
        days_claims = options['days_claim_evidence']

        now = timezone.now()
        cutoff_returned = now - timedelta(days=days_returned)
        cutoff_withdrawn = now - timedelta(days=days_withdrawn)
        cutoff_claims = now - timedelta(days=days_claims)

        mode_label = "[DRY RUN]" if dry_run else "[ACTIVE RUN]"
        self.stdout.write(self.style.NOTICE(f"{mode_label} Starting UTN Data Retention Enforcement at {now.isoformat()}..."))

        # 1. Withdrawn Reports Deletion (30 days)
        withdrawn_qs = ItemReport.objects.filter(
            status=ReportStatus.WITHDRAWN,
            updated_at__lt=cutoff_withdrawn
        )
        withdrawn_count = withdrawn_qs.count()
        self.stdout.write(f"Found {withdrawn_count} withdrawn reports past {days_withdrawn} days cutoff.")

        if not dry_run and withdrawn_count > 0:
            with transaction.atomic():
                for report in withdrawn_qs:
                    report_id = str(report.id)
                    title = report.title
                    report.delete()
                    AuditEvent.objects.create(
                        actor=None,
                        action="RETENTION_PURGE_WITHDRAWN_REPORT",
                        entity_type="ItemReport",
                        entity_id=report_id,
                        metadata_redacted={"reason": f"Withdrawn report retention expired ({days_withdrawn}d)", "title": title}
                    )
            self.stdout.write(self.style.SUCCESS(f"Purged {withdrawn_count} withdrawn reports."))

        # 2. Returned Items Anonymization & Vault Scrubbing (90 days)
        returned_qs = ItemReport.objects.filter(
            status=ReportStatus.RETURNED,
            updated_at__lt=cutoff_returned
        ).exclude(visibility=ReportVisibility.REMOVED)
        returned_count = returned_qs.count()
        self.stdout.write(f"Found {returned_count} returned reports past {days_returned} days cutoff awaiting vault scrubbing.")

        if not dry_run and returned_count > 0:
            scrubbed_count = 0
            with transaction.atomic():
                for report in returned_qs:
                    # Delete private verification vault
                    ReportPrivateDetail.objects.filter(report=report).delete()
                    report.visibility = ReportVisibility.REMOVED
                    report.public_description = "[ANONYMIZED_HISTORICAL_RECORD]"
                    report.save(update_fields=['visibility', 'public_description', 'updated_at'])
                    scrubbed_count += 1

                    AuditEvent.objects.create(
                        actor=None,
                        action="RETENTION_ANONYMIZE_RETURNED_REPORT",
                        entity_type="ItemReport",
                        entity_id=str(report.id),
                        metadata_redacted={"reason": f"Returned item vault purged past {days_returned}d"}
                    )
            self.stdout.write(self.style.SUCCESS(f"Anonymized and scrubbed private vault for {scrubbed_count} returned reports."))

        # 3. Claim Evidence & Statements Purge (180 days)
        claims_qs = Claim.objects.filter(
            status__in=[ClaimStatus.COMPLETED, ClaimStatus.REJECTED],
            updated_at__lt=cutoff_claims
        )
        claims_count = claims_qs.count()
        self.stdout.write(f"Found {claims_count} completed/rejected claims past {days_claims} days cutoff.")

        if not dry_run and claims_count > 0:
            evidence_purged_count = 0
            with transaction.atomic():
                for claim in claims_qs:
                    del_count, _ = ClaimEvidence.objects.filter(claim=claim).delete()
                    evidence_purged_count += del_count
                    claim.claimant_statement = "[REDACTED_BY_RETENTION_POLICY]"
                    claim.save(update_fields=['claimant_statement', 'updated_at'])

                    AuditEvent.objects.create(
                        actor=None,
                        action="RETENTION_PURGE_CLAIM_EVIDENCE",
                        entity_type="Claim",
                        entity_id=str(claim.id),
                        metadata_redacted={"reason": f"Claim evidence purged past {days_claims}d", "evidence_count": del_count}
                    )
            self.stdout.write(self.style.SUCCESS(f"Purged {evidence_purged_count} evidence records across {claims_count} claims."))

        self.stdout.write(self.style.SUCCESS(f"{mode_label} Data retention enforcement completed successfully."))
