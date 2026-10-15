import logging
import requests
from django.conf import settings
from reports.models import ItemReport, ItemEmbedding, EmbeddingStatus, ReportType, ReportStatus, ReportVisibility
from pgvector.django import CosineDistance

logger = logging.getLogger(__name__)

class NimEmbeddingAdapter:
    """
    Adapter for NVIDIA NIM embedding endpoints.
    Strictly isolated: never sends PII or private details to NVIDIA.
    """
    @classmethod
    def get_embedding(cls, text: str) -> list[float] | None:
        if not settings.NIM_ENABLED or not settings.NIM_API_KEY:
            return None

        clean_text = text.strip()[:2000]
        if not clean_text:
            return None

        url = f"{settings.NIM_BASE_URL}/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.NIM_API_KEY}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        payload = {
            "input": [clean_text],
            "model": settings.NIM_EMBEDDING_MODEL,
            "input_type": "passage",
            "encoding_format": "float"
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=settings.NIM_TIMEOUT_SECONDS)
            if res.status_code == 200:
                data = res.json()
                embedding = data['data'][0]['embedding']
                if len(embedding) == settings.NIM_EMBEDDING_DIMENSION:
                    return embedding
                logger.error(f"NIM returned vector dimension {len(embedding)}, expected {settings.NIM_EMBEDDING_DIMENSION}")
            else:
                logger.warning(f"NIM embedding request failed: {res.status_code} - {res.text[:200]}")
        except Exception as e:
            logger.error(f"Error calling NVIDIA NIM embedding API: {e}")

        return None

class MatchingService:
    @classmethod
    def prepare_safe_searchable_text(cls, report: ItemReport) -> str:
        """
        Compiles public attributes only for embedding and search.
        Zero contact details or secret verification attributes.
        """
        parts = [
            f"Category: {report.category}",
            f"Title: {report.title}",
            f"Description: {report.public_description}"
        ]
        return ". ".join(parts)

    @classmethod
    def trigger_embedding(cls, report: ItemReport) -> None:
        """
        Computes embedding if NIM is enabled.
        Never fails or blocks report creation on NIM failure.
        """
        if not settings.NIM_ENABLED or not settings.NIM_API_KEY:
            return

        try:
            safe_text = cls.prepare_safe_searchable_text(report)
            vector = NimEmbeddingAdapter.get_embedding(safe_text)
            
            emb_record, _ = ItemEmbedding.objects.get_or_create(report=report)
            if vector:
                emb_record.embedding = vector
                emb_record.embedding_status = EmbeddingStatus.READY
                emb_record.model_name = settings.NIM_EMBEDDING_MODEL
            else:
                emb_record.embedding_status = EmbeddingStatus.FAILED
            emb_record.save()
        except Exception as e:
            logger.error(f"Failed to record embedding for report {report.id}: {e}")

    @classmethod
    def find_matches_for_report(cls, report: ItemReport, limit: int = 10) -> dict:
        """
        Hybrid matching:
        - If query report is LOST -> search among OPEN FOUND reports.
        - If query report is FOUND -> search among OPEN LOST reports.
        - Combines deterministic keyword signals with pgvector semantic similarity.
        """
        target_type = ReportType.FOUND if report.report_type == ReportType.LOST else ReportType.LOST
        candidates_qs = ItemReport.objects.filter(
            report_type=target_type,
            status=ReportStatus.OPEN,
            visibility=ReportVisibility.ACTIVE
        ).select_related('last_seen_location', 'found_location', 'current_holding_location')

        # Check for vector embedding
        has_vector = False
        vector_candidates = []
        try:
            emb_record = getattr(report, 'embedding_record', None)
            if not emb_record:
                emb_record = ItemEmbedding.objects.filter(report=report, embedding_status=EmbeddingStatus.READY).first()

            if emb_record and emb_record.embedding is not None:
                # Query nearest neighbours using pgvector CosineDistance
                with_dist = candidates_qs.filter(
                    embedding_record__embedding_status=EmbeddingStatus.READY,
                    embedding_record__embedding__isnull=False
                ).annotate(
                    distance=CosineDistance('embedding_record__embedding', emb_record.embedding)
                ).order_by('distance')[:limit * 2]
                
                vector_candidates = list(with_dist)
                has_vector = len(vector_candidates) > 0
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to keywords: {e}")

        # Deterministic keyword baseline retrieval
        keywords = [w.lower() for w in (report.title + " " + report.public_description).split() if len(w) > 3][:6]
        keyword_candidates = []
        if keywords:
            from django.db.models import Q
            q_filter = Q()
            for kw in keywords:
                q_filter |= Q(title__icontains=kw) | Q(public_description__icontains=kw)
            keyword_candidates = list(candidates_qs.filter(q_filter)[:limit * 2])

        # Merge candidate pools
        all_candidates = {}
        for c in vector_candidates:
            all_candidates[c.id] = {'obj': c, 'vector_dist': getattr(c, 'distance', 1.0), 'kw_hit': False}
        for c in keyword_candidates:
            if c.id not in all_candidates:
                all_candidates[c.id] = {'obj': c, 'vector_dist': 1.0, 'kw_hit': True}
            else:
                all_candidates[c.id]['kw_hit'] = True

        # Fallback to category candidates if pool is still small
        if len(all_candidates) < 5:
            cat_candidates = candidates_qs.filter(category=report.category)[:10]
            for c in cat_candidates:
                if c.id not in all_candidates:
                    all_candidates[c.id] = {'obj': c, 'vector_dist': 1.0, 'kw_hit': False}

        # Calculate hybrid rank score
        ranked = []
        for cid, data in all_candidates.items():
            candidate = data['obj']
            score = 0.0

            # 1. Category agreement
            if candidate.category == report.category:
                score += 3.0

            # 2. Semantic vector similarity (1.0 - distance)
            if data['vector_dist'] < 1.0:
                similarity = max(0.0, 1.0 - data['vector_dist'])
                score += similarity * 5.0

            # 3. Keyword hit
            if data['kw_hit']:
                score += 2.0

            # 4. Location agreement
            cand_loc = candidate.found_location or candidate.last_seen_location
            rep_loc = report.last_seen_location or report.found_location
            if cand_loc and rep_loc and cand_loc == rep_loc:
                score += 2.0

            ranked.append({
                'candidate': candidate,
                'score': score,
                'vector_dist': data.get('vector_dist', 1.0),
                'kw_hit': data.get('kw_hit', False)
            })

        ranked.sort(key=lambda x: x['score'], reverse=True)
        top_candidates = ranked[:limit]

        matches_list = []
        for item in top_candidates:
            c = item['candidate']
            loc = c.current_holding_location or c.found_location or c.last_seen_location
            loc_label = loc.name if loc else "Participating location"

            # Confidence thresholding per TRD Section 5 & EVALUATION.md
            v_dist = item.get('vector_dist', 1.0)
            if v_dist < 0.35:
                match_label = "High similarity"
            elif v_dist <= 0.55:
                match_label = "Possible match"
            elif item.get('kw_hit'):
                match_label = "Keyword match"
            else:
                match_label = "Possible match"

            matches_list.append({
                "candidate_report_id": str(c.id),
                "category": c.category,
                "title": c.title,
                "public_description": c.public_description,
                "safe_location_label": loc_label,
                "reported_at": c.created_at.isoformat(),
                "match_label": match_label
            })

        return {
            "report_id": str(report.id),
            "retrieval_mode": "hybrid" if has_vector else "keyword_baseline",
            "matches": matches_list
        }
