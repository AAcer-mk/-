#!/usr/bin/env python3
"""Read-only technical measurements of inherited mix and authored silence."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import numpy as np


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    mix=args.source/'output/SILENT_PROTOCOL_MIX_SCENE_REVIEW_B10_v1_18M15S.flac'
    probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(mix)]))
    stream=next(s for s in probe['streams'] if s['codec_type']=='audio')
    assert stream['sample_rate']=='48000' and stream['channels']==2
    raw=subprocess.check_output(['ffmpeg','-v','error','-xerror','-i',str(mix),'-c:a','pcm_s32le','-f','s32le','-'])
    pcm=np.frombuffer(raw,dtype='<i4').reshape(-1,2)
    assert len(pcm)==1095*48000
    tl=json.loads((args.source/'project/full_picture_timeline.json').read_text())
    end=next(s for s in tl if s['id']=='END-03')
    a,b=end['start_frame']*2000,end['end_frame']*2000
    assert b-a==6*48000
    region=pcm[a:b]
    peak=float(np.max(np.abs(pcm.astype(np.int64))))/(2**31)
    report={'file':str(mix),'file_sha256':hashlib.sha256(mix.read_bytes()).hexdigest(),
            'sample_rate':48000,'channels':2,'sample_frames':len(pcm),'duration_seconds':len(pcm)/48000,
            'pcm_sha256':hashlib.sha256(raw).hexdigest(),'sample_peak_dBFS':float(20*np.log10(max(peak,1e-20))),
            'full_scale_samples':int(np.sum((pcm==2147483647)|(pcm==-2147483648))),
            'END_03':{'global_frames':[end['start_frame'],end['end_frame']],'sample_range':[a,b],
                       'sample_frames':b-a,'all_zero':bool(np.all(region==0)),'nonzero_samples':int(np.count_nonzero(region))},
            'new_voice_recording':False,'dialogue_performance_acceptance':'NOT_CLAIMED',
            'rights_chain_complete':False,'final_film_audio_acceptance':False}
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2))
    assert report['END_03']['all_zero'],'Authored silence failed'
    print(json.dumps(report,indent=2))


if __name__=='__main__':main()
