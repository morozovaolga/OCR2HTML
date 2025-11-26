import argparse
import re
from pathlib import Path
from typing import Iterable

from pymorphy2 import MorphAnalyzer

WORD_RE = re.compile(r"\b[\w']+\b", re.UNICODE)
DEFAULT_PRONOUNS = {"я", "ты", "он", "она", "оно", "мы", "вы", "они"}


def iter_words(text: str) -> Iterable[str]:
    return WORD_RE.findall(text)


def is_matching_pronoun(word: str, morph: MorphAnalyzer, pronouns: set[str]) -> bool:
    word_norm = word.lower()
    if word_norm in pronouns:
        return True
    for parse in morph.parse(word):
        if parse.tag.POS == "NPRO" and parse.normal_form in pronouns:
            return True
    return False


def has_verb_form(word: str, morph: MorphAnalyzer) -> bool:
    for parse in morph.parse(word):
        if parse.tag.POS in {"VERB", "INFN"}:
            return True
    return False


def analyze_text(text: str, pronouns: set[str], morph: MorphAnalyzer) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    warnings = []
    for sentence in sentences:
        tokens = list(iter_words(sentence))
        for idx in range(len(tokens) - 1):
            prev_word = tokens[idx]
            curr_word = tokens[idx + 1]
            if is_matching_pronoun(prev_word, morph, pronouns) and not has_verb_form(curr_word, morph):
                window_start = max(0, idx - 1)
                window_end = min(len(tokens), idx + 3)
                snippet = " ".join(tokens[window_start:window_end])
                warnings.append(
                    f"Пара {prev_word} + {curr_word} в предложении «{sentence.strip()}» ({snippet}) выглядит неправильно: {curr_word} не распознан как глагол."
                )
    return warnings


def main():
    parser = argparse.ArgumentParser(
        description="Контекстная проверка: ищет конструкции «местоимение + глагол» с неправильно распознанной формой."
    )
    parser.add_argument("--in", dest="inp", required=True, help="final_clean.txt для проверки контекста")
    parser.add_argument("--out", default="context_warnings.txt", help="Куда сохранять предупреждения")
    parser.add_argument(
        "--pronouns",
        default=",".join(sorted(DEFAULT_PRONOUNS)),
        help="Через запятую разделённый список местоимений (по умолчанию: %(default)s)",
    )
    args = parser.parse_args()

    pronouns = set(tok.strip().lower() for tok in args.pronouns.split(",") if tok.strip())

    text = Path(args.inp).read_text(encoding="utf-8", errors="ignore")
    morph = MorphAnalyzer()

    warnings = analyze_text(text, pronouns, morph)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if warnings:
        out_path.write_text("\n".join(warnings), encoding="utf-8")
        print(f"Найдено {len(warnings)} потенциальных контекстных ошибок, сохранено в {out_path}")
    else:
        out_path.write_text("Ошибок не найдено.\n", encoding="utf-8")
        print(f"Ошибок не найдено, создал пустой отчёт {out_path}")


if __name__ == "__main__":
    main()

