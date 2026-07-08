import time

from google import genai

API_KEY_1 = ""git add test_api.py
API_KEY_2 = ""

MODEL = "gemini-2.5-flash"
PROMPT = "Say 'Hello' in one short sentence."


def test_api_key(name, api_key):
    print(f"\n===== Testing {name} =====")

    try:
        client = genai.Client(api_key=api_key)

        start = time.perf_counter()

        response = client.models.generate_content(
            model=MODEL,
            contents=PROMPT,
        )

        elapsed = time.perf_counter() - start

        print("✅ Success")
        print(f"Time: {elapsed:.2f} s")
        print("Response:")
        print(response.text)

    except Exception as e:
        print("❌ Failed")
        print(type(e).__name__)
        print(e)


if __name__ == "__main__":
    test_api_key("API KEY 1", API_KEY_1)
    test_api_key("API KEY 2", API_KEY_2)
