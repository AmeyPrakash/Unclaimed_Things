from django.urls import reverse
from rest_framework.test import APITestCase
from accounts.models import User
from locations.models import Location, LocationType, LocationMembership, MembershipRole
from reports.models import ItemReport, ReportPrivateDetail, ReportType, ItemCategory, ReportStatus
from reports.serializers import PublicItemReportSerializer

class BackendFoundationTests(APITestCase):
    def setUp(self):
        self.location = Location.objects.create(
            name="Test Campus Library",
            location_type=LocationType.LIBRARY,
            description="Public test location"
        )
        self.regular_user = User.objects.create_user(
            email="regular@campus.edu",
            password="Password123!",
            display_name="Regular Student"
        )
        self.staff_user = User.objects.create_user(
            email="staff@campus.edu",
            password="Password123!",
            display_name="Staff Member"
        )
        LocationMembership.objects.create(
            user=self.staff_user,
            location=self.location,
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
            "email": "regular@campus.edu",
            "password": "Password123!"
        })
        self.assertEqual(login_res.status_code, 200)
        self.assertEqual(login_res.data['user']['email'], "regular@campus.edu")

        me_res = self.client.get(reverse('auth-me'))
        self.assertEqual(me_res.status_code, 200)
        self.assertEqual(me_res.data['user']['email'], "regular@campus.edu")

    def test_privacy_boundary_never_leaks_private_details(self):
        report = ItemReport.objects.create(
            title="Keys with red keychain",
            category=ItemCategory.KEYS,
            report_type=ReportType.FOUND,
            public_description="Found set of 3 brass keys",
            found_location=self.location,
            current_holding_location=self.location
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
