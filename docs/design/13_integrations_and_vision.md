# Integration with external systems + platform vision

## Integration with external systems

### ITSM Integration (ServiceNow, Jira, etc.)

- **Change request creation**: Automatically create tickets when Request Forms are submitted (or when an Execution is created)
- **Status synchronization**: Update ticket status as Executions progress
- **Device discovery**: Import devices from ITSM CMDB
- **Approval workflows**: Integrate with ITSM approval processes
- **Audit reporting**: Export audit logs to ITSM for compliance

Implementation approach:

- Use API call Tasks to integrate with ITSM APIs
- Store ITSM ticket references in Execution models
- Provide webhook endpoints for ITSM callbacks
- Optional: dedicated ITSM provider for bidirectional sync

### SIEM Integration (Splunk, QRadar, etc.)

- **Event forwarding**: Send change events, compliance failures, vulnerability alerts to SIEM
- **Session log export**: Forward terminal session records for security monitoring
- **Risk score updates**: Push risk score changes to SIEM for correlation

Implementation approach:

- Use webhook/API call Tasks for SIEM integration
- Configurable SIEM endpoints per organization
- Structured event format (JSON) for SIEM ingestion

### Secrets Management Integration

- **Password vault integration**: Pull device credentials from HashiCorp Vault, CyberArk, etc.
- **API key management**: Store and rotate API keys for controller integrations
- **SSO integration**: Support SAML/OIDC for user authentication

Implementation approach:

- Leverage Nautobot Secrets/SecretsGroup
- Create custom Secrets Providers if needed
- Support credential rotation workflows

## Platform vision: Nautobot-native network automation

This platform aims to provide comprehensive network automation capabilities similar to commercial platforms, but built natively on Nautobot as the **automation and execution arm** of the Nautobot ecosystem.

### What makes this platform powerful

1. **Low-code first**: Build automation via UI without writing code
2. **Pro-code capable**: Python hooks and custom providers for advanced use cases
3. **Composable**: Reusable Tasks assembled into Workflows
4. **Multi-platform**: Single Task, multiple vendor implementations
5. **Self-service**: Portal for operators to request work without understanding automation
6. **Integrated**: Works with Device Lifecycle Management, Golden Config, and external ITSM
7. **Auditable**: Full execution history with diffs, logs, and approvals

### What makes this Nautobot-native

1. **Nautobot as source of truth**: All automation reads from and updates Nautobot models
2. **Leverages Nautobot features**: Uses Custom Fields, Relationships, Config Context, Secrets, Jobs
3. **Integrates with Nautobot ecosystem**: Works with Device Lifecycle Management, Golden Config
4. **Follows Nautobot patterns**: Uses NautobotUIViewSet, NautobotModelViewSet, standard RBAC
5. **GitOps-friendly**: Everything can be versioned in Git, imported/exported
6. **Extensible**: Customers can add custom Tasks, Providers, and Workflows
