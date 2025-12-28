#!/usr/bin/env python
"""Verify that nautobot_network_provisioning is properly installed."""
import sys

try:
    import nautobot_network_provisioning
    print(f"✓ nautobot_network_provisioning version {nautobot_network_provisioning.__version__} installed")
    
    # Check models
    from nautobot_network_provisioning.models import (
        TaskIntent, TaskStrategy, Workflow, RequestForm, Execution
    )
    print("✓ All models importable")
    
    # Check views
    from nautobot_network_provisioning import views
    print("✓ Views module importable")
    
    # Check services
    from nautobot_network_provisioning.services import execution_engine
    print("✓ Services module importable")
    
    print("\n✅ Installation verified successfully!")
    sys.exit(0)
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error: {e}")
    sys.exit(1)

