import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GITHUB_API_KEY")
base_url = "https://models.inference.ai.azure.com"

print(f"Testing GitHub API Key: {api_key[:10]}...")

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

try:
    response = client.chat.completions.create(
        messages=[
            {
                "role": "system",
                "content": "",
            },
            {
                "role": "user",
                "content": "What is the capital of France?",
            },
        ],
        model="gpt-4o",
        temperature=1,
        max_tokens=4096,
        top_p=1,
    )

    print("Response:")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Error calling GitHub Models: {e}")
