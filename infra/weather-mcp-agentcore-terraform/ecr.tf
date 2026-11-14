resource "aws_ecr_repository" "weather_mcp" {
  name                 = "${var.project_name}-${var.environment}"
  image_tag_mutability = "IMMUTABLE"
  image_scanning_configuration {
    scan_on_push = true
  }
  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "weather_mcp" {
  repository = aws_ecr_repository.weather_mcp.name
  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 tagged images"
      selection = {
        tagStatus      = "tagged"
        tagPatternList = ["v*"]
        countType      = "imageCountMoreThan"
        countNumber    = 3
      }
      action = { type = "expire" }
    }]
  })
}

resource "aws_ecr_repository" "weather_agent" {
  name                 = "${var.project_name}-${var.environment}-agent"
  image_tag_mutability = "IMMUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }
}

resource "aws_ecr_lifecycle_policy" "weather_agent" {
  repository = aws_ecr_repository.weather_agent.name

  policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Keep last 3 tagged images"
      selection = {
        tagStatus      = "tagged"
        tagPatternList = ["v*"]
        countType      = "imageCountMoreThan"
        countNumber    = 3
      }
      action = {
        type = "expire"
      }
    }]
  })
}