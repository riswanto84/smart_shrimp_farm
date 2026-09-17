from decimal import Decimal
from django.contrib.auth.models import User
from django.test import TestCase
from payroll.models import Employee
from .models import EmployeeAdvance, AIAction
from .services.agent import interpret_command

class AIEmployeeStage1Tests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="test")
        self.employee = Employee.objects.create(employee_code="KRY-001", name="Budi Santoso", position="Teknisi", base_salary=Decimal("4500000"))

    def test_kasbon_creates_draft_only(self):
        result = interpret_command(self.user, "Kasbon Budi Rp500.000 untuk operasional tambak")
        self.assertTrue(result["ok"])
        self.assertEqual(result["type"], "draft")
        self.assertEqual(AIAction.objects.count(), 1)
        self.assertEqual(EmployeeAdvance.objects.count(), 0)

    def test_balance_read(self):
        EmployeeAdvance.objects.create(employee=self.employee, advance_date="2026-09-17", amount=Decimal("1000000"))
        result = interpret_command(self.user, "Berapa saldo kasbon Budi?")
        self.assertTrue(result["ok"])
        self.assertIn("Rp1.000.000", result["message"])
