from pathlib import Path
import json
import requests


# --------------------------------------------------
# Configuration
# --------------------------------------------------

API_URL = "http://127.0.0.1:8000"

IMAGE_PATH = Path(
    r"C:\Users\ARYAN\OneDrive\Desktop\AI\GEN-AI\SOVARA\data\test\Screenshot 2026-08-29 002329.png"
)

USER_QUERY = (
    "Explain the four stages of the engine cycle shown in the image "
    "and identify the key components involved in each stage."
)


# --------------------------------------------------
# Validate image
# --------------------------------------------------

if not IMAGE_PATH.exists():
    raise FileNotFoundError(
        f"Image not found:\n{IMAGE_PATH}"
    )


print("=" * 70)
print("SOVARA FULL VISION WORKFLOW TEST")
print("=" * 70)

print(f"\nImage : {IMAGE_PATH}")
print(f"Query : {USER_QUERY}")


# --------------------------------------------------
# Check API
# --------------------------------------------------

print("\nChecking SOVARA API...")

try:
    response = requests.get(
        f"{API_URL}/docs",
        timeout=10,
    )
    response.raise_for_status()

    print("✓ SOVARA API is reachable")

except requests.RequestException as exc:
    print("✗ Could not connect to SOVARA")
    print(exc)
    raise SystemExit(1)


# --------------------------------------------------
# Upload image + query
# --------------------------------------------------

print("\nSending request to SOVARA...")
print("Please wait. Qwen + Gemma may take some time.\n")


try:
    with open(IMAGE_PATH, "rb") as image_file:

        files = {
            "files": (
                IMAGE_PATH.name,
                image_file,
                "image/png",
            )
        }

        data = {
            "user_query": USER_QUERY,
        }

        response = requests.post(
            f"{API_URL}/analyze",
            files=files,
            data=data,
            timeout=300,
        )

except requests.RequestException as exc:
    print("✗ Request failed")
    print(exc)
    raise SystemExit(1)


# --------------------------------------------------
# Response
# --------------------------------------------------

print("=" * 70)
print(f"HTTP STATUS: {response.status_code}")
print("=" * 70)

if not response.ok:
    print("\nSOVARA returned an error:\n")
    print(response.text)
    raise SystemExit(1)


try:
    result = response.json()

except ValueError:
    print("\nResponse was not valid JSON:\n")
    print(response.text)
    raise SystemExit(1)


# --------------------------------------------------
# Save complete response
# --------------------------------------------------

output_path = Path("vision_workflow_result.json")

with open(
    output_path,
    "w",
    encoding="utf-8",
) as output_file:

    json.dump(
        result,
        output_file,
        indent=2,
        ensure_ascii=False,
    )


print("\n✓ Complete response saved to:")
print(output_path)


# --------------------------------------------------
# Display important sections
# --------------------------------------------------

print("\n" + "=" * 70)
print("FINAL ANSWER")
print("=" * 70)

print(
    result.get(
        "final_answer",
        "No final_answer field found."
    )
)


print("\n" + "=" * 70)
print("VISION RESULTS")
print("=" * 70)

print(
    json.dumps(
        result.get("evidence", []),
        indent=2,
        ensure_ascii=False,
    )
)


print("\n" + "=" * 70)
print("REASONING RESULTS")
print("=" * 70)

print(
    json.dumps(
        result.get("reasoning_results", []),
        indent=2,
        ensure_ascii=False,
    )
)


print("\n" + "=" * 70)
print("EXECUTION TRACE")
print("=" * 70)

trace = result.get("traceability", [])

for index, step in enumerate(trace, start=1):

    if isinstance(step, dict):
        node = step.get("node_name", "unknown")
        success = step.get("success", "?")

        print(
            f"{index:02d}. {node:<25} success={success}"
        )

    else:
        print(f"{index:02d}. {step}")


print("\n" + "=" * 70)
print("EXECUTION TELEMETRY")
print("=" * 70)

print(
    json.dumps(
        result.get("execution_telemetry", {}),
        indent=2,
        ensure_ascii=False,
    )
)


print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)