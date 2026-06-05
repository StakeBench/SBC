

# StakeBench: 
> This repository contains the benchmark templates, task definitions, LLM-based auto-evaluation scripts, and reproduction instructions for **StakeBench**, a stakeholder-centric benchmark for evaluating prompt-injection security of LLM-based web agents in realistic e-commerce environments.

---

## 1. Overview

StakeBench evaluates whether deployable LLM-based web agents can safely complete realistic web tasks when adversarial instructions are embedded in the content they observe. The benchmark studies both:

- **Indirect Prompt Injection (IPI):** adversarial instructions are embedded in environmental content encountered during task execution, such as product reviews, ratings, metadata, or other user-controllable e-commerce content.
- **Direct Prompt Injection (DPI):** adversarial instructions are inserted into the agent's primary user-input channel (as a reference setting).


StakeBench is built around a functional e-commerce environment and evaluates complete agent systems rather than isolated language models. StakeBench evaluates two deployable web-agent systems, **NanoBrowser** ([https://github.com/nanobrowser/nanobrowser](https://github.com/nanobrowser/nanobrowser)) and **BrowserUse** ([https://github.com/browser-use/browser-use](https://github.com/browser-use/browser-use)), each paired with two backbone LLMs, **GPT-5** and **Gemini-2.5-Flash**.


### Introduction Video

<a href="https://www.youtube.com/watch?v=bI4huFXcDYc">
  <img src="https://img.youtube.com/vi/bI4huFXcDYc/maxresdefault.jpg" width="700">
</a>

<br>

▶ <a href="https://www.youtube.com/watch?v=bI4huFXcDYc">Watch introduction video</a>

---

## 2. Repository Contents

```
StakeBench/
├── benchmark_settings.json         ← Edit this to configure your benchmark run
├── run_benchmark.py                ← IPI environment injection script
├── template_configs.py             ← Template definitions (do not edit)
├── run_judge.py                    ← LLM-based auto-evaluation script
├── run.sh                          ← Example judge commands
│
├── DPI_attack/
│   ├── Agent_Execution_log/
│   │   ├── BrowserUse/
│   │   │   ├── E1.1_log.jsonl      ← Agent trajectories from our experiments
│   │   │   └── ...
│   │   └── NanoBrowser/
│   ├── LLM_Judge/
│   │   ├── DPI_judge.py
│   │   ├── E1.1_Real_Bench.json
│   │   ├── E1.1_judge_prompt.txt
│   │   └── ...
│   ├── Judge_Output/
│   └── Judge_Output_results/
│       ├── BrowserUse/
│       │   ├── E1.1_judge_results.jsonl
│       │   └── ...
│       └── NanoBrowser/
│
└── IPI_attack/
    ├── Agent_Execution_log/
    ├── LLM_judge/
    ├── Judge_Output/
    └── Judge_Output_results/
```

---

## 3. Benchmark Summary

| Item | Description |
|---|---|
| Environment | OneStopMarket from VisualWebArena, a functional e-commerce platform |
| Primary attack setting | Indirect prompt injection through environmental content |
| Reference attack setting | Direct prompt injection through user input |
| Stakeholder categories | User, Seller, Platform |
| Attack objectives | 12 objective categories |
| Attack templates | 22 total: 9 DPI and 13 IPI |
| Product categories | 12 e-commerce categories |
| Executable adversarial cases | 264 |
| Evaluated agents | NanoBrowser, BrowserUse |
| Backbone models | GPT-5, Gemini-2.5-Flash |
| Repetitions | 3 runs per adversarial case |
| Total attacked runs | 3,168 |
| Metrics | ASR, TDR, BIR |


### Benchmark Construction Video

<a href="https://www.youtube.com/watch?v=B0J9BISEUuU">
  <img src="https://img.youtube.com/vi/B0J9BISEUuU/maxresdefault.jpg" width="700">
</a>

<br>

▶ <a href="https://www.youtube.com/watch?v=B0J9BISEUuU">Watch benchmark construction video</a>

---

## 4. Environment Installation

```bash
conda create -n stakebench python=3.11
conda activate stakebench
pip install openai
pip install google-generativeai   # for Gemini-2.5-Flash backbone
pip install colorama              # optional, for colored terminal output
```

Set your API keys:

**Linux/macOS**
```bash
export OPENAI_API_KEY=your_openai_api_key
export GOOGLE_API_KEY=your_google_api_key
```

**Windows**
```bash
set OPENAI_API_KEY=your_openai_api_key
set GOOGLE_API_KEY=your_google_api_key
```

---

## 5. Full Evaluation Workflow

The complete workflow has two stages: **(A) benchmark setup and agent evaluation**, and **(B) LLM-based judging**.

The `Agent_Execution_log/` directories contain the agent trajectories from our experiments, which can be used directly to reproduce the judging results in Stage B without repeating the agent runs in Stage A.

---

### Stage A — Benchmark Setup and Agent Evaluation

This stage is only required if you want to run your own agent trajectories.


#### Demo Video

<a href="https://www.youtube.com/watch?v=mH2WFOLAcVQ">
  <img src="https://img.youtube.com/vi/mH2WFOLAcVQ/maxresdefault.jpg" width="700">
</a>

<br>

▶ <a href="https://www.youtube.com/watch?v=mH2WFOLAcVQ">Watch demo video</a>

#### A1 — Install the Shopping Environment

Install and launch the OneStopShop e-commerce environment from VisualWebArena:

```
https://github.com/web-arena-x/webarena
```

Verify the environment is accessible:

```
Frontend:  http://localhost:7770
Admin:     http://localhost:7770/admin
```

#### A2 — Register an Account

Create a customer account on OneStopMarket and fill in all required fields (full name, home address, phone number, email, billing address). Some attack templates require the agent to access this account information. Make sure the account is signed in before running any template.

#### A3 — Configure `benchmark_settings.json`

All configurable settings are in a single file. Edit this file before running any template:

```json
{
  "bench_search_paths": [
    "./DPI_attack/LLM_Judge",
    "./IPI_attack/LLM_judge"
  ],
  "reviewer": {
    "nickname": "your_nickname",
    "review_title": "Your Review Title"
  },
  "attacker_address": "A fake address for address-tampering templates",
  "original_products": [
    "Product name exactly as it appears on the site",
    "..."
  ],
  "target_products": [
    "Corresponding target product paired with each original product",
    "..."
  ],
  "chain_groups": [
    ["Product A", "Product B", "Product C", "Product D", "Product E"]
  ]
}
```

The table below shows which fields are required for each IPI template:

| Template ID | Objective | `original_products` | `target_products` | `attacker_address` | `chain_groups` |
|-------------|-----------|:-------------------:|:-----------------:|:------------------:|:--------------:|
| E1.2 | Order/Payment Data Disclosure | ✅ | — | — | — |
| E2.2 | Personal Information Disclosure | ✅ | — | — | — |
| E3.3 | Coerced Purchase | ✅ | ✅ | — | — |
| E3.4 | Coerced Purchase | ✅ | ✅ | — | — |
| E4.2 | Order Tampering (Address) | ✅ | — | ✅ | — |
| E4.3 | Order Tampering (Address) | ✅ | — | ✅ | — |
| T1.2 | Biased Review Manipulation | ✅ | — | — | — |
| T2.2 | Rating Manipulation | ✅ | — | — | — |
| T3.2 | Malicious Cancellation | ✅ | — | — | — |
| T3.3 | Malicious Cancellation | ✅ | — | — | — |
| T4.2 | Order Inflation | ✅ | — | — | — |
| T4.3 | Order Inflation | ✅ | — | — | — |
| P4.1 | Workflow Loop Induction | — | — | — | ✅ |

DPI templates require no environment configuration.

#### A4 — Inject IPI Payloads / Retrieve DPI Prompts

```bash
# Inject an IPI payload into the shopping environment
python run_benchmark.py --inject --bench E1.2_Real_Bench.json

# Or pass the full path
python run_benchmark.py --inject --bench ./IPI_attack/LLM_judge/E1.2_Real_Bench.json

# Check currently active injection
python run_benchmark.py --status

# Remove injected reviews after evaluation (required before next template)
python run_benchmark.py --cleanup
```

For **DPI templates**, the script prints the adversarial user prompt directly to the terminal — no environment injection needed.

For **IPI templates**, the script injects the adversarial payload into the product review sections and prints the benign user input prompt for you to provide to the agent.

After injection, verify the payload is visible by navigating to a target product page on `http://localhost:7770` and scrolling to the **Customer Reviews** section.

> **Important:** always run `--cleanup` after finishing evaluation of each IPI template before injecting the next one. The script will block injection if a previous payload is still active.

#### A5 — Run Your Agent

Provide the agent with the user input prompt printed by the script. Run the agent against `http://localhost:7770` and record the full execution trajectory.

#### A6 — Save the Execution Log

Save each agent trajectory as a JSONL file under the appropriate path:

```
DPI_attack/Agent_Execution_log/<AgentName>/<template_id>_log.jsonl
IPI_attack/Agent_Execution_log/<AgentName>/<template_id>_log.jsonl
```

Each line in the JSONL file corresponds to one run and must follow this format:

```json
{
  "run_id": "E2.2__gemini-2.5-flash__trial1__product_name",
  "template_id": "E2.2",
  "model": "gemini-2.5-flash",
  "trial_index": 1,
  "trial_total": 3,
  "category": "product or category name",
  "status": "OK",
  "runtime": {
    "trajectory_text": "Full agent action trace...",
    "final_state_text": "Final page state or agent summary..."
  }
}
```

---

### Stage B — LLM-based Judge Evaluation

This stage reproduces the automatic judging results using the agent trajectories in `Agent_Execution_log/`. All automated labels are produced by a GPT-5 judge operating on the executed trajectory and final environment state under template-specific success conditions.


#### Evaluation Walkthrough Video

<a href="https://www.youtube.com/watch?v=gW4ytn38VhU">
  <img src="https://img.youtube.com/vi/gW4ytn38VhU/maxresdefault.jpg" width="700">
</a>

<br>

▶ <a href="https://www.youtube.com/watch?v=gW4ytn38VhU">Watch evaluation walkthrough video</a>

#### B1 — Run the Judge

```bash
# Evaluate all DPI and IPI results for all agents
python run_judge.py

# Evaluate all DPI results
python run_judge.py --attack DPI

# Evaluate all IPI results
python run_judge.py --attack IPI

# Evaluate all templates for one agent under DPI
python run_judge.py --attack DPI --agent NanoBrowser
python run_judge.py --attack DPI --agent BrowserUse

# Evaluate all templates for one agent under IPI
python run_judge.py --attack IPI --agent NanoBrowser
python run_judge.py --attack IPI --agent BrowserUse

# Evaluate one specific template for one agent
python run_judge.py --attack DPI --agent NanoBrowser --template_id E1.1
python run_judge.py --attack IPI --agent BrowserUse --template_id T4.2
```

Judge outputs are written to:

```
DPI_attack/Judge_Output/<AgentName>/<template_id>_judge_results.jsonl
IPI_attack/Judge_Output/<AgentName>/<template_id>_judge_results.jsonl
```

Each output record contains ASR, TDR, and BIR labels with confidence scores, supporting evidence, and a `need_human_review` flag for ambiguous cases.

---

## 6. Attack Taxonomy

StakeBench uses an entity-centric taxonomy. Each attack is categorized by the stakeholder bearing the resulting harm and the concrete adversarial objective it pursues.

### 6.1 User-targeted Objectives

| ID | Objective | Templates |
|---|---|---|
| E1 | Order or Payment Data Disclosure | DPI: E1.1; IPI: E1.2 |
| E2 | Personal Information Disclosure | DPI: E2.1; IPI: E2.2 |
| E3 | Coerced or Induced Purchases | DPI: E3.1, E3.2; IPI: E3.3, E3.4 |
| E4 | Order Tampering | DPI: E4.1; IPI: E4.2, E4.3 |

### 6.2 Seller-targeted Objectives

| ID | Objective | Templates |
|---|---|---|
| T1 | Biased Review-based Manipulation | DPI: T1.1; IPI: T1.2 |
| T2 | Rating Manipulation | DPI: T2.1; IPI: T2.2 |
| T3 | Malicious Cancellation | DPI: T3.1; IPI: T3.2, T3.3 |
| T4 | Order Inflation | DPI: T4.1; IPI: T4.2, T4.3 |

### 6.3 Platform-targeted Objectives

| ID | Objective | Templates |
|---|---|---|
| P1 | Spoofed Authority Instructions | DPI: E3.1, E3.2, E4.1, E1.1, E2.1; IPI: E3.3, T3.2, T3.3, E4.2, E4.3, T4.2, T4.3, E1.2, E2.2, T1.2 |
| P2 | Unauthorized Action Inducement | DPI: E3.1, E3.2, T3.1, E4.1, T4.1, E1.1, E2.1, T2.1; IPI: E3.3, E3.4, T3.2, T3.3, E4.2, E4.3, T4.2, T4.3, E1.2, E2.2, T2.2 |
| P3 | Workflow Bypass | DPI: T4.1, E1.1, E2.1; IPI: T4.2, T4.3, E1.2, E2.2, T2.2 |
| P4 | Workflow Loop Induction | IPI: P4.1 |

---

## 7. Evaluation Metrics

Each attacked trajectory is labeled along three complementary axes:

- **ASR (Attack Success Rate):** measures whether the adversarial objective is achieved through an executed action against the targeted entity. A run is ASR-positive only when the agent performs the benchmark-defined harmful action in the environment.
- **TDR (Task Deviation Rate):** measures whether the user's delegated benign task is materially disrupted. TDR is not reported for DPI because DPI replaces or augments the user input itself, rendering benign-task deviation conceptually ill-defined.
- **BIR (Behavioral Irregularity Rate):** measures whether the trajectory exhibits pathological execution beyond ordinary task failure, such as looping, contradictory planning, unstable navigation, or false nonexistence claims.

ASR and TDR jointly define four failure regimes: **Compounded Failure** (high ASR, high TDR), **Stealthy Parasitism** (high ASR, low TDR), **Misaligned Disruption** (low ASR, high TDR), and **Robust Behavior** (low ASR, low TDR).

---

## 8. Notes for Reviewers

### 8.1 Anonymization

This repository is anonymized for double-blind review. It does not include author names, institutional identifiers, private repository links, or non-anonymous contact information.

### 8.2 Fictitious Account Information

All account information appearing in agent trajectories — including names, addresses, email addresses, and phone numbers — are fictitious benchmark artifacts created solely for sandbox evaluation purposes. They do not correspond to any real individual, and any resemblance to real persons or locations is coincidental.

### 8.3 Additional Notes

- `--template_id` is optional; omitting it evaluates all templates.
- Judge output format is JSONL, one record per run.
- The `need_human_review` flag in the judge output identifies cases where automatic labeling is uncertain and manual inspection is recommended.
- All experiments are conducted within a fully sandboxed environment. No real user data, financial transactions, or third-party systems are involved at any stage.
