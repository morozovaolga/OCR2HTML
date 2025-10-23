import argparse
import ast
import json
import re
from pathlib import Path


def load_rules_from_py(file_path: Path):
    src = file_path.read_text(encoding="utf-8", errors="replace")
    tree = ast.parse(src, str(file_path))
    rules: list[tuple[str, str]] = []

    class V(ast.NodeVisitor):
        def visit_Assign(self, node: ast.Assign):
            val = node.value
            if not isinstance(val, ast.Call):
                return
            func = val.func
            is_resub = (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "re"
                and func.attr == "sub"
            )
            if not is_resub:
                return
            args = val.args
            if len(args) >= 3:
                pat, repl, sarg = args[0], args[1], args[2]
                if isinstance(pat, (ast.Str, ast.Constant)) and isinstance(repl, (ast.Str, ast.Constant)):
                    p = pat.s if isinstance(pat, ast.Str) else pat.value
                    r = repl.s if isinstance(repl, ast.Str) else repl.value
                    if isinstance(p, str) and isinstance(r, str):
                        rules.append((p, r))
            self.generic_visit(node)

    V().visit(tree)
    return rules


def main():
    ap = argparse.ArgumentParser(description="Apply oldspelling re.sub rules to structured blocks JSON.")
    ap.add_argument("--rules", default="oldspelling.py", help="Path to rules file")
    ap.add_argument("--in", dest="inp", default="output_vol2/structured.json", help="Structured JSON input")
    ap.add_argument("--out", default="output_vol2/structured_rules.json", help="Structured JSON output")
    args = ap.parse_args()

    rules = load_rules_from_py(Path(args.rules))
    data = json.loads(Path(args.inp).read_text(encoding="utf-8"))
    blocks = data.get("blocks", [])
    applied_total = 0

    for b in blocks:
        txt = b.get("text") or ""
        for pat, repl in rules:
            try:
                new_txt, n = re.subn(pat, repl, txt)
            except re.error:
                continue
            if n:
                applied_total += n
                txt = new_txt
        b["text"] = txt

    data["rules_applied"] = applied_total
    Path(args.out).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {args.out} (total replacements: {applied_total})")


if __name__ == "__main__":
    main()


