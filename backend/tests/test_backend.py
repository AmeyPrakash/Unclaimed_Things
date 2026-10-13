import io
from PIL import Image, ExifTags
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from accounts.models import User
from locations.models import Location, LocationType, LocationMembership, MembershipRole
from reports.models import ItemReport, ReportPrivateDetail, ReportType, ItemCategory, ReportStatus, ReportImage
from reports.serializers import PublicItemReportSerializer
from claims.models import Claim, ClaimStatus
from custody.models import CustodyEvent, CustodyEventType

class BackendFoundationTests(APITestCase):
    def setUp(self):
        self.library = Location.objects.create(
            name="Test Campus Library",
            location_type=LocationType.LIBRARY,
            description="Public library test location"
        )
        self.security_hq = Location.objects.create(
            name="Campus Security HQ",
            location_type=LocationType.SECURITY_OFFICE,
            description="Central campus security station"
        )
        self.student = User.objects.create_user(
            email="student@campus.edu",
            password="Password123!",
            display_name="Student Claimant"
        )
        self.other_student = User.objects.create_user(
            email="other@campus.edu",
            password="Password123!",
            display_name="Other Student"
        )
        self.library_staff = User.objects.create_user(
            email="library.staff@campus.edu",
            password="Password123!",
            display_name="Library Staff"
        )
        LocationMembership.objects.create(
            user=self.library_staff,
            location=self.library,
            role=MembershipRole.LOCATION_STAFF
        )
        self.security_staff = User.objects.create_user(
            email="security.staff@campus.edu",
            password="Password123!",
            display_name="Security Staff"
        )
        LocationMembership.objects.create(
            user=self.security_staff,
            location=self.security_hq,
            role=MembershipRole.LOCATION_STAFF
        )

    def test_health_endpoints(self):
        live_res = self.client.get(reverse('health-live'))
        self.assertEqual(live_res.status_code, 200)
        self.assertEqual(live_res.data['status'], 'ok')

        ready_res = self.client.get(reverse('health-ready'))
        self.assertEqual(ready_res.status_code, 200)
        self.assertEqual(ready_res.data['status'], 'ready')
        self.assertEqual(ready_res.data['checks']['database'], 'healthy')
        self.assertEqual(ready_res.data['checks']['pgvector'], 'installed')

    def test_authentication_flow(self):
        login_res = self.client.post(reverse('auth-login'), {
            "email": "student@campus.edu",
            "password": "Password123!"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.data['user']['email'], "student@campus.edu")

        me_res = self.client.get(reverse('auth-me'))
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.data['user']['email'], "student@campus.edu")

    def test_privacy_boundary_never_leaks_private_details(self):
        report = ItemReport.objects.create(
            title="Keys with red keychain",
            category=ItemCategory.KEYS,
            report_type=ReportType.FOUND,
            public_description="Found set of 3 brass keys",
            found_location=self.library,
            current_holding_location=self.library
        )
        ReportPrivateDetail.objects.create(
            report=report,
            private_description="Key tag has phone number 9999999999 and dorm room 204",
            distinguishing_details={"room": "204", "phone": "9999999999"}
        )

        data = PublicItemReportSerializer(report).data
        self.assertNotIn("private_description", data)
        self.assertNotIn("distinguishing_details", data)
        self.assertNotIn("9999999999", str(data))
        self.assertNotIn("dorm room", str(data))

    def test_image_upload_and_exif_stripping(self):
        self.client.force_authenticate(user=self.student)
        report = ItemReport.objects.create(
            title="Lost Backpack",
            category=ItemCategory.BAG,
            report_type=ReportType.LOST,
            public_description="Black waterproof canvas backpack",
            created_by=self.student
        )

        # Create test JPEG with embedded EXIF metadata
        img = Image.new("RGB", (64, 64), color="blue")
        exif = img.getexif()
        exif[ExifTags.Base.Make] = "CameraCorp"
        exif[ExifTags.Base.Model] = "ModelSecret-X"
        buf = io.BytesIO()
        img.save(buf, format="JPEG", exif=exif)
        buf.seek(0)

        uploaded = SimpleUploadedFile("backpack_photo.jpg", buf.getvalue(), content_type="image/jpeg")
        url = reverse('report-upload-image', kwargs={'pk': report.id})
        res = self.client.post(url, {'image': uploaded}, format='multipart')

        self.assertEqual(res.status_code, 201)
        self.assertTrue(ReportImage.objects.filter(report=report).exists())

        # Inspect stored image on disk / storage: verify EXIF is completely stripped
        saved_img_rec = ReportImage.objects.get(report=report)
        with saved_img_rec.image_file.open("rb") as f:
            saved_pil = Image.open(f)
            self.assertEqual(len(saved_pil.getexif()), 0, "EXIF metadata must be completely stripped")

    def test_end_to_end_lost_found_match_claim_handover_lifecycle(self):
        # 1. Student reports lost laptop
        self.client.force_authenticate(user=self.student)
        lost_res = self.client.post(reverse('report-lost-create'), {
            "title": "Silver MacBook Pro 14 inch",
            "category": "ELECTRONICS",
            "public_description": "Apple silver laptop in grey neoprene sleeve",
            "private_description": "Serial number C02G12345XYZ and sticker on palm rest",
            "distinguishing_details": {"serial": "C02G12345XYZ"}
        }, format='json')
        self.assertEqual(lost_res.status_code, 201)
        lost_id = lost_res.data['id']

        # 2. Staff at Library registers found laptop
        self.client.force_authenticate(user=self.library_staff)
        found_res = self.client.post(reverse('report-found-create'), {
            "title": "Silver Apple laptop 14-inch",
            "category": "ELECTRONICS",
            "public_description": "Found on second floor library study desk in grey sleeve",
            "found_location": str(self.library.id),
            "current_holding_location": str(self.library.id),
            "private_description": "Apple laptop with sticker on palm rest",
        }, format='json')
        self.assertEqual(found_res.status_code, 201)
        found_id = found_res.data['id']

        # 3. Retrieve matches for lost report
        match_res = self.client.get(reverse('report-matches', kwargs={'pk': lost_id}))
        self.assertEqual(match_res.status_code, 200)
        candidate_ids = [m['candidate_report_id'] for m in match_res.data['matches']]
        self.assertIn(str(found_id), candidate_ids, "Candidate retrieval must surface the matching found report")

        # 4. Student submits ownership claim on found item
        self.client.force_authenticate(user=self.student)
        claim_res = self.client.post(reverse('report-claim-create', kwargs={'pk': found_id}), {
            "claimant_statement": "This is my laptop. Serial number is C02G12345XYZ and sticker is a blue rocket."
        }, format='json')
        self.assertEqual(claim_res.status_code, 201)
        claim_id = claim_res.data['id']

        # 5. Library staff reviews pending claims
        self.client.force_authenticate(user=self.library_staff)
        staff_claims_res = self.client.get(reverse('claims-staff'))
        self.assertEqual(staff_claims_res.status_code, 200)
        review_claim_ids = [c['id'] for c in staff_claims_res.data]
        self.assertIn(str(claim_id), review_claim_ids)

        # 6. Library staff approves claim
        approve_res = self.client.post(reverse('claim-decide', kwargs={'pk': claim_id, 'decision': 'approve'}), {
            "note": "Verified serial number and photo ID with student"
        }, format='json')
        self.assertEqual(approve_res.status_code, 200)
        self.assertEqual(approve_res.data['status'], ClaimStatus.APPROVED)

        # 7. Library staff marks handover complete
        handover_res = self.client.post(reverse('claim-complete-handover', kwargs={'pk': claim_id}))
        self.assertEqual(handover_res.status_code, 200, getattr(handover_res, 'data', None))

        # 8. Verify found report status is updated to RETURNED
        found_report = ItemReport.objects.get(id=found_id)
        self.assertEqual(found_report.status, ReportStatus.RETURNED)

        # 9. Verify immutable custody event log
        handover_event = CustodyEvent.objects.filter(
            report=found_report,
            event_type=CustodyEventType.HANDOVER_COMPLETED
        ).first()
        self.assertIsNotNone(handover_event)
        self.assertEqual(handover_event.actor, self.library_staff)

    def test_custody_transfer_workflow_and_acknowledgement(self):
        found_report = ItemReport.objects.create(
            title="Calculus Textbook",
            category=ItemCategory.DOCUMENT,
            report_type=ReportType.FOUND,
            public_description="Hardcover 9th edition Stewart Calculus",
            found_location=self.library,
            current_holding_location=self.library
        )

        # Library staff requests transfer to Security HQ
        self.client.force_authenticate(user=self.library_staff)
        req_res = self.client.post(reverse('report-custody-transfer-request', kwargs={'pk': found_report.id}), {
            "to_location_id": str(self.security_hq.id),
            "note_private": "Transferring to central security office for overnight safekeeping"
        }, format='json')
        self.assertEqual(req_res.status_code, 201)
        transfer_event_id = req_res.data['id']

        # Critical invariant: Holding location must NOT change before acknowledgement
        found_report.refresh_from_db()
        self.assertEqual(found_report.current_holding_location, self.library)

        # Security staff views pending transfers
        self.client.force_authenticate(user=self.security_staff)
        pending_res = self.client.get(reverse('custody-transfers-pending'))
        self.assertEqual(pending_res.status_code, 200)
        pending_ids = [e['id'] for e in pending_res.data]
        self.assertIn(str(transfer_event_id), pending_ids)

        # Security staff accepts and acknowledges receipt
        accept_res = self.client.post(reverse('custody-transfer-accept', kwargs={'pk': transfer_event_id}), {
            "note_private": "Received textbook from campus courier; placed in Locker B-4"
        }, format='json')
        self.assertEqual(accept_res.status_code, 200)

        # Verify current holding location is now Security HQ
        found_report.refresh_from_db()
        self.assertEqual(found_report.current_holding_location, self.security_hq)

    def test_claim_idor_protection(self):
        found_report = ItemReport.objects.create(
            title="Water Bottle",
            category=ItemCategory.BOTTLE,
            report_type=ReportType.FOUND,
            public_description="White metal bottle",
            found_location=self.library,
            current_holding_location=self.library
        )
        claim = Claim.objects.create(
            report=found_report,
            claimant=self.student,
            claimant_statement="Confidential: my name is etched on underside"
        )

        # Other student attempts to access student's claim directly
        self.client.force_authenticate(user=self.other_student)
        idor_res = self.client.get(reverse('claim-detail', kwargs={'pk': claim.id}))
        self.assertEqual(idor_res.status_code, 403, "Other students must not be able to read foreign claims")
