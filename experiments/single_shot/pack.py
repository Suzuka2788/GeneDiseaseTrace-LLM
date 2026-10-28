"""Build the single-shot prompt for one paper.

The fixed part (card + output format) is identical for every paper and is sent separately from the paper,
so a run of several papers can reuse it from the prompt cache.

Usage: python experiments/single_shot/pack.py PMC10487392
Writes runs/prompts/<paper>.txt (fixed part + paper, as one file for reading) and prints the sizes.
"""
import sys

from common import HERE, RUNS, load


def fixed_part():
    return "\n\n".join([(HERE / "card.md").read_text(encoding="utf-8"), (HERE / "format.md").read_text(encoding="utf-8")])


def paper_part(paper_id):
    article, kept, dropped, sentences = load(paper_id)
    lines = [f"# Paper {article['paper_id']} ({article['article_type']}): {article['title']}",
             "Each line starts with a sentence ID; table rows, titles and captions count as one sentence each. "
             "References and author-contribution, funding and conflict-of-interest sections are removed.", ""]
    by_block = {}
    for sid, (block_id, s, e) in sentences.items():
        by_block.setdefault(block_id, []).append((sid, s, e))
    for block in kept:
        lines.append(f"[{block['block_id']} | {block['content_type']} | {block['section']}]")
        for sid, s, e in by_block[block["block_id"]]:
            lines.append(f"{sid} {block['text'][s:e]}")
    lines += ["", "Now output the result in the output format."]
    return "\n".join(lines), dropped


def build_prompt(paper_id):
    """Fixed part and paper as one text, for CLIs without a separate system prompt."""
    paper, dropped = paper_part(paper_id)
    return fixed_part() + "\n\n" + paper, dropped


def main(paper_id):
    paper, dropped = paper_part(paper_id)
    fixed = fixed_part()
    out = RUNS / "prompts" / f"{paper_id}.txt"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(fixed + "\n\n" + paper, encoding="utf-8")
    print(f"{out}: fixed part {len(fixed)} characters, paper part {len(paper)} characters; dropped blocks: {dropped}")


if __name__ == "__main__":
    main(sys.argv[1])
