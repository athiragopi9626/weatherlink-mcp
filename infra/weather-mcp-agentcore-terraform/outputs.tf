output "ecr_repository_url" {
  value = aws_ecr_repository.weather_mcp.repository_url
}

output "cognito_user_pool_id" {
  value = aws_cognito_user_pool.mcp.id
}

output "cognito_client_id" {
  value = aws_cognito_user_pool_client.langgraph.id
}

output "cognito_token_endpoint" {
  value = "https://${aws_cognito_user_pool_domain.mcp.domain}.auth.${var.aws_region}.amazoncognito.com/oauth2/token"
}

output "cognito_scope" {
  value = "${aws_cognito_resource_server.mcp.identifier}/invoke"
}

output "agentcore_runtime_arn" {
  value = var.deploy_runtime ? aws_bedrockagentcore_agent_runtime.weather_mcp[0].agent_runtime_arn : null
}

output "agentcore_runtime_id" {
  value = var.deploy_runtime ? aws_bedrockagentcore_agent_runtime.weather_mcp[0].agent_runtime_id : null
}

output "weather_agent_ecr_repository_url" {
  description = "ECR repository URL for the LangGraph agent"
  value       = aws_ecr_repository.weather_agent.repository_url
}