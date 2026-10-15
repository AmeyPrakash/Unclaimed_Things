import json
from django.core.management.base import BaseCommand
from audit.services import PilotMetricsService

class Command(BaseCommand):
    help = "Exports campus pilot recovery metrics and KPI scorecard per PRD Section 9."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Filter metrics to the past N days (e.g. --days 30).'
        )
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output metrics in JSON format.'
        )
        parser.add_argument(
            '--csv',
            action='store_true',
            help='Output metrics in CSV format.'
        )
        parser.add_argument(
            '--output',
            type=str,
            default=None,
            help='Optional destination file path to save the exported report.'
        )

    def handle(self, *args, **options):
        days = options['days']
        as_json = options['json']
        as_csv = options['csv']
        output_file = options['output']

        metrics = PilotMetricsService.compute_metrics(days=days)

        if as_json:
            formatted_output = json.dumps(metrics, indent=2)
        elif as_csv:
            formatted_output = PilotMetricsService.generate_csv(metrics)
        else:
            # Colorized ASCII Summary Card
            lines = [
                "=" * 80,
                "   THE UNCLAIMED THINGS NETWORK (UTN) - CAMPUS PILOT METRICS & KPI SCORECARD",
                f"   Scope: {'Past ' + str(days) + ' days' if days else 'All Time Pilot History'} | Generated: {metrics['period']['generated_at']}",
                "=" * 80,
                "",
                "[1] RECOVERY & RESTORATION SUCCESS (PRD Section 9)",
                f"  * Total Found Belongings Registered: {metrics['recovery_metrics']['total_found_items']}",
                f"  * Belongings Restored to Owner:      {metrics['recovery_metrics']['returned_to_owner']}",
                f"  * Items In Current Secure Custody:   {metrics['recovery_metrics']['currently_in_custody']}",
                f"  * Recovery Success Rate:             {metrics['recovery_metrics']['recovery_rate_pct']}% " +
                ("[PASS]" if metrics['recovery_metrics']['target_gate_met'] else "[ACTION NEEDED]"),
                "",
                "[2] SEARCH & LOST REPORTS",
                f"  * Total Lost Reports Filed:          {metrics['lost_reports']['total_lost_filed']}",
                f"  * Active Open Searches:              {metrics['lost_reports']['open_lost_active']}",
                f"  * Reports Withdrawn by Student:      {metrics['lost_reports']['withdrawn_by_user']}",
                "",
                "[3] CLAIMS & VERIFICATION PRECISION",
                f"  * Total Ownership Claims Filed:      {metrics['claims_and_verification']['total_claims']}",
                f"  * Approved & Verified Claims:        {metrics['claims_and_verification']['approved']}",
                f"  * Completed Physical Handovers:      {metrics['claims_and_verification']['completed']}",
                f"  * Needs More Evidence (Info Req):    {metrics['claims_and_verification']['needs_info']}",
                f"  * Rejected / Unsubstantiated Claims: {metrics['claims_and_verification']['rejected']}",
                f"  * Pending Staff Review:              {metrics['claims_and_verification']['pending_review']}",
                f"  * Claim Verification Precision:      {metrics['claims_and_verification']['verification_precision_pct']}%",
                f"  * False Positive Claim Rate:         {metrics['claims_and_verification']['false_positive_claim_rate_pct']}% " +
                ("[PASS]" if metrics['claims_and_verification']['target_gate_met'] else "[HIGH FRAUD RISK]"),
                "",
                "[4] CUSTODY TRAIL & MULTI-LOCATION TRANSFERS",
                f"  * Total Custody Audit Events:        {metrics['custody_and_transfers']['total_custody_events']}",
                f"  * Handover Events Recorded:          {metrics['custody_and_transfers']['handover_events_recorded']}",
                f"  * Custody Trail Completeness:        {metrics['custody_and_transfers']['custody_trail_integrity_pct']}%",
                f"  * Inter-Facility Transfers Sent:     {metrics['custody_and_transfers']['transfers_requested']}",
                f"  * Transfers Acknowledged & Accepted: {metrics['custody_and_transfers']['transfers_accepted']}",
                f"  * Median Handover Turnaround:        {metrics['custody_and_transfers']['median_handover_turnaround_hours'] or 'N/A'} hours",
                "",
                "[5] ABUSE MODERATION & SAFETY MONITORING",
                f"  * Community Abuse Flags:             {metrics['safety_and_moderation']['community_abuse_flags']}",
                f"  * Moderated Listings (Hidden):       {metrics['safety_and_moderation']['hidden_listings']}",
                f"  * Removed Inappropriate Listings:    {metrics['safety_and_moderation']['removed_listings']}",
                f"  * Suspended User Accounts:           {metrics['safety_and_moderation']['suspended_users']}",
                "",
                "[6] AUDIT TELEMETRY & IDEMPOTENCY",
                f"  * Total Immutable Audit Events:      {metrics['audit_and_idempotency']['total_audit_events']}",
                f"  * Idempotency Replays Verified:      {metrics['audit_and_idempotency']['idempotent_handovers_verified']}",
                "=" * 80
            ]
            formatted_output = "\n".join(lines)

        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(formatted_output)
            self.stdout.write(self.style.SUCCESS(f"Pilot metrics exported successfully to: {output_file}"))
        else:
            self.stdout.write(formatted_output)
