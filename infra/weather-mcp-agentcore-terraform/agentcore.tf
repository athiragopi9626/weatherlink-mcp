
# ============================================================
# AgentCore Runtime 1: MCP Weather Server
# ============================================================

resource "aws_bedrockagentcore_agent_runtime" "weather_mcp" {
  count = var.deploy_runtime ? 1 : 0

  agent_runtime_name = replace(
    "${var.project_name}_${var.environment}",
    "-",
    "_"
  )

  description = "Weather MCP server with Cognito M2M JWT inbound authentication"

  # Dedicated MCP execution role
  role_arn = aws_iam_role.weather_mcp.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.weather_mcp.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "MCP"
  }

  # Cognito JWT authentication for inbound MCP requests
  authorizer_configuration {
    custom_jwt_authorizer {
      discovery_url = "https://cognito-idp.${var.aws_region}.amazonaws.com/${aws_cognito_user_pool.mcp.id}/.well-known/openid-configuration"

      allowed_clients = [
        aws_cognito_user_pool_client.langgraph.id
      ]

      allowed_scopes = [
        "${aws_cognito_resource_server.mcp.identifier}/invoke"
      ]
    }
  }

  environment_variables = {
    LOG_LEVEL            = "INFO"
    AWS_REGION           = var.aws_region
    METOFFICE_SECRET_ARN = var.metoffice_secret_arn
  }

  depends_on = [
    aws_iam_role_policy.weather_mcp
  ]
}


# ============================================================
# AgentCore Runtime 2: LangGraph Weather Agent
# ============================================================

resource "aws_bedrockagentcore_agent_runtime" "weather_agent" {
  count = var.deploy_runtime ? 1 : 0

  agent_runtime_name = replace(
    "${var.project_name}_${var.environment}_agent",
    "-",
    "_"
  )

  description = "LangGraph weather agent"

  # Dedicated LangGraph execution role
  role_arn = aws_iam_role.weather_agent.arn

  agent_runtime_artifact {
    container_configuration {
      container_uri = "${aws_ecr_repository.weather_agent.repository_url}:${var.image_tag}"
    }
  }

  network_configuration {
    network_mode = "PUBLIC"
  }

  protocol_configuration {
    server_protocol = "HTTP"
  }

  environment_variables = {
    LOG_LEVEL  = "INFO"
    AWS_REGION = var.aws_region

    # Cognito credentials stored in Secrets Manager
    COGNITO_SECRET_ARN = var.cognito_secret_arn

    # Deployed MCP Runtime HTTPS endpoint
    MCP_SERVER_URL = "https://bedrock-agentcore.${var.aws_region}.amazonaws.com/runtimes/${urlencode(aws_bedrockagentcore_agent_runtime.weather_mcp[0].agent_runtime_arn)}/invocations?qualifier=DEFAULT"
  }

  depends_on = [
    aws_iam_role_policy.weather_agent
  ]
}
