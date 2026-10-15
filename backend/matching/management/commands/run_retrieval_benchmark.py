import time
from django.core.management.base import BaseCommand
from django.conf import settings
from locations.models import Location, LocationType
from reports.models import ItemReport, ItemCategory, ReportType, ReportStatus, ReportVisibility, ItemEmbedding, EmbeddingStatus
from matching.services import MatchingService

BENCHMARK_PAIRS = [
    # Positive Test Pairs (Semantic Synonymy, Brand vs Generic, Visual Abstraction, Institutional)
    {
        "id": "P01",
        "type": "positive",
        "category": ItemCategory.ELECTRONICS,
        "query_title": "Space grey MacBook Pro",
        "query_desc": "Space grey MacBook Pro with cracked charger wire lost near study pods",
        "target_title": "Dark Apple laptop",
        "target_desc": "Dark Apple laptop with taped charging cord found on library desk",
        "description": "Semantic synonymy (MacBook Pro vs Apple laptop)"
    },
    {
        "id": "P02",
        "type": "positive",
        "category": ItemCategory.BOTTLE,
        "query_title": "Blue insulated water flask",
        "query_desc": "Insulated stainless steel water flask blue with dent on base",
        "target_title": "Hydro Flask thermal tumbler",
        "target_desc": "Matte dark blue Hydro Flask thermal tumbler found by gym locker",
        "description": "Brand vs generic (water flask vs Hydro Flask tumbler)"
    },
    {
        "id": "P03",
        "type": "positive",
        "category": ItemCategory.KEYS,
        "query_title": "Dorm room brass key",
        "query_desc": "Dorm room brass key on black lanyard with tag",
        "target_title": "Campus lanyard with keys",
        "target_desc": "Set of brass keys with campus lanyard found in lecture hall",
        "description": "Colloquial overlap (brass key on lanyard)"
    },
    {
        "id": "P04",
        "type": "positive",
        "category": ItemCategory.BAG,
        "query_title": "North Face commuter bag",
        "query_desc": "Black North Face water resistant commuter bag with notebook inside",
        "target_title": "Dark padded backpack",
        "target_desc": "Dark backpack with padded laptop compartment and rain cover",
        "description": "Visual abstraction (commuter bag vs padded backpack)"
    },
    {
        "id": "P05",
        "type": "positive",
        "category": ItemCategory.DOCUMENT,
        "query_title": "Student ID card",
        "query_desc": "Student ID card with computer science ribbon and barcode",
        "target_title": "University identification card",
        "target_desc": "University identification card in plastic holder found at cafeteria",
        "description": "Institutional synonym (Student ID vs University identification)"
    },
    {
        "id": "P06",
        "type": "positive",
        "category": ItemCategory.ACCESSORY,
        "query_title": "Casio vintage digital watch",
        "query_desc": "Silver Casio vintage digital watch with metal link strap",
        "target_title": "Retro metallic wrist watch",
        "target_desc": "Retro metallic wrist watch with digital display and clasp",
        "description": "Synonym description (vintage digital watch vs retro wrist watch)"
    },
    {
        "id": "P07",
        "type": "positive",
        "category": ItemCategory.ELECTRONICS,
        "query_title": "Wireless earbuds charging case",
        "query_desc": "Wireless earbuds charging case white glossy finish",
        "target_title": "AirPods charging box",
        "target_desc": "AirPods charging case found near library printer station",
        "description": "Generic vs brand term (earbuds case vs AirPods box)"
    },
    {
        "id": "P08",
        "type": "positive",
        "category": ItemCategory.CLOTHING,
        "query_title": "Navy blue hooded sweatshirt",
        "query_desc": "Navy blue hooded sweatshirt with university crest on front",
        "target_title": "Dark blue pullover hoodie",
        "target_desc": "Dark blue pullover hoodie with college embroidery on chest",
        "description": "Clothing synonymy (hooded sweatshirt vs pullover hoodie)"
    },
    {
        "id": "P09",
        "type": "positive",
        "category": ItemCategory.DOCUMENT,
        "query_title": "Leather bifold wallet",
        "query_desc": "Leather bifold wallet containing state driving license",
        "target_title": "Dark brown pocket wallet",
        "target_desc": "Dark brown pocket wallet with government driver ID card",
        "description": "Synonymy (bifold wallet vs pocket wallet)"
    },
    {
        "id": "P10",
        "type": "positive",
        "category": ItemCategory.BOTTLE,
        "query_title": "Clear glass water bottle",
        "query_desc": "Clear glass water bottle with silicone grip sleeve",
        "target_title": "Transparent glass flask",
        "target_desc": "Transparent glass flask with protective rubber coating",
        "description": "Material synonym (glass water bottle vs transparent glass flask)"
    },

    # Hard Negative Test Pairs (Cross-category, Material Divergence, Style Divergence)
    {
        "id": "N01",
        "type": "negative",
        "category": ItemCategory.ELECTRONICS,
        "query_title": "Silver iPad 10th generation",
        "query_desc": "Silver iPad 10th generation tablet with apple pencil",
        "target_title": "Silver MacBook Air",
        "target_desc": "Silver MacBook Air 13 inch laptop computer",
        "description": "Hard Negative: Same brand/color, different device form factor"
    },
    {
        "id": "N02",
        "type": "negative",
        "category": ItemCategory.BOTTLE,
        "query_title": "Stainless steel red mug",
        "query_desc": "Stainless steel red insulated mug with travel lid",
        "target_title": "Red plastic gym bottle",
        "target_desc": "Red plastic reusable gym bottle with measurement markings",
        "description": "Hard Negative: Same color, different material and shape"
    },
    {
        "id": "N03",
        "type": "negative",
        "category": ItemCategory.ACCESSORY,
        "query_title": "Gold framed reading glasses",
        "query_desc": "Gold framed wire rim prescription reading glasses",
        "target_title": "Black sunglasses in hard case",
        "target_desc": "Black polarized sunglasses in protective hard case",
        "description": "Hard Negative: Eyewear category divergence (reading vs sun)"
    },
    {
        "id": "N04",
        "type": "negative",
        "category": ItemCategory.KEYS,
        "query_title": "Honda car key fob",
        "query_desc": "Car key fob with remote button for Honda Civic",
        "target_title": "Single locker key",
        "target_desc": "Single locker key with metal ring and number 42 tag",
        "description": "Hard Negative: Vehicle electronic fob vs mechanical locker key"
    },
    {
        "id": "N05",
        "type": "negative",
        "category": ItemCategory.BAG,
        "query_title": "Leather messenger bag",
        "query_desc": "Leather messenger bag brown with brass buckle and shoulder strap",
        "target_title": "Brown canvas duffle bag",
        "target_desc": "Brown canvas duffle bag for gym with zipper pocket",
        "description": "Hard Negative: Bag style divergence (messenger vs duffle)"
    },
    {
        "id": "N06",
        "type": "negative",
        "category": ItemCategory.ELECTRONICS,
        "query_title": "Over-ear headphones",
        "query_desc": "Black wireless noise cancelling over-ear headphones",
        "target_title": "Bluetooth speaker",
        "target_desc": "Black portable cylindrical bluetooth speaker with strap",
        "description": "Hard Negative: Audio electronics divergence (headphones vs speaker)"
    },
    {
        "id": "N07",
        "type": "negative",
        "category": ItemCategory.CLOTHING,
        "query_title": "Red winter scarf",
        "query_desc": "Red woolen winter scarf with fringe edges",
        "target_title": "Red baseball cap",
        "target_desc": "Red baseball cap with campus athletic department logo",
        "description": "Hard Negative: Clothing divergence (scarf vs cap)"
    },
    {
        "id": "N08",
        "type": "negative",
        "category": ItemCategory.DOCUMENT,
        "query_title": "Blue passport holder",
        "query_desc": "Blue passport holder with international documents",
        "target_title": "Blue ring binder",
        "target_desc": "Blue 3-ring binder with course syllabus and lecture notes",
        "description": "Hard Negative: Document container divergence (passport vs binder)"
    },
    {
        "id": "N09",
        "type": "negative",
        "category": ItemCategory.ACCESSORY,
        "query_title": "Silver braided chain bracelet",
        "query_desc": "Silver braided chain bracelet with small heart charm",
        "target_title": "Stainless steel bike chain lock",
        "target_desc": "Stainless steel bike chain lock with combination dial",
        "description": "Hard Negative: Metal chain jewelry vs bicycle security lock"
    },
    {
        "id": "N10",
        "type": "negative",
        "category": ItemCategory.BOTTLE,
        "query_title": "Green protein shaker bottle",
        "query_desc": "Green plastic shaker bottle with protein mixer wire ball",
        "target_title": "Green ceramic travel mug",
        "target_desc": "Green ceramic coffee travel mug with silicone sip lid",
        "description": "Hard Negative: Fitness shaker bottle vs ceramic coffee mug"
    }
]

class Command(BaseCommand):
    help = "Runs retrieval benchmark across 20 synthetic lost/found evaluation pairs (EVALUATION.md)."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-cleanup',
            action='store_true',
            help='Preserve seeded benchmark records in database instead of deleting after run.'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=5,
            help='Number of candidate matches to retrieve per query (default: 5).'
        )

    def handle(self, *args, **options):
        cleanup = not options['no_cleanup']
        limit = options['limit']

        self.stdout.write(self.style.MIGRATE_HEADING("=== UTN Retrieval Benchmark Suite ==="))
        self.stdout.write(f"NIM Enabled: {settings.NIM_ENABLED} | Model: {settings.NIM_EMBEDDING_MODEL}")
        self.stdout.write(f"Evaluating {len(BENCHMARK_PAIRS)} test pairs (10 Positive, 10 Hard Negative)...\n")

        location, _ = Location.objects.get_or_create(
            name="Benchmark Testing Facility",
            defaults={
                "location_type": LocationType.OTHER,
                "description": "Synthetic isolated location for automated benchmark evaluation."
            }
        )

        created_reports = []
        target_records = {}

        try:
            # 1. Seed Ground-Truth Target Found Reports
            self.stdout.write("1. Seeding ground-truth target FOUND reports...")
            for pair in BENCHMARK_PAIRS:
                target_report = ItemReport.objects.create(
                    title=f"[BENCHMARK] {pair['target_title']}",
                    category=pair['category'],
                    report_type=ReportType.FOUND,
                    public_description=pair['target_desc'],
                    found_location=location,
                    current_holding_location=location,
                    status=ReportStatus.OPEN,
                    visibility=ReportVisibility.ACTIVE
                )
                created_reports.append(target_report)
                target_records[pair['id']] = target_report

                # Generate embedding if NIM is enabled
                MatchingService.trigger_embedding(target_report)

            self.stdout.write(f"   Seeded {len(created_reports)} target reports successfully.\n")

            # 2. Run Retrieval Evaluation
            self.stdout.write("2. Executing retrieval benchmark queries...")
            p_at_1_hits = 0
            p_at_5_hits = 0
            reciprocal_ranks = []
            latencies_ms = []
            results_table = []

            for pair in BENCHMARK_PAIRS:
                # Create synthetic query LOST report
                query_report = ItemReport.objects.create(
                    title=f"[QUERY] {pair['query_title']}",
                    category=pair['category'],
                    report_type=ReportType.LOST,
                    public_description=pair['query_desc'],
                    last_seen_location=location,
                    status=ReportStatus.OPEN,
                    visibility=ReportVisibility.ACTIVE
                )
                created_reports.append(query_report)
                MatchingService.trigger_embedding(query_report)

                # Execute matching
                t0 = time.perf_counter()
                match_result = MatchingService.find_matches_for_report(query_report, limit=limit)
                t1 = time.perf_counter()
                latency_ms = (t1 - t0) * 1000.0
                latencies_ms.append(latency_ms)

                retrieval_mode = match_result.get('retrieval_mode', 'keyword_baseline')
                matches = match_result.get('matches', [])
                target_id = str(target_records[pair['id']].id)

                # Calculate rank and match label of ground-truth target
                target_rank = None
                target_match = None
                for idx, m in enumerate(matches):
                    if m['candidate_report_id'] == target_id:
                        target_rank = idx + 1
                        target_match = m
                        break

                if pair['type'] == 'positive':
                    is_p1 = (target_rank == 1)
                    is_p5 = (target_rank is not None and target_rank <= 5)
                    rr = 1.0 / target_rank if target_rank else 0.0

                    if is_p1:
                        p_at_1_hits += 1
                    if is_p5:
                        p_at_5_hits += 1
                    reciprocal_ranks.append(rr)

                    label_str = target_match.get('match_label', '') if target_match else ''
                    status_str = f"Rank {target_rank} [{label_str}]" if target_rank else "Missed"
                    eval_outcome = "PASS" if is_p5 else "FAIL"
                else:
                    # Hard negative: Target must NOT receive a 'High similarity' false-positive badge
                    high_conf = (target_match and target_match.get('match_label') == 'High similarity')
                    label_str = target_match.get('match_label', '') if target_match else ''
                    eval_outcome = "FAIL (High Conf FP)" if high_conf else "PASS (Restrained)"
                    status_str = f"Rank {target_rank} [{label_str}]" if target_rank else "Filtered"


                results_table.append({
                    "id": pair['id'],
                    "type": pair['type'].upper(),
                    "category": pair['category'],
                    "mode": retrieval_mode,
                    "target_status": status_str,
                    "latency_ms": latency_ms,
                    "outcome": eval_outcome,
                    "description": pair['description']
                })

            # 3. Print Results Breakdown Table
            self.stdout.write("\n" + "=" * 90)
            self.stdout.write(f"{'ID':<5} | {'Type':<8} | {'Category':<12} | {'Rank / Result':<14} | {'Latency':<9} | {'Outcome':<10} | {'Test Concept'}")
            self.stdout.write("-" * 90)
            for row in results_table:
                outcome_style = self.style.SUCCESS if "PASS" in row['outcome'] else self.style.WARNING
                self.stdout.write(
                    f"{row['id']:<5} | {row['type']:<8} | {row['category']:<12} | {row['target_status']:<14} | "
                    f"{row['latency_ms']:>6.1f}ms | {outcome_style(row['outcome']):<19} | {row['description']}"
                )
            self.stdout.write("=" * 90 + "\n")

            # 4. Compute Aggregate Metrics
            num_positives = sum(1 for p in BENCHMARK_PAIRS if p['type'] == 'positive')
            p1_score = (p_at_1_hits / num_positives) * 100.0 if num_positives else 0.0
            p5_score = (p_at_5_hits / num_positives) * 100.0 if num_positives else 0.0
            mrr_score = sum(reciprocal_ranks) / num_positives if num_positives else 0.0
            avg_latency = sum(latencies_ms) / len(latencies_ms) if latencies_ms else 0.0

            self.stdout.write(self.style.SUCCESS("=== Aggregate Retrieval Metrics ==="))
            self.stdout.write(f"• Precision@1 (Top Match Accuracy):  {p1_score:.1f}% ({p_at_1_hits}/{num_positives})")
            self.stdout.write(f"• Precision@5 / Recall@5:            {p5_score:.1f}% ({p_at_5_hits}/{num_positives})")
            self.stdout.write(f"• Mean Reciprocal Rank (MRR):        {mrr_score:.2f}")
            self.stdout.write(f"• Mean Retrieval Latency:            {avg_latency:.2f} ms")
            self.stdout.write("=" * 45 + "\n")

        finally:
            if cleanup and created_reports:
                self.stdout.write("Cleaning up synthetic benchmark reports from database...")
                del_ids = [r.id for r in created_reports]
                ItemEmbedding.objects.filter(report_id__in=del_ids).delete()
                ItemReport.objects.filter(id__in=del_ids).delete()
                if location and location.name == "Benchmark Testing Facility":
                    location.delete()
                self.stdout.write(self.style.SUCCESS(f"Cleaned up {len(created_reports)} temporary benchmark records."))
