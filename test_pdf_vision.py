from pathlib import Path
import json
import requests


# ============================================================
# CONFIGURATION
# ============================================================

API_URL = "http://127.0.0.1:8000"

PDF_PATH = Path(
    r"C:\Users\ARYAN\OneDrive\Desktop\AI\GEN-AI\SOVARA\data\uploads\file_2b915c3f_winninng ppt inspo .pdf"
)

IMAGE_PATH = Path(
    r"C:\Users\ARYAN\OneDrive\Desktop\AI\GEN-AI\SOVARA\data\test\Screenshot 2026-08-29 002329.png"
)

USER_QUERY = (
    "Analyze the information in the document together with the "
    "engine-cycle diagram. Explain what the document says about "
    "the relevant topic and use the image to explain the "
    "four-stroke engine cycle where relevant. Clearly distinguish "
    "information directly supported by the document from information "
    "supported by the image."
)


# ============================================================
# VALIDATION
# ============================================================

print("=" * 70)
print("SOVARA PDF + IMAGE CROSS-MODAL TEST")
print("=" * 70)

for path in [PDF_PATH, IMAGE_PATH]:

    if not path.exists():
        raise FileNotFoundError(
            f"\nFile not found:\n{path}"
        )

    print(f"\n✓ Found: {path.name}")


# ============================================================
# CHECK API
# ============================================================

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


# ============================================================
# SEND MULTIMODAL REQUEST
# ============================================================

print("\nSending PDF + image to SOVARA...")
print("This may take some time.\n")


try:

    with open(PDF_PATH, "rb") as pdf_file, \
         open(IMAGE_PATH, "rb") as image_file:

        files = [
            (
                "files",
                (
                    PDF_PATH.name,
                    pdf_file,
                    "application/pdf",
                ),
            ),
            (
                "files",
                (
                    IMAGE_PATH.name,
                    image_file,
                    "image/png",
                ),
            ),
        ]

        data = {
            "user_query": USER_QUERY,
        }

        response = requests.post(
            f"{API_URL}/analyze",
            files=files,
            data=data,
            timeout=600,
        )

except requests.RequestException as exc:

    print("✗ Request failed")
    print(exc)

    raise SystemExit(1)


# ============================================================
# BASIC RESPONSE CHECK
# ============================================================

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


# ============================================================
# SAVE COMPLETE RESPONSE
# ============================================================

output_path = Path(
    "pdf_vision_workflow_result.json"
)

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


print(
    f"\n✓ Complete response saved to:\n"
    f"{output_path}"
)


# ============================================================
# FINAL ANSWER
# ============================================================

print("\n" + "=" * 70)
print("FINAL ANSWER")
print("=" * 70)

print(
    result.get(
        "final_answer",
        "No final_answer returned.",
    )
)


# ============================================================
# EVIDENCE
# ============================================================

print("\n" + "=" * 70)
print("EVIDENCE")
print("=" * 70)

evidence = result.get(
    "evidence",
    [],
)

print(
    json.dumps(
        evidence,
        indent=2,
        ensure_ascii=False,
    )
)


# ============================================================
# TRACEABILITY
# ============================================================

print("\n" + "=" * 70)
print("TRACEABILITY")
print("=" * 70)

traceability = result.get(
    "traceability",
    [],
)

for index, step in enumerate(
    traceability,
    start=1,
):

    print(
        f"{index:02d}. "
        f"{step.get('node_name', 'unknown'):<25} "
        f"success={step.get('success', '?')}"
    )


# ============================================================
# TELEMETRY
# ============================================================

print("\n" + "=" * 70)
print("EXECUTION TELEMETRY")
print("=" * 70)

print(
    json.dumps(
        result.get(
            "execution_telemetry",
            {},
        ),
        indent=2,
        ensure_ascii=False,
    )
)


# ============================================================
# VERIFICATION
# ============================================================

print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

print(
    json.dumps(
        result.get(
            "verification_results",
            [],
        ),
        indent=2,
        ensure_ascii=False,
    )
)


# ============================================================
# DELIVERABLES
# ============================================================

print("\n" + "=" * 70)
print("GENERATED DELIVERABLES")
print("=" * 70)

print(
    json.dumps(
        result.get(
            "generated_deliverables",
            [],
        ),
        indent=2,
        ensure_ascii=False,
    )
)


print("\n" + "=" * 70)
print("TEST COMPLETE")
print("=" * 70)