"""Printable offline comparison of a baseline plan and saved alternatives."""
import html


def transition_report(plan):
    e = lambda value: html.escape(str(value), quote=True)
    def table(headers, rows):
        return '<table><thead><tr>' + ''.join(f'<th>{e(h)}</th>' for h in headers) + '</tr></thead><tbody>' + ''.join(
            '<tr>' + ''.join(f'<td>{e(cell)}</td>' for cell in row) + '</tr>' for row in rows) + '</tbody></table>'
    baseline, target = plan['baseline'], plan['target']
    alternatives = table(['Original rank', 'Candidate', 'Nominal checks', 'Network families changed', 'Stage change', 'Shared-stage part changes', 'Charge Δ kV/stage', 'Uncertainty'], [
        [o['original_rank'], o['candidate_id'], 'Pass' if o['nominal_review']['eligible_nominal'] else 'Review',
         o['changed_network_families'], o['active_stages_added'] - o['active_stages_deactivated'],
         o['shared_stage_part_changes'], f"{o['charge_delta_kv_stage']:+.3f}", o['uncertainty_status']]
        for o in plan['options']])
    chosen = next((o for o in plan['options'] if o['candidate_id'] == plan['closest_nominal_candidate_id']), None)
    details = ''
    if chosen:
        for name, network in chosen['networks'].items():
            rows = [[f"{p['ohm']:g} Ω", p['baseline_per_stage'], p['target_per_stage'],
                     p['retained_on_shared_stages'], p['added_on_shared_stages'], p['removed_from_shared_stages'],
                     p['required_on_newly_active_stages'], p['present_on_deactivated_stages']]
                    for p in network['parts']]
            details += f'<section><h2>{e(name.title())} network</h2><p>{e(network["baseline_topology"])} → {e(network["target_topology"])}</p>'
            details += table(['Value', 'Before /stage', 'After /stage', 'Retained, shared stages', 'Added, shared stages', 'Removed, shared stages', 'Newly active stages', 'Deactivated stages'], rows) + '</section>'
        verification = chosen.get('verification')
        challenge = f"{verification['passed']}/{verification['total']} recorded checks pass" if verification else 'Post-ranking challenge not recorded'
        details = f'<h2>Closest nominal option: original rank {e(chosen["original_rank"])}</h2><p>{e(challenge)} · uncertainty {e(chosen["uncertainty_status"])}.</p>' + details
    else:
        details = '<p>No nominally passing option is selected. Failing alternatives remain diagnostic.</p>'
    priorities = ' → '.join(plan['priority'])
    return f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Setup transition {e(plan['id'])}</title>
<style>body{{font:14px system-ui;color:#16303f;background:#eef3f5;margin:0}}main{{max-width:1100px;margin:24px auto;background:white;padding:32px}}h1{{font-size:28px}}h2{{font-size:18px;margin-top:26px}}p{{line-height:1.6}}table{{border-collapse:collapse;width:100%;font-size:12px}}td,th{{border-bottom:1px solid #d8e3e8;padding:10px;text-align:left;vertical-align:top}}th{{background:#f0f5f6}}.callout{{border-left:4px solid #be8a39;padding:14px;background:#fff6e7}}.audit{{font-size:11px;overflow-wrap:anywhere}}@media print{{body{{background:white}}main{{margin:0;padding:0}}thead{{display:table-header-group}}tr{{break-inside:avoid}}@page{{size:A4 landscape;margin:14mm}}}}</style>
<main><p>IMPULSETWIN AI · SAVED SETUP COMPARISON</p><h1>Plan changes before the next shot</h1>
<p>Baseline {e(baseline['run_id'])} / {e(baseline['candidate_id'])} → target {e(target['run_id'])}, {e(target['impulse_type'])}, {e(target['test_kv'])} kV.</p>
<p>{e(baseline['profile_name'])} · layout {e(baseline['layout_id'])}. Inventory: {e(target['inventory_provenance'])}.</p>
<aside class="callout">{e(plan['review'])}<p>{e(plan['scope'])}</p></aside>
<h2>Saved alternatives in their original order</h2>{alternatives}<p>Change preference: {e(priorities)}. Original optimizer ranking is unchanged; post-ranking challenge results do not select this option.</p>
{details}<h2>Audit trail</h2><p class="audit">Plan {e(plan['id'])} · {e(plan['created_at'])}<br>Baseline run SHA-256: {e(baseline['run_sha256'])}<br>Target run SHA-256: {e(target['run_sha256'])}<br>Target model: {e(target['model_version'])}</p></main></html>'''
