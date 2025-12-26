"""
API Serializers v2.0

Properly exposes all fields including template_content.
Supports nested strategy creation/update.
"""
from rest_framework import serializers
from nautobot.apps.api import NautobotModelSerializer
from nautobot.dcim.api.serializers import PlatformSerializer
from ..models import TaskIntent, TaskStrategy, Workflow, Folder, RequestForm, Execution


class TaskStrategySerializer(NautobotModelSerializer):
    """
    Serializer for TaskStrategy (platform-specific implementations).
    
    Fully exposes template_content and method_config for Studio editing.
    """
    platform_detail = PlatformSerializer(source='platform', read_only=True)
    effective_template = serializers.ReadOnlyField()
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    
    class Meta:
        model = TaskStrategy
        fields = [
            "id",
            "url",
            "name",
            "task_intent",
            "platform",
            "platform_detail",
            "method",
            "method_display",
            "priority",
            "enabled",
            "template_content",
            "effective_template",
            "method_config",
            "inherit_from",
            # Metadata
            "created",
            "last_updated",
        ]
        read_only_fields = ["id", "url", "created", "last_updated"]


class TaskStrategyNestedSerializer(NautobotModelSerializer):
    """
    Nested serializer for strategies within TaskIntent.
    Used for read operations - shows strategies inline.
    """
    platform_name = serializers.CharField(source='platform.name', read_only=True)
    platform_slug = serializers.CharField(source='platform.slug', read_only=True)
    method_display = serializers.CharField(source='get_method_display', read_only=True)
    
    class Meta:
        model = TaskStrategy
        fields = [
            "id",
            "name",
            "platform",
            "platform_name",
            "platform_slug",
            "method",
            "method_display",
            "priority",
            "enabled",
            "template_content",
            "method_config",
        ]


class TaskIntentSerializer(NautobotModelSerializer):
    """
    Serializer for TaskIntent.
    
    Includes nested strategies for read operations.
    Supports the new 'inputs' field structure.
    """
    strategies = TaskStrategyNestedSerializer(many=True, read_only=True)
    
    # Computed fields
    input_count = serializers.ReadOnlyField()
    strategy_count = serializers.ReadOnlyField()
    
    # Legacy field mapping for backwards compatibility
    implementations = TaskStrategyNestedSerializer(
        source='strategies', 
        many=True, 
        read_only=True
    )
    
    class Meta:
        model = TaskIntent
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "category",
            "folder",
            # The contract (inputs)
            "inputs",
            "input_schema",  # Legacy
            "variable_mappings",  # Legacy
            # Validation & rollback
            "validation_config",
            "rollback_template",
            # Git sync metadata
            "source_file",
            "source_hash",
            "last_synced",
            # Computed
            "input_count",
            "strategy_count",
            # Nested strategies
            "strategies",
            "implementations",  # Legacy alias
            # Metadata
            "created",
            "last_updated",
        ]
        read_only_fields = [
            "id", "url", "created", "last_updated",
            "input_count", "strategy_count"
        ]


class TaskIntentListSerializer(NautobotModelSerializer):
    """
    Lightweight serializer for task list views.
    Excludes nested strategies for performance.
    """
    input_count = serializers.ReadOnlyField()
    strategy_count = serializers.ReadOnlyField()
    
    class Meta:
        model = TaskIntent
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "category",
            "folder",
            "input_count",
            "strategy_count",
            "source_file",
        ]


# ═══════════════════════════════════════════════════════════════════════════
# OTHER SERIALIZERS
# ═══════════════════════════════════════════════════════════════════════════
class WorkflowSerializer(NautobotModelSerializer):
    class Meta:
        model = Workflow
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "graph_definition",
            "enabled",
            "approval_required",
            "folder",
            "created",
            "last_updated",
        ]


class FolderSerializer(NautobotModelSerializer):
    class Meta:
        model = Folder
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "parent",
            "created",
            "last_updated",
        ]


class RequestFormSerializer(NautobotModelSerializer):
    class Meta:
        model = RequestForm
        fields = [
            "id",
            "url",
            "name",
            "slug",
            "description",
            "workflow",
            "published",
            "field_definition",
            "folder",
            "created",
            "last_updated",
        ]


class ExecutionSerializer(NautobotModelSerializer):
    class Meta:
        model = Execution
        fields = [
            "id",
            "url",
            "workflow",
            "request_form",
            "status",
            "user",
            "input_data",
            "start_time",
            "end_time",
            "created",
            "last_updated",
        ]
