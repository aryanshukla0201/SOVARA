from app.tools.vision.image_analyzer import VisionAnalyzer


analyzer = VisionAnalyzer()

result = analyzer.analyze(
    image_path="C:\\Users\\ARYAN\\OneDrive\\Desktop\\AI\\GEN-AI\\SOVARA\\data\\test\\Screenshot 2026-08-29 002329.png",
    task_context=(
        "Analyze this image and explain the four-stroke "
        "engine cycle shown in the diagram."
    ),
)

print("\nVisionAnalyzer result:\n")
print(result)