"""Find every occurrence of a name or phrase in the parsed paper, with block ID, offsets and context.

Usage: python -m toolkit.find TEXT [--ignore-case] [--regex] [--whole-word]
Use it to check that a surface form or quote exists exactly as you will write it in judgments.json.
"""
import argparse
import re

from .common import load_article


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("text")
    parser.add_argument("--ignore-case", action="store_true")
    parser.add_argument("--regex", action="store_true")
    parser.add_argument("--whole-word", action="store_true")
    args = parser.parse_args()
    pattern = args.text if args.regex else re.escape(args.text)
    if args.whole_word:
        pattern = rf"(?<!\w){pattern}(?!\w)"
    regex = re.compile(pattern, re.I if args.ignore_case else 0)
    _, article, _ = load_article()
    hits = 0
    for block in article["blocks"]:
        for match in regex.finditer(block["text"]):
            hits += 1
            text = block["text"]
            context = text[max(0, match.start() - 60):match.end() + 60].replace("\n", " ")
            print(f"{block['block_id']} [{match.start()}:{match.end()}] {block['content_type']} | ...{context}...")
    print(f"{hits} match(es)")


if __name__ == "__main__":
    main()
