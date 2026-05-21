from dataclasses import dataclass


@dataclass(frozen=True)
class LanguageProfile:
    code: str
    display_name: str
    english_name: str
    aliases: tuple[str, ...]
    translation_notes: tuple[str, ...]


SUPPORTED_PROFILES = (
    LanguageProfile(
        code="en",
        display_name="Inglés",
        english_name="English",
        aliases=("en", "eng", "en-us", "en-gb", "english", "inglés", "ingles"),
        translation_notes=("Preserve the existing English workflow and translation maps.",),
    ),
    LanguageProfile(
        code="zh-cmn",
        display_name="Chino mandarín",
        english_name="Mandarin Chinese",
        aliases=("zh", "zho", "chi", "cmn", "zh-cmn", "zh-cn", "zh-hans", "zh-hant", "mandarin", "mandarin chinese", "chinese", "chino", "chino mandarín", "chino mandarin", "中文", "普通话", "國語", "国语"),
        translation_notes=("Resolve implied subjects naturally in Spanish LatAm.",),
    ),
    LanguageProfile(
        code="hi",
        display_name="Hindi",
        english_name="Hindi",
        aliases=("hi", "hin", "hindi", "हिन्दी", "हिंदी"),
        translation_notes=("Preserve respectful tone and avoid overly literal postpositions.",),
    ),
    LanguageProfile(
        code="pt",
        display_name="Portugués",
        english_name="Portuguese",
        aliases=("pt", "por", "pt-br", "pt-pt", "portuguese", "portugués", "portugues", "português", "brazilian portuguese"),
        translation_notes=("Prefer neutral LatAm phrasing, not calques from Portuguese.",),
    ),
    LanguageProfile(
        code="fr",
        display_name="Francés",
        english_name="French",
        aliases=("fr", "fra", "fre", "french", "francés", "frances", "français", "francais"),
        translation_notes=("Avoid literal French syntax; preserve politeness naturally.",),
    ),
    LanguageProfile(
        code="ru",
        display_name="Ruso",
        english_name="Russian",
        aliases=("ru", "rus", "russian", "ruso", "русский"),
        translation_notes=("Restore omitted pronouns only when Spanish needs them.",),
    ),
    LanguageProfile(
        code="de",
        display_name="Alemán",
        english_name="German",
        aliases=("de", "deu", "ger", "german", "deutsch", "alemán", "aleman"),
        translation_notes=("Split long German structures into readable Spanish subtitle lines.",),
    ),
    LanguageProfile(
        code="ja",
        display_name="Japonés",
        english_name="Japanese",
        aliases=("ja", "jpn", "japanese", "japonés", "japones", "日本語", "nihongo"),
        translation_notes=("Preserve names and honorifics when useful for fandom context.",),
    ),
    LanguageProfile(
        code="wuu",
        display_name="Chino Wu (Shanghainés)",
        english_name="Wu Chinese / Shanghainese",
        aliases=("wuu", "zh-wuu", "wu", "wu chinese", "shanghainese", "shanghai", "shanghainés", "shanghaines", "chino wu", "吴语", "吳語", "上海话"),
        translation_notes=("Treat as distinct from Mandarin when metadata explicitly says Wu/Shanghainese.",),
    ),
    LanguageProfile(
        code="ko",
        display_name="Coreano",
        english_name="Korean",
        aliases=("ko", "kor", "korean", "coreano", "한국어", "조선말"),
        translation_notes=("Reflect speech level politely without over-formalizing Spanish.",),
    ),
    LanguageProfile(
        code="it",
        display_name="Italiano",
        english_name="Italian",
        aliases=("it", "ita", "italian", "italiano"),
        translation_notes=("Avoid Italian word-order calques in Spanish.",),
    ),
)


PROFILE_BY_CODE = {profile.code: profile for profile in SUPPORTED_PROFILES}
ALIAS_TO_CODE = {
    alias.casefold(): profile.code
    for profile in SUPPORTED_PROFILES
    for alias in profile.aliases
}
SUPPORTED_LANGUAGE_CODES = tuple(profile.code for profile in SUPPORTED_PROFILES)
SUPPORTED_LANGUAGE_NAMES = tuple(profile.display_name for profile in SUPPORTED_PROFILES)


class UnsupportedLanguageError(ValueError):
    def __init__(self, language: str):
        self.language = language
        available = ", ".join(SUPPORTED_LANGUAGE_NAMES)
        super().__init__(
            f"Idioma no soportado: {language}. Idiomas disponibles: {available}."
        )


def normalize_language_code(language: str) -> str:
    if not language:
        raise UnsupportedLanguageError("<sin metadata>")
    key = language.strip().casefold()
    if key in ALIAS_TO_CODE:
        return ALIAS_TO_CODE[key]
    if "-" in key:
        base_key = key.split("-", 1)[0]
        if base_key in ALIAS_TO_CODE:
            return ALIAS_TO_CODE[base_key]
    raise UnsupportedLanguageError(language)


def get_language_profile(language: str) -> LanguageProfile:
    return PROFILE_BY_CODE[normalize_language_code(language)]
