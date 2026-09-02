from app.models.model_factory import ModelFactory


def main():
    model = ModelFactory.create("qwen")

    print("Model adapter:", model.name)
    print("Testing model...\n")

    response = model.generate(
        "Explain the difference between deterministic analysis and LLM reasoning in three concise bullet points."
    )

    print("RESPONSE:")
    print(response)


if __name__ == "__main__":
    main()