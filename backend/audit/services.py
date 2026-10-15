import csv
import io
from datetime import timedelta
from django.utils import timezone
from reports.models import ItemReport, ReportType, ReportStatus, ReportVisibility, ReportAbuseFlag
from claims.models import Claim, ClaimStatus
from custody.models import CustodyEvent, CustodyEventType
from audit.models import AuditEvent
from accounts.models import User
from locations.models import Location

class PilotMetricsService:
    """
    Computes campus pilot success metrics and operational KPIs per PRD Section 9.
    Provides structured metrics dictionaries and CSV exports for pilot stakeholders.
    """

    @classmethod
    def compute_metrics(cls, days: int | None = None, location_id: str | None = None) -> dict:
        now = timezone.now()
        reports_qs = ItemReport.objects.all()
        claims_qs = Claim.objects.all()
        custody_qs = CustodyEvent.objects.all()
        audit_qs = AuditEvent.objects.all()

        if days is not None:
            since = now - timedelta(days=days)
            reports_qs = reports_qs.filter(created_at__gte=since)
            claims_qs = claims_qs.filter(created_at__gte=since)
            custody_qs = custody_qs.filter(created_at__gte=since)
            audit_qs = audit_qs.filter(created_at__gte=since)

        if location_id:
            reports_qs = reports_qs.filter(
                found_location_id=location_id
            ) | reports_qs.filter(
                last_seen_location_id=location_id
            )

        # 1. Recovery Success Metrics (PRD Section 9)
        total_found = reports_qs.filter(report_type=ReportType.FOUND).count()
        returned_found = reports_qs.filter(report_type=ReportType.FOUND, status=ReportStatus.RETURNED).count()
        open_found = reports_qs.filter(report_type=ReportType.FOUND, status=ReportStatus.OPEN).count()
        recovery_rate_pct = round((returned_found / total_found * 100.0), 1) if total_found > 0 else 0.0

        # 2. Lost Belongings & Surfacing
        total_lost = reports_qs.filter(report_type=ReportType.LOST).count()
        open_lost = reports_qs.filter(report_type=ReportType.LOST, status=ReportStatus.OPEN).count()
        withdrawn_lost = reports_qs.filter(report_type=ReportType.LOST, status=ReportStatus.WITHDRAWN).count()

        # 3. Ownership Claims & Verification Precision
        total_claims = claims_qs.count()
        approved_claims = claims_qs.filter(status=ClaimStatus.APPROVED).count()
        completed_claims = claims_qs.filter(status=ClaimStatus.COMPLETED).count()
        rejected_claims = claims_qs.filter(status=ClaimStatus.REJECTED).count()
        needs_info_claims = claims_qs.filter(status=ClaimStatus.NEEDS_INFO).count()
        pending_claims = claims_qs.filter(status=ClaimStatus.PENDING).count()

        decided_claims = approved_claims + completed_claims + rejected_claims
        successful_claims = approved_claims + completed_claims
        claim_verification_precision_pct = round((successful_claims / decided_claims * 100.0), 1) if decided_claims > 0 else 0.0
        false_positive_claim_rate_pct = round((rejected_claims / decided_claims * 100.0), 1) if decided_claims > 0 else 0.0

        # 4. Custody Trail Completeness & Integrity
        total_custody_events = custody_qs.count()
        handover_events = custody_qs.filter(event_type=CustodyEventType.HANDOVER_COMPLETED).count()
        returned_reports = reports_qs.filter(status=ReportStatus.RETURNED)
        returned_count = returned_reports.count()

        # Check returned reports that have at least one HANDOVER_COMPLETED custody event
        returned_with_handover = returned_reports.filter(
            custody_events__event_type=CustodyEventType.HANDOVER_COMPLETED
        ).distinct().count()
        custody_integrity_pct = round((returned_with_handover / returned_count * 100.0), 1) if returned_count > 0 else 100.0

        # 5. Multi-Location Transfer Operations
        transfers_requested = custody_qs.filter(event_type=CustodyEventType.TRANSFER_REQUESTED).count()
        transfers_accepted = custody_qs.filter(event_type=CustodyEventType.TRANSFER_ACCEPTED).count()
        transfer_completion_pct = round((transfers_accepted / transfers_requested * 100.0), 1) if transfers_requested > 0 else 100.0

        # 6. Handover Turnaround Latency (Hours from intake to handover)
        turnaround_hours = []
        for rep in returned_reports.filter(custody_events__event_type=CustodyEventType.HANDOVER_COMPLETED).distinct():
            handover_ev = rep.custody_events.filter(event_type=CustodyEventType.HANDOVER_COMPLETED).order_by('created_at').first()
            if handover_ev and rep.created_at:
                delta = (handover_ev.created_at - rep.created_at).total_seconds() / 3600.0
                if delta >= 0:
                    turnaround_hours.append(round(delta, 1))

        if turnaround_hours:
            turnaround_hours.sort()
            mean_turnaround_hours = round(sum(turnaround_hours) / len(turnaround_hours), 1)
            median_turnaround_hours = round(turnaround_hours[len(turnaround_hours) // 2], 1)
        else:
            mean_turnaround_hours = None
            median_turnaround_hours = None

        # 7. Safety, Abuse & Moderation Metrics
        total_abuse_flags = ReportAbuseFlag.objects.count()
        hidden_reports = reports_qs.filter(visibility=ReportVisibility.HIDDEN).count()
        removed_reports = reports_qs.filter(visibility=ReportVisibility.REMOVED).count()
        suspended_users = User.objects.filter(is_active=False).count()

        # 8. Audit & Idempotency Health
        total_audit_events = audit_qs.count()
        idempotent_handovers = audit_qs.filter(
            action="HANDOVER_COMPLETED",
            metadata_redacted__idempotency_key__isnull=False
        ).count()

        return {
            "period": {
                "generated_at": now.isoformat(),
                "filter_days": days,
                "location_filter": location_id
            },
            "recovery_metrics": {
                "total_found_items": total_found,
                "returned_to_owner": returned_found,
                "currently_in_custody": open_found,
                "recovery_rate_pct": recovery_rate_pct,
                "target_gate_met": recovery_rate_pct >= 50.0 if total_found > 0 else True
            },
            "lost_reports": {
                "total_lost_filed": total_lost,
                "open_lost_active": open_lost,
                "withdrawn_by_user": withdrawn_lost
            },
            "claims_and_verification": {
                "total_claims": total_claims,
                "approved": approved_claims,
                "completed": completed_claims,
                "needs_info": needs_info_claims,
                "rejected": rejected_claims,
                "pending_review": pending_claims,
                "verification_precision_pct": claim_verification_precision_pct,
                "false_positive_claim_rate_pct": false_positive_claim_rate_pct,
                "target_gate_met": false_positive_claim_rate_pct <= 25.0
            },
            "custody_and_transfers": {
                "total_custody_events": total_custody_events,
                "handover_events_recorded": handover_events,
                "custody_trail_integrity_pct": custody_integrity_pct,
                "transfers_requested": transfers_requested,
                "transfers_accepted": transfers_accepted,
                "transfer_completion_pct": transfer_completion_pct,
                "mean_handover_turnaround_hours": mean_turnaround_hours,
                "median_handover_turnaround_hours": median_turnaround_hours
            },
            "safety_and_moderation": {
                "community_abuse_flags": total_abuse_flags,
                "hidden_listings": hidden_reports,
                "removed_listings": removed_reports,
                "suspended_users": suspended_users
            },
            "audit_and_idempotency": {
                "total_audit_events": total_audit_events,
                "idempotent_handovers_verified": idempotent_handovers
            }
        }

    @classmethod
    def generate_csv(cls, metrics: dict) -> str:
        """
        Formats computed metrics into standard CSV string for spreadsheet export.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow(["UTN Campus Pilot Success Metrics & KPI Report"])
        writer.writerow(["Generated At", metrics['period']['generated_at']])
        writer.writerow(["Filter Days", metrics['period']['filter_days'] or "All Time"])
        writer.writerow([])

        writer.writerow(["Category", "Metric", "Value", "Unit / Status"])

        # Recovery
        rec = metrics['recovery_metrics']
        writer.writerow(["Recovery", "Total Found Belongings Registered", rec['total_found_items'], "items"])
        writer.writerow(["Recovery", "Successfully Returned to Owner", rec['returned_to_owner'], "items"])
        writer.writerow(["Recovery", "Belongings In Current Custody", rec['currently_in_custody'], "items"])
        writer.writerow(["Recovery", "Recovery Success Rate", rec['recovery_rate_pct'], "%"])
        writer.writerow(["Recovery", "Pilot Gate Status", "PASS" if rec['target_gate_met'] else "ACTION_NEEDED", "status"])

        # Lost Reports
        lost = metrics['lost_reports']
        writer.writerow(["Lost Reports", "Total Lost Reports Filed", lost['total_lost_filed'], "reports"])
        writer.writerow(["Lost Reports", "Active Open Searches", lost['open_lost_active'], "reports"])
        writer.writerow(["Lost Reports", "Withdrawn by Student", lost['withdrawn_by_user'], "reports"])

        # Claims
        cl = metrics['claims_and_verification']
        writer.writerow(["Claims", "Total Ownership Claims", cl['total_claims'], "claims"])
        writer.writerow(["Claims", "Approved Claims", cl['approved'], "claims"])
        writer.writerow(["Claims", "Completed Handovers", cl['completed'], "claims"])
        writer.writerow(["Claims", "Needs Info / Evidence Requested", cl['needs_info'], "claims"])
        writer.writerow(["Claims", "Rejected Claims", cl['rejected'], "claims"])
        writer.writerow(["Claims", "Pending Review", cl['pending_review'], "claims"])
        writer.writerow(["Claims", "Verification Precision Rate", cl['verification_precision_pct'], "%"])
        writer.writerow(["Claims", "False Positive Claim Rate", cl['false_positive_claim_rate_pct'], "%"])

        # Custody
        cust = metrics['custody_and_transfers']
        writer.writerow(["Custody", "Custody Events Recorded", cust['total_custody_events'], "events"])
        writer.writerow(["Custody", "Custody Trail Completeness", cust['custody_trail_integrity_pct'], "%"])
        writer.writerow(["Custody", "Transfers Dispatched", cust['transfers_requested'], "transfers"])
        writer.writerow(["Custody", "Transfers Acknowledged/Accepted", cust['transfers_accepted'], "transfers"])
        writer.writerow(["Custody", "Median Handover Turnaround", cust['median_handover_turnaround_hours'] or "N/A", "hours"])

        # Safety
        safe = metrics['safety_and_moderation']
        writer.writerow(["Safety", "Community Abuse Flags", safe['community_abuse_flags'], "flags"])
        writer.writerow(["Safety", "Moderated Hidden Listings", safe['hidden_listings'], "listings"])
        writer.writerow(["Safety", "Removed Inappropriate Listings", safe['removed_listings'], "listings"])
        writer.writerow(["Safety", "Suspended Accounts", safe['suspended_users'], "users"])

        # Idempotency
        audit = metrics['audit_and_idempotency']
        writer.writerow(["Audit", "Total Immutable Audit Records", audit['total_audit_events'], "records"])
        writer.writerow(["Audit", "Idempotency Handover Tokens", audit['idempotent_handovers_verified'], "verified"])

        return output.getvalue()
