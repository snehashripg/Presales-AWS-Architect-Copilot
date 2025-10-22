"""Models for BedrockAgentCore runtime.

Contains data models and enums used throughout the runtime system.
"""

from enum import Enum


class PingStatus(str, Enum):
    """Ping status enum for health check responses."""

    HEALTHY = "Healthy"
    HEALTHY_BUSY = "HealthyBusy"


# Header constants
SESSION_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Session-Id"
REQUEST_ID_HEADER = "X-Amzn-Bedrock-AgentCore-Runtime-Request-Id"
ACCESS_TOKEN_HEADER = "WorkloadAccessToken"  # nosec
OAUTH2_CALLBACK_URL_HEADER = "OAuth2CallbackUrl"
AUTHORIZATION_HEADER = "Authorization"
CUSTOM_HEADER_PREFIX = "X-Amzn-Bedrock-AgentCore-Runtime-Custom-"

# Task action constants
TASK_ACTION_PING_STATUS = "ping_status"
TASK_ACTION_JOB_STATUS = "job_status"
TASK_ACTION_FORCE_HEALTHY = "force_healthy"
TASK_ACTION_FORCE_BUSY = "force_busy"
TASK_ACTION_CLEAR_FORCED_STATUS = "clear_forced_status"
