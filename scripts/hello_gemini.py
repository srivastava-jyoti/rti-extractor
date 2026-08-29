from google import genai

from rti_extractor.config import get_settings


def main() -> None:
    settings = get_settings()
    client = genai.Client(api_key=settings.gemini_api_key)

    print("Models this key can reach:\n")
    count = 0
    for model in client.models.list():
        actions = getattr(model, "supported_actions", None)
        usable = bool(actions) and "generateContent" in actions
        print(f"  {'usable' if usable else '      '}  {model.name}")
        count += 1

    print(f"\n{count} models listed.")
    print(f".env currently asks for: {settings.gemini_model!r}")


if __name__ == "__main__":
    main()
