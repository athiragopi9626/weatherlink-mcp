import os
import json
import boto3
import httpx


def get_mcp_access_token() -> str:
    # Read Cognito credentials from Secrets Manager.
    client = boto3.client("secretsmanager")

    response = client.get_secret_value(
        SecretId=os.environ["COGNITO_SECRET_ARN"]
    )

    credentials = json.loads(response["SecretString"])

    # Request an OAuth2 access token from Cognito.
    token_response = httpx.post(
        credentials["COGNITO_TOKEN_URL"],
        data={
            "grant_type": "client_credentials",
            "scope": "weather-mcp/invoke",
        },
        auth=(
            credentials["COGNITO_CLIENT_ID"],
            credentials["COGNITO_CLIENT_SECRET"],
        ),
        timeout=15.0,
    )

    token_response.raise_for_status()

    return token_response.json()["access_token"]