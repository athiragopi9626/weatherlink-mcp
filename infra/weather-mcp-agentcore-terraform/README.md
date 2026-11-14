# Weather MCP server — AgentCore Runtime (Terraform)

AWS services are split across `ecr.tf`, `cognito.tf`, `iam.tf`, and `agentcore.tf`. All inputs are declared in `variables.tf`.

## Prerequisites

- AWS account credentials with permissions to create Cognito, ECR, IAM, AgentCore resources.
- Terraform >= 1.6 and AWS provider >= 6.24.
- Docker buildx capable of building `linux/arm64` images.
- Existing MCP server adapted to bind `0.0.0.0:8000/mcp`, using Streamable HTTP, and stateless mode for applicable MCP versions.
- Verify AWS service availability in your selected Region.

## Step 1: Bootstrap infrastructure (without runtime)

```bash
cp terraform.tfvars.example terraform.tfvars
# Edit unique Cognito domain prefix and region
terraform init
terraform fmt -recursive
terraform validate
terraform plan -out=bootstrap.tfplan
terraform apply bootstrap.tfplan
```

## Step 2: Build and push your application image

Create a Dockerfile for your EXISTING server code (this package does not invent a replacement weather server). The image must be ARM64 and expose port 8000. Confirm the app serves `/mcp` and handles `GET /ping` if you implement the recommended health endpoint.

```bash
REGION=eu-west-1 # Change to match aws_region in terraform.tfvars
REPO=$(terraform output -raw ecr_repository_url)
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
aws ecr get-login-password --region "$REGION" | docker login --username AWS --password-stdin "${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
docker buildx build --platform linux/arm64 -t "${REPO}:v1" --push PATH_TO_YOUR_MCP_APP
```

Replace PATH_TO_YOUR_MCP_APP with the directory containing your Dockerfile and server files. The image tag must match `image_tag` in tfvars. `REGION` must match `aws_region` in tfvars.

## Step 3: Create AgentCore Runtime

Set `deploy_runtime = true` in `terraform.tfvars`, then:

```bash
terraform plan -out=runtime.tfplan
terraform apply runtime.tfplan
```

## Step 4: Configure client and test

Use the Cognito token endpoint, client ID and `weather-mcp/invoke` scope. Obtain the client secret securely (see security notes) and request an OAuth client_credentials access token. Invoke AgentCore's HTTPS runtime invocation endpoint with `Authorization: Bearer TOKEN` and a Streamable HTTP MCP client.

## Security notes / important limits

- Cognito app-client secret is held in Terraform state. Store state in a secured encrypted remote backend with tightly restricted access; do not output the secret or commit state files.
- This Terraform does NOT provision the actual Met Office API key. If supplied, `metoffice_secret_arn` grants GetSecretValue and passes its ARN, not the key. Adapt your Python app to fetch the secret; for customer-managed KMS keys add a narrowly scoped kms:Decrypt permission.
- `network_mode = "PUBLIC"` is needed for outbound public weather API access in this design; it does not bypass AgentCore's JWT inbound authorizer. Review outbound restrictions before production.
- AgentCore inbound JWT checks client and scope; implement per-tool authorization in the server if different tools require different permissions.
- CloudWatch service log delivery, tracing, alerts, CI/CD image publishing, and backend configuration are not yet provisioned.
- Do not run Terraform with `deploy_runtime=true` until the image exists in ECR.
- The project is a deployable Terraform starting point, not an executed AWS deployment. Validate against your actual account/Region before applying.

## References

- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-mcp-protocol-contract.html
- https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/runtime-permissions.html
- https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/bedrockagentcore_agent_runtime
