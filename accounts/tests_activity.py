from django.contrib.auth.models import User
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import AuditLog, Role


@override_settings(ALLOWED_HOSTS=["testserver", "localhost"])
class ActivityLogTests(TestCase):
    def setUp(self):
        self.root = User.objects.create_superuser("root_test", "root@example.com", "pass12345")
        self.owner = User.objects.create_user("owner_test", password="pass12345")
        owner_role = Role.objects.create(name="Owner")
        self.owner.userprofile.roles.add(owner_role)
        self.technician = User.objects.create_user("tech_test", password="pass12345")
        tech_role = Role.objects.create(name="Teknisi")
        self.technician.userprofile.roles.add(tech_role)

    def test_root_can_view_activity_log(self):
        self.client.force_login(self.root)
        response = self.client.get(reverse("accounts:activity_logs"))
        self.assertEqual(response.status_code, 200)

    def test_owner_can_view_activity_log(self):
        self.client.force_login(self.owner)
        response = self.client.get(reverse("accounts:activity_logs"))
        self.assertEqual(response.status_code, 200)

    def test_other_role_is_forbidden(self):
        self.client.force_login(self.technician)
        response = self.client.get(reverse("accounts:activity_logs"))
        self.assertEqual(response.status_code, 403)

    def test_middleware_logs_successful_post_without_password(self):
        self.client.force_login(self.root)
        self.client.post(reverse("accounts:edit_profile"), {
            "first_name": "Root",
            "last_name": "Test",
            "email": "root@example.com",
            "phone": "08123456789",
            "password": "should-not-be-stored",
        })
        log = AuditLog.objects.filter(user=self.root).latest("created_at")
        self.assertEqual(log.action_type, "update")
        self.assertNotIn("should-not-be-stored", str(log.metadata))
