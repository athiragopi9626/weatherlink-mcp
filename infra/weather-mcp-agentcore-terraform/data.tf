
data "aws_secretsmanager_secret" "metoffice_warning" {
  name = "weather-mcp/metoffice-warning-api-key"
}
