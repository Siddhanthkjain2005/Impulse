"""Conservative acquisition review for local trial feedback, not IEC certification.

Metrics remain the original linear-interpolation results. This review neither
resamples a waveform nor infers instrument bandwidth, saturation or uncertainty.
"""
import numpy as np


VERSION = 'waveform-acquisition-review-v1'
MIN_RISING_INTERVALS = 4


def assess_waveform(time_us, voltage_kv, measured):
    issues = []
    metrics = {'sample_count': 0, 'rising_intervals_30_90': 0,
               'minimum_rising_intervals': MIN_RISING_INTERVALS,
               'flat_crest_max_consecutive_samples': 0}
    try:
        t = np.asarray(time_us, dtype=float)
        raw = np.asarray(voltage_kv, dtype=float)
        if (t.ndim != 1 or raw.ndim != 1 or len(t) != len(raw) or len(t) < 10
                or not np.isfinite(t).all() or not np.isfinite(raw).all()
                or not (np.diff(t) > 0).all()):
            raise ValueError('Missing or invalid stored waveform samples.')
        metrics['sample_count'] = len(t)
        t30, t90 = float(measured['t30_us']), float(measured['t90_us'])
        baseline = float(measured.get('baseline_kv', 0))
        polarity = float(measured['polarity'])
        crest = float(measured['crest_kv'])
        if (not np.isfinite([t30, t90, baseline, polarity, crest]).all()
                or not t[0] <= t30 < t90 <= t[-1] or crest <= 0 or polarity not in (-1, 1)):
            raise ValueError('Stored extraction metadata cannot support acquisition review.')
        # Count acquired adjacent intervals intersecting the measured rising window.
        # Total CSV row count is insufficient when the front is sampled sparsely.
        intervals = int(np.sum((t[:-1] < t90) & (t[1:] > t30)))
        metrics['rising_intervals_30_90'] = intervals
        if intervals < MIN_RISING_INTERVALS:
            issues.append({'code': 'sparse_rising_limb', 'message':
                f'Only {intervals} acquired intervals span the rising 30–90% window; '
                f'at least {MIN_RISING_INTERVALS} are required for this local-calibration heuristic. '
                'Capture the rising limb at a higher sampling rate before creating a correction.'})
        v = (raw - baseline) * polarity
        # Exact or numerically equal plateaus are review flags, not a saturation diagnosis.
        at_crest = np.isclose(v, crest, rtol=0, atol=max(abs(crest) * 1e-9, 1e-12))
        longest = current = 0
        for equal in at_crest:
            current = current + 1 if equal else 0
            longest = max(longest, current)
        metrics['flat_crest_max_consecutive_samples'] = longest
        if longest >= 3:
            issues.append({'code': 'flat_crest', 'message':
                'A sustained flat crest may be clipped or quantized. Review the acquisition '
                'range and waveform before creating a correction; clipping is not proven.'})
    except (TypeError, ValueError, KeyError):
        issues.append({'code': 'missing_acquisition_evidence', 'message':
            'Stored waveform samples or extraction metadata are missing or invalid. '
            'Re-upload the original CSV to review acquisition quality before calibration.'})
    allowed = not issues
    return {'version': VERSION, 'status': 'usable' if allowed else 'review_required',
            'calibration_allowed': allowed, 'issues': issues, 'metrics': metrics,
            'scope': 'Acquisition heuristics only, not IEC certification or an instrument uncertainty estimate. '
                     'No resampling, smoothing or changes to raw samples. Passing does not establish laboratory accuracy.'}
