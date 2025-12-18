"""Phase 1/2 smoke tests (skipped outside a Nautobot/Django test environment)."""

import pytest

pytest.importorskip("django")

from django.test import TestCase

from nautobot_network_provisioning.api.serializers import TaskDefinitionSerializer
from nautobot_network_provisioning.filters import TaskDefinitionFilterSet
from nautobot_network_provisioning.models import TaskDefinition
from nautobot_network_provisioning.tables import TaskDefinitionTable
from nautobot_network_provisioning.views import TaskDefinitionUIViewSet


class Phase1SmokeTest(TestCase):
    def test_taskdefinition_viewset_wiring(self):
        self.assertEqual(TaskDefinitionUIViewSet.queryset.model, TaskDefinition)
        self.assertEqual(TaskDefinitionUIViewSet.table_class, TaskDefinitionTable)
        self.assertEqual(TaskDefinitionUIViewSet.filterset_class, TaskDefinitionFilterSet)
        self.assertEqual(TaskDefinitionUIViewSet.serializer_class, TaskDefinitionSerializer)


