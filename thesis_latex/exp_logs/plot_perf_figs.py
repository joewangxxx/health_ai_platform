import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt


def _load_metrics(path: Path) -> dict:
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def _save_dual(fig, out_base: Path) -> None:
    fig.tight_layout()
    fig.savefig(out_base.with_suffix('.png'), dpi=220, bbox_inches='tight')
    fig.savefig(out_base.with_suffix('.pdf'), bbox_inches='tight')
    plt.close(fig)


def plot_tps(metrics: dict, out_dir: Path) -> None:
    analyze = metrics["analyze"]
    iot = metrics["iot"]

    x_a = [item["concurrency"] for item in analyze]
    y_a = [item["tps"] for item in analyze]
    x_i = [item["concurrency"] for item in iot]
    y_i = [item["tps"] for item in iot]

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(x_a, y_a, marker='o', linewidth=2.0, label='/analyze/comprehensive')
    ax.plot(x_i, y_i, marker='s', linewidth=2.0, label='/api/v1/iot/sync/batch')

    ax.set_xlabel('Concurrency (users)')
    ax.set_ylabel('TPS (req/s)')
    ax.set_xticks(sorted(set(x_a + x_i)))
    ax.grid(True, linestyle='--', alpha=0.35)
    ax.legend(loc='best', frameon=False)

    _save_dual(fig, out_dir / 'fig_6_4_tps_concurrency')


def plot_p99(metrics: dict, out_dir: Path) -> None:
    analyze = metrics["analyze"]
    iot = metrics["iot"]

    x_a = [item["concurrency"] for item in analyze]
    y_a = [item["rt_p99_ms"] for item in analyze]
    x_i = [item["concurrency"] for item in iot]
    y_i = [item["rt_p99_ms"] for item in iot]

    fig, ax = plt.subplots(figsize=(6.8, 4.2))
    ax.plot(x_a, y_a, marker='o', linewidth=2.0, label='/analyze/comprehensive')
    ax.plot(x_i, y_i, marker='s', linewidth=2.0, label='/api/v1/iot/sync/batch')

    ax.set_xlabel('Concurrency (users)')
    ax.set_ylabel('P99 latency (ms)')
    ax.set_xticks(sorted(set(x_a + x_i)))
    ax.grid(True, linestyle='--', alpha=0.35)
    ax.legend(loc='best', frameon=False)

    _save_dual(fig, out_dir / 'fig_6_5_p99_concurrency')


def plot_cache_timeline(metrics: dict, out_dir: Path) -> None:
    chat_cache = metrics["chat_cache"]
    rt_cache = float(chat_cache["cache_rt_avg_ms"])
    rt_nocache = float(chat_cache["no_cache_rt_avg_ms"])

    phases = [
        'Warmup',
        'Steady',
        'Invalidate',
        'Recompute',
        'Recover',
        'Steady-2',
    ]
    x = list(range(len(phases)))

    hit_rate = [100.0, 100.0, 0.0, 0.0, 100.0, 100.0]
    latency = [rt_cache, rt_cache, rt_nocache, rt_nocache, rt_cache, rt_cache]

    fig, ax1 = plt.subplots(figsize=(7.2, 4.4))
    ax2 = ax1.twinx()

    l1 = ax1.plot(x, hit_rate, color='#1f77b4', marker='o', linewidth=2.0, label='Cache hit rate')
    l2 = ax2.plot(x, latency, color='#d62728', marker='s', linewidth=2.0, label='Avg latency')

    ax1.axvline(2, color='gray', linestyle='--', alpha=0.6)
    ax1.axvline(4, color='gray', linestyle='--', alpha=0.6)

    ax1.set_xlabel('State transition stage')
    ax1.set_ylabel('Hit rate (%)', color='#1f77b4')
    ax2.set_ylabel('Avg latency (ms)', color='#d62728')
    ax1.set_xticks(x)
    ax1.set_xticklabels(phases, rotation=20, ha='right')

    ax1.set_ylim(-5, 105)
    ax2.set_yscale('log')
    ax2.set_ylim(min(1.0, rt_cache * 0.6), rt_nocache * 1.4)

    lines = l1 + l2
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, loc='upper left', frameon=False)
    ax1.grid(True, linestyle='--', alpha=0.30)

    _save_dual(fig, out_dir / 'fig_6_6_cache_timeline')


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate Figure 6-4~6-6 from performance JSON metrics.')
    parser.add_argument('--input', type=Path, default=Path('thesis_latex/exp_logs/perf_metrics_20260315.json'))
    parser.add_argument('--output-dir', type=Path, default=Path('thesis_latex/images'))
    args = parser.parse_args()

    metrics = _load_metrics(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    plot_tps(metrics, args.output_dir)
    plot_p99(metrics, args.output_dir)
    plot_cache_timeline(metrics, args.output_dir)

    print('Generated figures:')
    for stem in ['fig_6_4_tps_concurrency', 'fig_6_5_p99_concurrency', 'fig_6_6_cache_timeline']:
        print(f' - {args.output_dir / (stem + ".png")}')
        print(f' - {args.output_dir / (stem + ".pdf")}')


if __name__ == '__main__':
    main()
