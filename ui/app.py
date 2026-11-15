
import json
import os
import uuid

import boto3
import streamlit as st

AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")
AGENT_ARN = os.environ["AGENT_RUNTIME_ARN"]

client = boto3.client("bedrock-agentcore", region_name=AWS_REGION)

st.set_page_config(
    page_title="Weather AI",
    page_icon="🌤️",
    layout="centered",
)

st.title("🌤️ Weather AI")
st.caption("Weather forecasts powered by AWS AgentCore")

if "messages" not in st.session_state:
    st.session_state.messages = []

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

prompt = st.chat_input("Ask about the weather...")

if prompt:
    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Checking the forecast..."):
            try:
                response = client.invoke_agent_runtime(
                    agentRuntimeArn=AGENT_ARN,
                    runtimeSessionId=st.session_state.session_id,
                    contentType="application/json",
                    accept="application/json",
                    payload=json.dumps(
                        {"prompt": prompt}
                    ).encode("utf-8"),
                )

                raw = response["response"].read()
                result = json.loads(raw)

                answer = result.get("final_answer")

                if not answer:
                    forecast = result.get("forecast", {})
                    risk = result.get("risk_level", "unknown")

                    answer = (
                        f"**Weather risk:** {risk}\n\n"
                        f"**Forecast:**\n\n"
                        f"```json\n"
                        f"{json.dumps(forecast, indent=2)}\n"
                        f"```"
                    )

                st.write(answer)

            except Exception as exc:
                answer = "Unable to retrieve the forecast."
                st.error(f"{answer} {exc}")

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )
