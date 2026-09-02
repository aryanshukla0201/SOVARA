from app.core.config import get_settings


settings = get_settings()

print("MODEL PROVIDER:", settings.model_provider)
print("QWEN MODEL:", settings.qwen_model)
print("GEMMA MODEL:", settings.gemma_model)
print("OLLAMA URL:", settings.ollama_base_url)
print("UPLOAD DIRECTORY:", settings.upload_directory)
print("OUTPUT DIRECTORY:", settings.output_directory)
print("MAX REPAIR ATTEMPTS:", settings.max_repair_attempts)
