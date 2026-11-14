resource "aws_cognito_user_pool" "mcp" {
  name = "${var.project_name}-${var.environment}"
}

resource "aws_cognito_user_pool_domain" "mcp" {
  domain       = var.cognito_domain_prefix
  user_pool_id = aws_cognito_user_pool.mcp.id
}

resource "aws_cognito_resource_server" "mcp" {
  identifier   = "weather-mcp"
  name         = "Weather MCP API"
  user_pool_id = aws_cognito_user_pool.mcp.id

  scope {
    scope_name        = "invoke"
    scope_description = "Invoke the weather MCP server"
  }
}

resource "aws_cognito_user_pool_client" "langgraph" {
  name                                 = "${var.project_name}-${var.environment}-langgraph"
  user_pool_id                         = aws_cognito_user_pool.mcp.id
  generate_secret                      = true
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["client_credentials"]
  allowed_oauth_scopes                 = ["${aws_cognito_resource_server.mcp.identifier}/invoke"]
  access_token_validity                = 60
  token_validity_units {
    access_token = "minutes"
  }
  enable_token_revocation = true
  depends_on = [aws_cognito_resource_server.mcp]
}
