#!/usr/bin/env python3
"""Build the complete shot inventory from recovered files and measured media.

Candidate counts are physical files, not creative approvals. A section video is
evidence of an inherited workprint, never an automatic final-shot designation.
"""
import argparse
import collections
import json
from pathlib import Path


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--repo',type=Path,required=True)
    args=p.parse_args();repo=args.repo;source=args.source
    timeline=json.loads((source/'project/full_picture_timeline.json').read_text())
    media=json.loads((repo/'production/codex_pipeline/qa/inherited/media.json').read_text())
    valid={Path(r['path']).resolve():r for r in media if r.get('full_decode')=='PASS'}
    def short(path):
        return 'baseline/'+str(path.relative_to(source)) if path.is_relative_to(source) else str(path.relative_to(repo))
    rows=[]
    for s in timeline:
        sid=s['id'];candidates=[]
        for folder in [source/'art/candidates',source/'graphics/native_candidates',repo/'production/sol61/assets']+[repo/f'production/sol61_r{r}/assets' for r in range(2,7)]:
            candidates.extend(folder.glob(sid+'_v*.png'))
        inherited=[p for p in valid if p.parent==source/'output/sections' and p.name.startswith(s['section']+'_')]
        if sid.startswith('E6-') or sid=='E6-CARD':
            if sid not in ['E6-07','E6-08']:
                inherited.extend(p for p in valid if ('E6_PART_A_WORKPRINT' in p.name and sid!='E6-09') or (p.name.startswith('E6-09') and sid=='E6-09'))
        if s['section']=='F7':inherited.extend(p for p in valid if p.name=='F7_SEQUENCE_WORKPRINT_r3_1080P_BILINGUAL.mp4')
        if sid in ['E7-01','E7-08','E7-09']:inherited.extend(p for p in valid if p.name.startswith(sid+'_WORKPRINT_r5_') and p.suffix=='.mp4')
        if sid=='E7-CARD':inherited.extend(p for p in valid if p.name=='E7_CARD_WORKPRINT_r4_MASTER.mkv')
        if sid in ['E7-04','E7-05']:inherited.extend(p for p in valid if p.name=='E7_APPROVAL_INSERTS_WORKPRINT_r4_MASTER.mkv')
        if sid=='E7-07':inherited.extend(p for p in valid if p.name=='E7_PRINTER_LCD_WORKPRINT_r4_MASTER.mkv')
        if candidates or inherited:
            status='部分完成';reason='源候选/已解码工作版存在，最终创作验收未通过'
        elif s.get('native'):
            status='仅有配置，未渲染';reason='原生图形实现存在，未找到对应已验证输出'
        else:
            status='完全缺失画面资产';reason='恢复范围内没有对应候选或已验证工作片'
        movement='程序化二维动画' if s.get('native') else '静态图片与整体摄影运动'
        if sid in ['F5-04','F6-03','F6-04','F7-01','F7-03']:movement='静态端点局部光流，表演需返工'
        if sid=='E5-06':movement='多层二维合成，独立车辆图层'
        if sid in ['E7-02','E7-03','E7-06','E6-07','E6-08']:
            reason='缺少连续人物动作；静帧不能补足';status='部分完成/连续表演缺失'
        rows.append({**s,'audit_status':status,'motion_type':movement,'reason':reason,
                     'candidate_paths':[short(p) for p in candidates],
                     'inherited_decoded_media':[short(p) for p in sorted(set(inherited))],
                     'candidate_count_is_not_approval':True,'final_creative_acceptance':False,
                     'audio_acceptance':'无法验证最终表演','new_render':None})
    payload={'schema':2,'fps':24,'frames':26280,'status_counts':dict(collections.Counter(x['audit_status'] for x in rows)),
             'final_accepted_shots':0,'scope':'All 152 authored timeline entries, 140 photographic descriptions','shots':rows}
    (repo/'production/SHOT_AUDIT.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2))
    lines=['# 逐镜恢复审计','','全部152条保留原帧区间。候选数只计文件，不等于合格候选数；已解码分场工作版不等于正式表演或导演终验。完整文件映射见`production/SHOT_AUDIT.json`。','',
           '|镜头|帧区间 [起,止)|状态|历史运动方法|候选文件数|工作片引用数|','|---|---|---|---|---|---|']
    for r in rows:lines.append(f"|{r['id']}|{r['start_frame']}–{r['end_frame']}|{r['audit_status']}|{r['motion_type']}|{len(r['candidate_paths'])}|{len(r['inherited_decoded_media'])}|")
    (repo/'docs/CODEX_SHOT_AUDIT.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps(payload['status_counts'],ensure_ascii=False))


if __name__=='__main__':main()
