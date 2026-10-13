from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from locations.models import Location, LocationType, LocationMembership, MembershipRole
from reports.models import ItemReport, ReportPrivateDetail, ReportType, ItemCategory, ReportStatus, ReportVisibility
from matching.services import MatchingService

class Command(BaseCommand):
    help = "Seeds initial synthetic pilot locations, staff accounts, and test reports."

    def handle(self, *args, **options):
        self.stdout.write("Seeding pilot locations...")
        lib, _ = Location.objects.get_or_create(
            name="Central Campus Library",
            defaults={
                "location_type": LocationType.LIBRARY,
                "description": "Main campus library front desk and lost-and-found cabinet."
            }
        )
        sec, _ = Location.objects.get_or_create(
            name="Campus Security Office",
            defaults={
                "location_type": LocationType.SECURITY_OFFICE,
                "description": "Main campus gate security office near the north entrance."
            }
        )
        bus, _ = Location.objects.get_or_create(
            name="College Bus Transit Depot",
            defaults={
                "location_type": LocationType.BUS_SERVICE,
                "description": "Transit operations desk at the campus bus terminal."
            }
        )

        self.stdout.write("Seeding test users...")
        admin, created = User.objects.get_or_create(
            email="admin@campus.edu",
            defaults={"display_name": "Campus Administrator", "is_staff": True, "is_superuser": True}
        )
        if created:
            admin.set_password("AdminPass123!")
            admin.save()

        lib_staff, created = User.objects.get_or_create(
            email="library.staff@campus.edu",
            defaults={"display_name": "Library Staff"}
        )
        if created:
            lib_staff.set_password("StaffPass123!")
            lib_staff.save()
        LocationMembership.objects.get_or_create(
            user=lib_staff,
            location=lib,
            role=MembershipRole.LOCATION_STAFF
        )

        sec_staff, created = User.objects.get_or_create(
            email="security.staff@campus.edu",
            defaults={"display_name": "Security Staff"}
        )
        if created:
            sec_staff.set_password("StaffPass123!")
            sec_staff.save()
        LocationMembership.objects.get_or_create(
            user=sec_staff,
            location=sec,
            role=MembershipRole.LOCATION_STAFF
        )

        student1, created = User.objects.get_or_create(
            email="student1@campus.edu",
            defaults={"display_name": "Alice Sharma"}
        )
        if created:
            student1.set_password("StudentPass123!")
            student1.save()

        student2, created = User.objects.get_or_create(
            email="student2@campus.edu",
            defaults={"display_name": "Bob Verma"}
        )
        if created:
            student2.set_password("StudentPass123!")
            student2.save()

        self.stdout.write("Seeding sample reports...")
        # 1. Found Blue Water Bottle in Library
        found_bottle, created = ItemReport.objects.get_or_create(
            title="Matte blue metal water bottle",
            defaults={
                "report_type": ReportType.FOUND,
                "created_by": lib_staff,
                "category": ItemCategory.BOTTLE,
                "public_description": "Insulated stainless steel dark blue bottle found on 2nd floor reading hall table.",
                "found_at": timezone.now() - timedelta(days=1),
                "found_location": lib,
                "current_holding_location": lib,
                "status": ReportStatus.OPEN,
                "visibility": ReportVisibility.ACTIVE
            }
        )
        if created:
            ReportPrivateDetail.objects.create(
                report=found_bottle,
                private_description="Has a subtle scratch on the base and a faded white bird sticker.",
                distinguishing_details={"brand": "HydroFlask", "sticker": "White bird"}
            )
            MatchingService.trigger_embedding(found_bottle)

        # 2. Lost Water bottle by Student
        lost_bottle, created = ItemReport.objects.get_or_create(
            title="Lost dark blue HydroFlask flask",
            defaults={
                "report_type": ReportType.LOST,
                "created_by": student1,
                "category": ItemCategory.BOTTLE,
                "public_description": "Dark blue insulated water bottle left somewhere in the library yesterday afternoon.",
                "last_seen_at": timezone.now() - timedelta(days=1),
                "last_seen_location": lib,
                "status": ReportStatus.OPEN,
                "visibility": ReportVisibility.ACTIVE
            }
        )
        if created:
            ReportPrivateDetail.objects.create(
                report=lost_bottle,
                private_description="There is a small bird sticker near the bottom.",
                distinguishing_details={"capacity": "750ml"}
            )
            MatchingService.trigger_embedding(lost_bottle)

        self.stdout.write(self.style.SUCCESS("Successfully seeded pilot locations, accounts, and sample reports!"))
