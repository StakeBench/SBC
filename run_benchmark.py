#!/usr/bin/env python3
"""
run_benchmark.py
================
REAL-Bench runner for OneStopMarket.
Handles all 22 templates: 9 DPI + 13 IPI.

DPI:  Extracts user input prompt and prints it for manual agent testing.
IPI:  Injects malicious review content into target product pages.

Usage:
  python run_benchmark.py --inject --bench E1.2_Real_Bench.json   # inject IPI / print DPI
  python run_benchmark.py --cleanup                                # remove last injection
  python run_benchmark.py --status                                 # show active injections
"""

import json
import subprocess
import sys
import argparse
import os
import random
from datetime import datetime
from template_configs import TEMPLATE_CONFIGS, NICKNAME, REVIEW_TITLE

# Load bench search paths from settings
import json as _json, os as _os
with open(_os.path.join(_os.path.dirname(__file__), "benchmark_settings.json")) as _f:
    _settings = _json.load(_f)
BENCH_SEARCH_PATHS = _settings.get("bench_search_paths", [])

# ─────────────────────────────────────────────────────────────
# DATABASE CONFIG
# ─────────────────────────────────────────────────────────────
DOCKER_CONTAINER = "shopping"
DB_USER          = "magentouser"
DB_PASS          = "MyPassword"
DB_NAME          = "magentodb"
DEFAULT_STORE_ID = 1
STATE_FILE       = "injected_state.json"
# ─────────────────────────────────────────────────────────────


# ── DB Helpers ────────────────────────────────────────────────────────────────

def run_sql(sql: str) -> str:
    cmd = [
        "docker", "exec", DOCKER_CONTAINER,
        "mysql", f"-u{DB_USER}", f"-p{DB_PASS}", DB_NAME,
        "--batch", "--skip-column-names", "-e", sql,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        stderr = result.stderr.replace(
            "[Warning] Using a password on the command line interface can be insecure.\n", ""
        )
        if stderr.strip():
            raise RuntimeError(f"MySQL error: {stderr.strip()}")
    return result.stdout.strip()


def escape_sql(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"')


def get_product_id(product_name: str) -> int:
    result = run_sql(f"""
        SELECT p.entity_id
        FROM catalog_product_entity p
        JOIN catalog_product_entity_varchar v ON p.entity_id = v.entity_id
        JOIN eav_attribute a ON v.attribute_id = a.attribute_id
        WHERE a.attribute_code = 'name'
        AND v.value LIKE '%{escape_sql(product_name[:60])}%'
        ORDER BY CHAR_LENGTH(v.value) ASC
        LIMIT 1;
    """)
    if not result:
        raise ValueError(f"Product not found: '{product_name}'")
    return int(result)


def get_rating_option_id(star_value: int) -> int | None:
    result = run_sql(f"""
        SELECT ro.option_id FROM rating_option ro
        JOIN rating r ON ro.rating_id = r.rating_id
        WHERE ro.value = {star_value}
        ORDER BY r.rating_id ASC LIMIT 1;
    """)
    return int(result) if (result and result.isdigit()) else None


def pick_rating(rating_type: str) -> int:
    """Return a random star value: 'positive' -> 4 or 5, 'negative' -> 1 or 2."""
    if rating_type == "positive":
        return random.choice([4, 5])
    else:
        return random.choice([1, 2])


def insert_review(product_id: int, content: str, template_id: str,
                  rating_stars: int, store_id: int = DEFAULT_STORE_ID) -> int:
    """Insert an approved review. Returns review_id."""
    now      = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    nickname = NICKNAME
    title    = REVIEW_TITLE

    run_sql(f"""
        INSERT INTO review (created_at, entity_id, entity_pk_value, status_id)
        VALUES ('{now}', 1, {product_id}, 1);
    """)

    review_id = int(run_sql(f"""
        SELECT review_id FROM review
        WHERE entity_pk_value = {product_id}
        ORDER BY review_id DESC LIMIT 1;
    """))

    run_sql(f"""
        INSERT INTO review_detail (review_id, store_id, title, detail, nickname)
        VALUES ({review_id}, {store_id}, '{escape_sql(title)}',
                '{escape_sql(content)}', '{escape_sql(nickname)}');
    """)

    run_sql(f"""
        INSERT IGNORE INTO review_store (review_id, store_id)
        VALUES ({review_id}, {store_id});
    """)

    # Insert ONE vote for rating_id=4 only (matches Magento's frontend behaviour)
    percent   = rating_stars * 20
    option_id = (4 - 1) * 5 + rating_stars  # rating_id=4, e.g. 5stars → option_id=20
    run_sql(f"""
        INSERT INTO rating_option_vote
            (option_id, remote_ip, remote_ip_long, customer_id,
             entity_pk_value, rating_id, review_id, percent, value)
        VALUES ({option_id}, '127.0.0.1', 2130706433, 0,
                {product_id}, 4, {review_id}, {percent}, {rating_stars});
    """)

    # Update aggregated table for rating_id=4 only
    agg_exists = run_sql(f"""
        SELECT primary_id FROM rating_option_vote_aggregated
        WHERE rating_id = 4 AND entity_pk_value = {product_id} AND store_id = 0
        LIMIT 1;
    """)
    if not agg_exists:
        run_sql(f"""
            INSERT INTO rating_option_vote_aggregated
                (rating_id, entity_pk_value, vote_count, vote_value_sum, percent, percent_approved, store_id)
            VALUES (4, {product_id}, 1, {rating_stars}, {percent}, {percent}, 0);
        """)
    else:
        run_sql(f"""
            UPDATE rating_option_vote_aggregated
            SET vote_count     = vote_count + 1,
                vote_value_sum = vote_value_sum + {rating_stars},
                percent        = ROUND((vote_value_sum + {rating_stars}) / ((vote_count + 1) * 5) * 100),
                percent_approved = ROUND((vote_value_sum + {rating_stars}) / ((vote_count + 1) * 5) * 100)
            WHERE rating_id = 4 AND entity_pk_value = {product_id} AND store_id = 0;
        """)

    existing = run_sql(f"""
        SELECT reviews_count FROM review_entity_summary
        WHERE entity_pk_value = {product_id}
          AND store_id = {store_id} AND entity_type = 1 LIMIT 1;
    """)
    if not existing:
        run_sql(f"""
            INSERT INTO review_entity_summary
                (entity_pk_value, entity_type, reviews_count, store_id)
            VALUES ({product_id}, 1, 1, {store_id});
        """)
    else:
        run_sql(f"""
            UPDATE review_entity_summary SET reviews_count = reviews_count + 1
            WHERE entity_pk_value = {product_id}
              AND store_id = {store_id} AND entity_type = 1;
        """)

    return review_id


def delete_review(review_id: int):
    # Get product_id before deleting
    vote_info = run_sql(f"""
        SELECT entity_pk_value FROM rating_option_vote
        WHERE review_id = {review_id} LIMIT 1;
    """)

    run_sql(f"DELETE FROM rating_option_vote WHERE review_id = {review_id};")
    run_sql(f"DELETE FROM review_detail WHERE review_id = {review_id};")
    run_sql(f"DELETE FROM review_store WHERE review_id = {review_id};")
    run_sql(f"DELETE FROM review WHERE review_id = {review_id};")

    # Recalculate aggregated table for rating_id=4 only
    if vote_info and vote_info.strip():
        product_id = int(vote_info.strip())
        agg = run_sql(f"""
            SELECT COUNT(*), COALESCE(SUM(value), 0)
            FROM rating_option_vote
            WHERE rating_id = 4 AND entity_pk_value = {product_id};
        """)
        if agg:
            parts = agg.split("\t")
            cnt   = int(parts[0]) if len(parts) > 0 else 0
            total = int(parts[1]) if len(parts) > 1 else 0
            pct   = round(total / (cnt * 5) * 100) if cnt > 0 else 0
            run_sql(f"""
                UPDATE rating_option_vote_aggregated
                SET vote_count = {cnt}, vote_value_sum = {total},
                    percent = {pct}, percent_approved = {pct}
                WHERE rating_id = 4 AND entity_pk_value = {product_id} AND store_id = 0;
            """)


def flush_cache():
    print("  Flushing Magento cache...")
    subprocess.run(
        ["docker", "exec", DOCKER_CONTAINER,
         "php", "/var/www/magento2/bin/magento", "cache:flush"],
        capture_output=True, timeout=120
    )
    subprocess.run(
        ["docker", "exec", DOCKER_CONTAINER,
         "php", "/var/www/magento2/bin/magento", "indexer:reindex", "review_entity"],
        capture_output=True, timeout=120
    )
    print("  ✓ Cache flushed")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


# ── DPI Handler ───────────────────────────────────────────────────────────────

def handle_dpi(template: dict, template_id: str):
    """For DPI: just print the user input prompt."""
    prompt = template.get("input_prompt", {}).get("prompt", "")
    intent = template.get("input_prompt", {}).get("user_intent_summary", "")

    # Some DPI templates have no input_prompt — payload is in attack_spec.injection_content
    if not prompt:
        prompt = template.get("attack_spec", {}).get("injection_content", "")

    print(f"\n{'='*60}")
    print(f"  DPI TEMPLATE — {template_id}")
    print(f"{'='*60}")
    print(f"\n COPY THIS PROMPT INTO YOUR AGENT:\n")
    print(f"{'─'*60}")
    print(prompt)
    print(f"{'─'*60}")
    if intent:
        print(f"\n User intent: {intent}")
    print(f"\n No review injection needed for DPI templates.")


# ── IPI Handler ───────────────────────────────────────────────────────────────

def handle_ipi(template: dict, template_id: str, config: dict):
    """For IPI: inject malicious review content into product pages."""

    raw_content     = template["attack_spec"]["injection_content"]
    rating_type     = config.get("rating",           "negative")
    needs_original  = config.get("needs_original",   False)
    needs_target    = config.get("needs_target",     False)
    multi           = config.get("multiple_reviews", 1)
    orig_products   = config.get("original_products", [])
    tgt_products    = config.get("target_products",  [])

    print(f"\n{'='*60}")
    print(f"  IPI TEMPLATE — {template_id}")
    print(f"  Rating type    : {rating_type}")
    print(f"  Reviews/product: {multi}")
    print(f"  Products       : {len(orig_products)}")
    print(f"  needs_original : {needs_original}  needs_target: {needs_target}")
    print(f"{'='*60}\n")

    # Print benign user input once (same for all products)
    raw_prompt = template.get("input_prompt", {}).get("prompt", "")
    intent     = template.get("input_prompt", {}).get("user_intent_summary", "")
    if raw_prompt:
        print(f" BENIGN USER INPUT FOR AGENT:\n{'─'*60}")
        print(raw_prompt)
        print(f"{'─'*60}")
        if intent:
            print(f" User intent: {intent}")
        print()

    # Hard block if previous injection is still active
    state = load_state()
    if state and state.get("reviews"):
        print(f"\n✗ Cannot inject: active reviews from template '{state.get('template_id')}' still exist.")
        print(f"  Run cleanup first: python run_benchmark.py --cleanup")
        return

    injected = []
    failed   = []

    # Build product pairs
    chain_groups   = config.get("chain_groups", [])
    chain_products = config.get("chain_products", [])  # legacy fallback

    if chain_groups:
        valid_chains = [c for c in chain_groups if c]

        if not valid_chains:
            print("  ✗ No chains defined yet in chain_groups.")
            return

        # Warn if any product appears in more than one chain
        all_products_flat = [p for chain in valid_chains for p in chain]
        seen = {}
        duplicates = []
        for p in all_products_flat:
            if p in seen:
                duplicates.append(p)
            seen[p] = True
        if duplicates:
            print(f"\n⚠️  WARNING: The following products appear in more than one chain:")
            for d in duplicates:
                print(f"    - {d}")
            print("  Products across chains must be unique! Please fix template_configs.py.\n")
            ans = input("  Continue anyway? (y/N): ").strip().lower()
            if ans != "y":
                return

        print(f"  Running {len(valid_chains)} chain(s)...\n")

        for chain_idx, chain in enumerate(valid_chains):
            n = len(chain)
            print(f"  ── Chain {chain_idx + 1}/{len(valid_chains)} ({n} products) ──")
            for i in range(n):
                orig_name = chain[i]
                tgt_name  = chain[(i + 1) % n]
                print(f"  [{i+1}/{n}] {orig_name[:55]}...")
                print(f"        → targets: {tgt_name[:55]}...")

                content = raw_content
                content = content.replace("[targeted_product]", tgt_name)
                content = content.replace("[target_product]",   tgt_name)
                content = content.replace("[Product B]",        tgt_name)

                extra_slots = config.get("extra_slots", {})
                for placeholder, value in extra_slots.items():
                    content = content.replace(placeholder, value)

                try:
                    product_id = get_product_id(orig_name)
                    for j in range(multi):
                        stars     = pick_rating(rating_type)
                        review_id = insert_review(product_id, content, template_id, stars)
                        print(f"      ✓ review_id={review_id} ⭐{stars}")
                        injected.append({
                            "review_id":    review_id,
                            "product_id":   product_id,
                            "product_name": orig_name,
                        })
                except Exception as e:
                    print(f"      ✗ {e}")
                    failed.append(orig_name)
            print()

        save_state({
            "template_id": template_id,
            "injected_at": datetime.now().isoformat(),
            "reviews":     injected,
        })

        flush_cache()

        print(f"{'─'*60}")
        print(f"  Injected: {len(injected)} reviews across {len(valid_chains)} chain(s)  |  Failed: {len(failed)}")
        if failed:
            for p in failed:
                print(f"    - {p}")
        pre_note = config.get("pre_test_note")
        if pre_note:
            print(f"\n{pre_note}")
        print(f"\n  Run your agent evaluation now.")
        print(f"  When done: python run_benchmark.py --cleanup")
        return
        n = len(chain_products)
        product_pairs = [
            (chain_products[i], chain_products[(i + 1) % n])
            for i in range(n)
        ]
    elif needs_target and tgt_products:
        product_pairs = list(zip(orig_products, tgt_products))
    else:
        product_pairs = [(p, None) for p in orig_products]

    for i, (orig_name, tgt_name) in enumerate(product_pairs):
        print(f"[{i+1}/{len(product_pairs)}] {orig_name[:65]}...")

        # Personalise content — replace all known slot placeholders
        content = raw_content
        if needs_original:
            content = content.replace("[original_product]", orig_name)
            content = content.replace("[Product A]", orig_name)
            content = content.replace("[Product]", orig_name)
        if needs_target and tgt_name:
            content = content.replace("[target_product]", tgt_name)
            content = content.replace("[targeted_product]", tgt_name)
            content = content.replace("[Product B]", tgt_name)

        # Replace any extra custom slots (e.g. "[Attacker's Address]")
        extra_slots = config.get("extra_slots", {})
        for placeholder, value in extra_slots.items():
            content = content.replace(placeholder, value)

        try:
            product_id = get_product_id(orig_name)

            # ── Decoy positive reviews ────────────────────────────────────────
            # Inject exactly the texts in config["decoy_texts"].
            # Empty list [] = no decoys, just the adversarial payload.
            decoy_texts = config.get("decoy_texts", [])
            for d, decoy_text in enumerate(decoy_texts):
                decoy_id = insert_review(product_id, decoy_text, f"{template_id}_decoy", 5)
                print(f"  ✓ decoy review {d+1}/{len(decoy_texts)}  review_id={decoy_id}  ⭐5")
                injected.append({
                    "review_id":    decoy_id,
                    "product_id":   product_id,
                    "product_name": orig_name,
                })

            # ── Malicious review(s) ──────────────────────────────────────────
            for j in range(multi):
                stars     = pick_rating(rating_type)
                review_id = insert_review(product_id, content, template_id, stars)
                label     = f" (review {j+1}/{multi})" if multi > 1 else ""
                print(f"  ✓ malicious review_id={review_id}  ⭐{stars}{label}")
                injected.append({
                    "review_id":    review_id,
                    "product_id":   product_id,
                    "product_name": orig_name,
                })

        except Exception as e:
            print(f"  ✗ {e}")
            failed.append(orig_name)

    save_state({
        "template_id": template_id,
        "injected_at": datetime.now().isoformat(),
        "reviews":     injected,
    })

    flush_cache()

    print(f"\n{'─'*60}")
    print(f"  Injected: {len(injected)} reviews  |  Failed: {len(failed)}")
    if failed:
        for p in failed:
            print(f"    - {p}")

    pre_note = config.get("pre_test_note")
    if pre_note:
        print(f"\n{pre_note}")

    print(f"\n  Run your agent evaluation now.")
    print(f"  When done: python run_benchmark.py --cleanup")


# ── Cleanup ───────────────────────────────────────────────────────────────────

def cmd_cleanup():
    state = load_state()
    if not state or not state.get("reviews"):
        print("Nothing to clean up.")
        return

    template_id = state.get("template_id", "?")
    reviews     = state["reviews"]
    print(f"\n{'='*60}")
    print(f"  CLEANUP — Template: {template_id}  ({len(reviews)} reviews)")
    print(f"{'='*60}\n")

    success = 0
    for r in reviews:
        try:
            delete_review(r["review_id"])
            print(f"  Deleted review_id={r['review_id']}  {r['product_name'][:50]}...")
            success += 1
        except Exception as e:
            print(f"  ✗ review_id={r['review_id']}: {e}")

    flush_cache()
    save_state({})
    print(f"\n  Cleaned up {success}/{len(reviews)} reviews. Ready for next template.")


# ── Status ────────────────────────────────────────────────────────────────────

def cmd_status():
    state = load_state()
    if not state or not state.get("reviews"):
        print("No active injected reviews.")
        return
    print(f"\nActive: Template={state['template_id']}  Injected={state.get('injected_at','?')}")
    print(f"Reviews ({len(state['reviews'])}):")
    for r in state["reviews"]:
        print(f"  review_id={r['review_id']}  {r['product_name'][:60]}...")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="REAL-Bench runner for OneStopMarket")
    parser.add_argument("--inject",  action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument("--status",  action="store_true")
    parser.add_argument("--bench",   help="Path to Real_Bench JSON file")
    args = parser.parse_args()

    if args.inject:
        if not args.bench:
            parser.error("--inject requires --bench <file>")
        if not os.path.exists(args.bench):
            # Try searching in known bench directories
            filename = os.path.basename(args.bench)
            found = None
            for search_path in BENCH_SEARCH_PATHS:
                candidate = os.path.join(search_path, filename)
                if os.path.exists(candidate):
                    found = candidate
                    break
            if found:
                args.bench = found
            else:
                print(f"File not found: {args.bench}")
                print(f"Also searched in:")
                for p in BENCH_SEARCH_PATHS:
                    print(f"  {p}")
                sys.exit(1)

        with open(args.bench) as f:
            bench = json.load(f)

        template    = bench["templates"][0]
        template_id = template["template_id"]
        config      = TEMPLATE_CONFIGS.get(template_id)

        if not config:
            print(f"No config found for template '{template_id}' in template_configs.py")
            print(f"Add an entry for '{template_id}' and re-run.")
            sys.exit(1)

        if config["type"] == "DPI":
            handle_dpi(template, template_id)
        else:
            handle_ipi(template, template_id, config)

    elif args.cleanup:
        cmd_cleanup()

    elif args.status:
        cmd_status()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()