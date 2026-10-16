#!/usr/bin/env python3
"""Actual local preset TTS, preserving source model hashes and original dialogue.

Outputs are isolated casting/performance candidates. Never replaces a film mix
or asserts that an inherited character voice has been matched.
"""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess
import time

import numpy as np
import onnxruntime as ort
import soundfile as sf
from kokoro_onnx import Kokoro
from misaki import zh

EXPECTED={
    'kokoro-v1.0.onnx':(325505369,'beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a'),
    'voices-v1.0.bin':(28214398,'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d')}


def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    p=argparse.ArgumentParser();p.add_argument('--models',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    for name,(size,want) in EXPECTED.items():
        path=args.models/name;assert path.stat().st_size==size and digest(path)==want,name
    ort.disable_telemetry_events();options=ort.SessionOptions()
    options.intra_op_num_threads=1;options.inter_op_num_threads=1;options.execution_mode=ort.ExecutionMode.ORT_SEQUENTIAL
    options.add_session_config_entry('session.intra_op.allow_spinning','0')
    session=ort.InferenceSession(str(args.models/'kokoro-v1.0.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
    model=Kokoro.from_session(session,str(args.models/'voices-v1.0.bin'))
    g2p=zh.ZHG2P(version='1.0')
    items=[('HALE_F7_yunjian','很好。还剩三个。你做得很好，林雾。','zm_yunjian',.92),
           ('HALE_F7_yunxi','很好。还剩三个。你做得很好，林雾。','zm_yunxi',.92),
           ('HALE_F7_yunyang','很好。还剩三个。你做得很好，林雾。','zm_yunyang',.92),
           ('LINWU_F9_xiaoyi','你回答我！','zf_xiaoyi',.95)]
    rows=[]
    for name,text,voice,speed in items:
        target=args.output/(name+'_CASTING_CANDIDATE.flac')
        if target.exists():raise FileExistsError('Preserve prior candidates; use a new output revision')
        phones,_=g2p(text)
        if '❓' in phones:raise ValueError('Unresolved phonemes: '+text)
        start=time.monotonic();wave,sr=model.create(phones,voice=voice,speed=speed,is_phonemes=True)
        wave=np.asarray(wave,dtype=np.float32)
        assert np.isfinite(wave).all() and len(wave)>sr/3 and np.max(np.abs(wave))<1
        sf.write(target,wave,sr,subtype='PCM_24')
        subprocess.run(['ffmpeg','-v','error','-xerror','-i',str(target),'-f','null','-'],check=True)
        row={'path':target.name,'text':text,'phonemes':phones,'model':'Kokoro v1.0 ONNX',
             'preset':voice,'speed':speed,'sample_rate':sr,'channels':1,'sample_frames':len(wave),
             'seconds':len(wave)/sr,'synthesis_seconds':time.monotonic()-start,'sha256':digest(target),
             'peak_dBFS':float(20*np.log10(max(float(np.max(np.abs(wave))),1e-20))),
             'full_decode':'PASS','human_reference_audio':False,'new_recording':True,
             'final_performance_acceptance':False,'historical_voice_identity_matched':False,
             'status':'NEW_LOCAL_SYNTHESIS_CASTING_AND_LANGUAGE_REVIEW_PENDING'}
        rows.append(row);print(json.dumps(row,ensure_ascii=False),flush=True)
    report={'generator_sha256':digest(Path(__file__)),'model_files':{name:{'bytes':size,'sha256':h} for name,(size,h) in EXPECTED.items()},
            'source_record':'baseline/docs/B06_NEW_VOICE_SOURCE_RECORD.json',
            'public_model_url':'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/',
            'license':'Model/presets: Apache-2.0 per maintainer; kokoro-onnx runtime: MIT',
            'weights_redistributed':False,'runtime':{name:importlib.metadata.version(name) for name in ['kokoro-onnx','onnxruntime','misaki','soundfile','numpy']},
            'source_film_mix_modified':False,'candidates':rows,
            'limitations':['Casting/voice identity and language listening review pending.',
                           'Hale breath/pitch abnormality and Lin Wu emotional break are not certified.',
                           'The existing mixed dialogue has not been source-separated or replaced.']}
    (args.output/'VOICE_CANDIDATES.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
