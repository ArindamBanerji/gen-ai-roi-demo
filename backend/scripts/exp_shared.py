"""
V-CENTROID-VALUE-SUITE: Shared utilities
========================================
All 7 experiments import from this file.
Place in backend/scripts/ alongside the experiment files.
"""

import sys
import os
import numpy as np
from collections import Counter

# Path setup
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, BACKEND_DIR)

GAE_DIR = os.environ.get(
    "CLAUDE_GAE",
    os.path.join(os.path.dirname(os.path.dirname(BACKEND_DIR)), "graph-attention-engine-v50")
)
sys.path.insert(0, GAE_DIR)

from gae.profile_scorer import ProfileScorer
from app.domains.soc.config import (
    SOCDomainConfig, SOC_CATEGORIES, SCORER_ACTIONS,
    SOC_FACTORS, SOC_FACTOR_SIGMA
)

# ═══ CONSTANTS ═══
C = len(SOC_CATEGORIES)
A = len(SCORER_ACTIONS)
D = len(SOC_FACTORS)
CATEGORIES = list(SOC_CATEGORIES)
ACTIONS = list(SCORER_ACTIONS)

ACTION_OFFSET_SCALE = 0.74
CATEGORY_WEIGHTS = [0.65, 0.12, 0.08, 0.06, 0.05, 0.04]
ORACLE_NOISE = 0.15
ETA_CONFIRM = 0.05
ETA_OVERRIDE = 0.01
THETA_CONF = 0.60
K_BATCH = 10
SIGMA_BAR = np.mean([SOC_FACTOR_SIGMA[f] for f in SOC_FACTORS])
SEEDS = [42, 123, 777, 2024, 9999]

FREQ_NOISE = {0: 0.08, 1: 0.12, 2: 0.15, 3: 0.18, 4: 0.22, 5: 0.22}
ADJACENT = {0: [1], 1: [0, 3], 2: [3], 3: [1, 2]}


def get_base_centroids():
    config = SOCDomainConfig()
    return config.get_initial_centroids()


def build_gt(rng, base_mu, offset_scale=ACTION_OFFSET_SCALE):
    gt = base_mu.copy()
    for ci in range(C):
        for ai in range(A):
            gt[ci, ai] += rng.normal(0, offset_scale, D) * 0.1
    return gt


def true_action(gt, ci, fv):
    dists = [np.linalg.norm(fv - gt[ci, ai]) for ai in range(A)]
    return int(np.argmin(dists))


def noise_realistic(gt_a, ci, rng, noise_rate=None):
    rate = noise_rate if noise_rate is not None else FREQ_NOISE.get(ci, 0.15)
    if rng.random() < rate:
        nbrs = ADJACENT.get(gt_a, [])
        if nbrs:
            return int(rng.choice(nbrs))
        wrong = [a for a in range(A) if a != gt_a]
        return int(rng.choice(wrong))
    return gt_a


def majority_acc(log):
    if not log:
        return 0.0
    by_cat = {}
    for ci, ga in log:
        by_cat.setdefault(ci, []).append(ga)
    maj = {ci: Counter(acts).most_common(1)[0][0] for ci, acts in by_cat.items()}
    return sum(1 for ci, ga in log if maj.get(ci) == ga) / len(log)


def make_scorer(mu=None):
    base = get_base_centroids() if mu is None else mu
    return ProfileScorer(mu=base.copy(), categories=CATEGORIES, actions=ACTIONS)


class ThreeStagePipeline:
    """Three-stage evidence pipeline wrapping ProfileScorer."""

    def __init__(self, scorer, K=K_BATCH, theta_conf=THETA_CONF,
                 category_weights=None):
        self.scorer = scorer
        self.K = K
        self.theta_conf = theta_conf
        self.cat_weights = category_weights or [1 / C] * C
        self.mean_weight = 1 / C
        self.buffers = {}
        self.counts = np.zeros((C, A))
        self.stats = {'gate_blocked': 0, 'gate_passed': 0,
                      'batch_total': 0, 'batch_sig': 0,
                      'batch_rej': 0, 'updates': 0}

    def process(self, fv, ci, scorer_action, correct, gt_action, confidence):
        if confidence > self.theta_conf:
            self.stats['gate_blocked'] += 1
            return
        self.stats['gate_passed'] += 1

        ai_target = gt_action
        key = (ci, ai_target)
        if key not in self.buffers:
            self.buffers[key] = []
        self.buffers[key].append({
            'fv': fv.copy(), 'correct': correct,
            'gt_action': gt_action, 'scorer_action': scorer_action,
        })
        if len(self.buffers[key]) >= self.K:
            self._flush(key)

    def _flush(self, key):
        ci, ai = key
        buf = self.buffers[key]
        confirmed = [b for b in buf if b['correct']]
        K_total = len(buf)
        self.stats['batch_total'] += 1
        self.buffers[key] = []

        if len(confirmed) == 0:
            self.stats['batch_rej'] += 1
            self.counts[ci, ai] += K_total
            return

        K_conf = len(confirmed)
        mu_cur = self.scorer.centroids[ci, ai]
        d_bar = np.mean([b['fv'] - mu_cur for b in confirmed], axis=0)
        magnitude = np.linalg.norm(d_bar)
        tau = SIGMA_BAR / np.sqrt(K_conf)

        self.counts[ci, ai] += K_total

        if magnitude <= tau:
            self.stats['batch_rej'] += 1
            return

        self.stats['batch_sig'] += 1

        N = self.counts[ci, ai]
        precision = K_total / (N + K_total)
        vol_scale = np.sqrt(self.mean_weight / self.cat_weights[ci])
        vol_scale = np.clip(vol_scale, 0.1, 3.0)
        combined = np.clip(precision * vol_scale, 0.01, 1.0)

        mean_fv = np.mean([b['fv'] for b in confirmed], axis=0)
        effective_fv = mu_cur + combined * (mean_fv - mu_cur)

        gt_actions = [b['gt_action'] for b in confirmed]
        batch_gt = Counter(gt_actions).most_common(1)[0][0]
        result = self.scorer.score(effective_fv.astype(np.float64), ci)
        batch_correct = (result.action_index == batch_gt)

        self.scorer.update(effective_fv.astype(np.float64), ci,
                           result.action_index, batch_correct, batch_gt)
        self.stats['updates'] += 1

    @property
    def update_rate(self):
        total = self.stats['gate_blocked'] + self.stats['gate_passed']
        return self.stats['updates'] / total if total > 0 else 0.0


def run_learning_loop(gt, start_mu, N, checkpoints, seed,
                      use_pipeline=False, K=K_BATCH, theta_conf=THETA_CONF,
                      cat_weights=None, oracle_noise_rate=None,
                      return_scorer=False):
    """Generic learning loop. Returns checkpoint dict."""
    rng = np.random.default_rng(seed)
    cw = cat_weights or CATEGORY_WEIGHTS

    scorer = make_scorer(start_mu)
    static = make_scorer(start_mu)
    pipeline = None
    if use_pipeline:
        pipeline = ThreeStagePipeline(scorer, K=K, theta_conf=theta_conf,
                                       category_weights=cw)

    lc, sc = 0, 0
    log = []
    cp = {}

    for n in range(1, N + 1):
        ci = int(rng.choice(C, p=cw))
        fv = np.clip(rng.normal(0.5, 0.15, D), 0, 1).astype(np.float64)
        ta = true_action(gt, ci, fv)
        oa = noise_realistic(ta, ci, rng, oracle_noise_rate)

        lr = scorer.score(fv, ci)
        correct = (lr.action_index == oa)
        if correct:
            lc += 1

        if use_pipeline:
            pipeline.process(fv, ci, lr.action_index, correct, oa, lr.confidence)
        else:
            scorer.update(fv, ci, lr.action_index, correct, oa)

        sr = static.score(fv, ci)
        if sr.action_index == oa:
            sc += 1
        log.append((ci, oa))

        if n in checkpoints:
            cp[n] = {
                'learn': lc / n * 100,
                'static': sc / n * 100,
                'majority': majority_acc(log) * 100,
                'frobenius': float(np.linalg.norm(scorer.centroids - start_mu)),
            }

    result = {'checkpoints': cp, 'pipeline_stats': pipeline.stats if pipeline else None}
    if return_scorer:
        result['scorer'] = scorer
    return result
