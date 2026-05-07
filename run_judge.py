# run_judge_all.py

import argparse
import subprocess
from pathlib import Path


def find_templates(judge_dir: Path):
    return sorted(judge_dir.glob("*_Real_Bench.json"))


def template_id_from_path(path: Path):
    return path.name.replace("_Real_Bench.json", "")


def run_one(script_path, template_path, runs_path, out_path, model):
    cmd = [
        "python",
        str(script_path),
        "--template_path", str(template_path),
        "--runs_path", str(runs_path),
        "--out_path", str(out_path),
        "--model", model,
    ]

    print("\n" + "=" * 100)
    print("Running:")
    print(" ".join(cmd))
    print("=" * 100)

    subprocess.run(cmd, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--attack", choices=["DPI", "IPI", "all"], default="all")
    parser.add_argument("--agent", choices=["BrowserUse", "NanoBrowser", "all"], default="all") # you can change to your selected agent name file
    parser.add_argument("--model", default="gpt-5")
    parser.add_argument("--template_id", default=None, help="Run only one template, e.g., E1.1")
    args = parser.parse_args()

    root = Path(args.root)

    attacks = ["DPI", "IPI"] if args.attack == "all" else [args.attack]
    agents = ["BrowserUse", "NanoBrowser"] if args.agent == "all" else [args.agent]

    for attack in attacks:
        attack_dir = root / f"{attack}_attack"

        judge_dir = attack_dir / ("LLM_Judge" if attack == "DPI" else "LLM_judge")
        script_path = judge_dir / (f"{attack}_judge.py")

        output_root = attack_dir / "Judge_Output"
        output_root.mkdir(exist_ok=True)

        templates = find_templates(judge_dir)


        for template_path in templates:
            tid = template_id_from_path(template_path)

            if args.template_id is not None and tid != args.template_id:
                continue

            for agent in agents:
                runs_path = attack_dir / "Agent_Execution_log" / agent / f"{tid}_log.jsonl"

                if not runs_path.exists():
                    print(f"[SKIP] Missing runs: {runs_path}")
                    continue

                out_dir = output_root / agent
                out_dir.mkdir(parents=True, exist_ok=True)

                out_path = out_dir / f"{tid}_judged_result.jsonl"

                run_one(
                    script_path=script_path,
                    template_path=template_path,
                    runs_path=runs_path,
                    out_path=out_path,
                    model=args.model,
                )


if __name__ == "__main__":
    main()