
# ============================================================
# Common trust policy for AgentCore Runtime
# ============================================================

data "aws_iam_policy_document" "agentcore_assume" {
  statement {
    sid     = "AllowAgentCore"
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["bedrock-agentcore.amazonaws.com"]
    }

    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }

    condition {
      test     = "ArnLike"
      variable = "aws:SourceArn"
      values = [
        "arn:aws:bedrock-agentcore:${var.aws_region}:${data.aws_caller_identity.current.account_id}:*"
      ]
    }
  }
}


# ============================================================
# ROLE 1: MCP SERVER
# ============================================================

resource "aws_iam_role" "weather_mcp" {
  name = "${var.project_name}-${var.environment}-mcp-runtime"

  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
}


data "aws_iam_policy_document" "weather_mcp_permissions" {

  # ECR authentication
  statement {
    sid       = "GetEcrAuthorizationToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Pull only the MCP container image
  statement {
    sid = "ReadMcpContainerImage"

    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]

    resources = [
      aws_ecr_repository.weather_mcp.arn
    ]
  }

  # CloudWatch logging
  statement {
    sid = "WriteAgentCoreLogs"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]

    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
    ]
  }

  # Met Office API credentials
  dynamic "statement" {
    for_each = var.metoffice_secret_arn == "" ? [] : [var.metoffice_secret_arn]

    content {
      sid       = "ReadMetOfficeSecret"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [statement.value]
    }
  }
}


resource "aws_iam_role_policy" "weather_mcp" {
  name = "${var.project_name}-${var.environment}-mcp-policy"

  role   = aws_iam_role.weather_mcp.id
  policy = data.aws_iam_policy_document.weather_mcp_permissions.json
}


# ============================================================
# ROLE 2: LANGGRAPH AGENT
# ============================================================

resource "aws_iam_role" "weather_agent" {
  name = "${var.project_name}-${var.environment}-langgraph-runtime"

  assume_role_policy = data.aws_iam_policy_document.agentcore_assume.json
}


data "aws_iam_policy_document" "weather_agent_permissions" {

  # ECR authentication
  statement {
    sid       = "GetEcrAuthorizationToken"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  # Pull only the LangGraph container image
  statement {
    sid = "ReadLangGraphContainerImage"

    actions = [
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer"
    ]

    resources = [
      aws_ecr_repository.weather_agent.arn
    ]
  }

  # CloudWatch logging
  statement {
    sid = "WriteAgentCoreLogs"

    actions = [
      "logs:CreateLogGroup",
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ]

    resources = [
      "arn:aws:logs:${var.aws_region}:${data.aws_caller_identity.current.account_id}:log-group:/aws/bedrock-agentcore/runtimes/*"
    ]
  }

  # Cognito client credentials
  dynamic "statement" {
    for_each = var.cognito_secret_arn == "" ? [] : [var.cognito_secret_arn]

    content {
      sid       = "ReadCognitoSecret"
      actions   = ["secretsmanager:GetSecretValue"]
      resources = [statement.value]
    }
  }
}


resource "aws_iam_role_policy" "weather_agent" {
  name = "${var.project_name}-${var.environment}-langgraph-policy"

  role   = aws_iam_role.weather_agent.id
  policy = data.aws_iam_policy_document.weather_agent_permissions.json
}
