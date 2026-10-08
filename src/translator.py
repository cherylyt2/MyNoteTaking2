import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "translate_prompt.md"
TARGET_LANGUAGES = {
    "cantonese": "Cantonese, written in Traditional Chinese characters",
    "chinese": "Traditional Chinese",
    "english": "English",
    "japanese": "Japanese",
    "korean": "Korean",
}


def llm_generate(prompt: str, target_language: str) -> str:
    """Translate prompt into one of the supported target languages."""
    language = TARGET_LANGUAGES.get(target_language.strip().lower())
    if language is None:
        supported = ", ".join(TARGET_LANGUAGES.values())
        raise ValueError(f"Unsupported target language. Choose: {supported}.")

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing. Check your .env file.")

    system_prompt = PROMPT_PATH.read_text(encoding="utf-8").replace(
        "{{target_language}}", language
    )
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    for attempt in range(2):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            extra_body={"reasoning": {"enabled": True}},
        )
        choices = getattr(response, "choices", None)
        message = getattr(choices[0], "message", None) if choices else None
        translation = getattr(message, "content", None)
        if (
            isinstance(translation, str)
            and translation.strip()
            and "\ufffd" not in translation
        ):
            return translation.strip()

    raise RuntimeError(
        "Translation provider returned no valid translation after retry. Please try again."
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Translate text with OpenRouter.")
    parser.add_argument(
        "--target",
        required=True,
        choices=[language.title() for language in TARGET_LANGUAGES],
        help="Target language: Chinese, Cantonese, English, Japanese, or Korean.",
    )
    parser.add_argument("prompt", nargs="*", help="Text to translate.")
    args = parser.parse_args()

    prompt = " ".join(args.prompt).strip()
    if not prompt:
        prompt = input("Text to translate: ").strip()
    if not prompt:
        parser.error("a prompt is required")

    try:
        print(llm_generate(prompt, args.target))
    except Exception as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()