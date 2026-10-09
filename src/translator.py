import argparse
import logging
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)

# MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
# MODEL = "google/gemma-4-26b-a4b-it:free"
MODEL = "nvidia/nemotron-3.5-lightning:free"
MAX_ATTEMPTS = 3
PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "translate_prompt.md"
TARGET_LANGUAGES = {
    # "cantonese": "Cantonese, written in Traditional Chinese characters",
    "chinese": "Traditional Chinese",
    "english": "English",
    "japanese": "Japanese",
    "korean": "Korean",
}
TARGET_LANGUAGE_INSTRUCTIONS = {
    "japanese": (
        "Write natural Japanese using hiragana and/or katakana where appropriate. "
        "Do not answer in Chinese."
    ),
    "korean": "Write natural Korean in Hangul. Do not answer in Chinese.",
}


def _has_expected_script(translation: str, target_language: str) -> bool:
    if target_language == "japanese":
        return any(
            "\u3041" <= character <= "\u3096"
            or "\u30a1" <= character <= "\u30fa"
            or "\u31f0" <= character <= "\u31ff"
            or "\uff66" <= character <= "\uff9d"
            for character in translation
        )
    if target_language == "korean":
        return any(
            "\uac00" <= character <= "\ud7a3"
            or "\u1100" <= character <= "\u11ff"
            or "\u3130" <= character <= "\u318f"
            for character in translation
        )
    return True


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
    ).replace(
        "{{language_instructions}}",
        TARGET_LANGUAGE_INSTRUCTIONS.get(
            target_language.strip().lower(),
            "Use the standard writing system for the target language.",
        ),
    )
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
    last_finish_reason = None
    for attempt in range(MAX_ATTEMPTS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": prompt},
            ],
            extra_body={"reasoning": {"enabled": False}},
        )
        choices = getattr(response, "choices", None)
        choice = choices[0] if choices else None
        last_finish_reason = getattr(choice, "finish_reason", None)
        message = getattr(choice, "message", None)
        translation = getattr(message, "content", None)
        if (
            isinstance(translation, str)
            and translation.strip()
            and "\ufffd" not in translation
            and _has_expected_script(
                translation.strip(),
                target_language.strip().lower(),
            )
        ):
            return translation.strip()

        logger.warning(
            "OpenRouter returned no valid translation on attempt %d/%d "
            "(finish_reason=%s)",
            attempt + 1,
            MAX_ATTEMPTS,
            last_finish_reason,
        )
        if attempt < MAX_ATTEMPTS - 1:
            time.sleep(0.5 * (2 ** attempt))

    raise RuntimeError(
        "Translation provider returned no valid translation after "
        f"{MAX_ATTEMPTS} attempts (last finish_reason={last_finish_reason}). "
        "Please try again."
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