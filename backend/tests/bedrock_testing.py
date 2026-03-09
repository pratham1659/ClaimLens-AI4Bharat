import boto3, json

client = boto3.client("bedrock-runtime", region_name="ap-south-1")

response = client.invoke_model(
    modelId="anthropic.claude-3-haiku-20240307-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": "hello"}],
        "max_tokens": 50
    })
)

print(response)