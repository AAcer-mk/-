// Real Chromium video playback: decoder frames + progression + screenshots.
// These are functional playback checks, not a substitute for sound/acting review.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');

(async () => {
  const files = process.argv.slice(2).map(p => path.resolve(p));
  if (!files.length) throw new Error('Pass one or more MP4 files');
  // Use a short-lived loopback server: managed Chromium blocks file:// pages.
  const server=http.createServer((req,res)=>{
    const match=/^\/(video|page)\/(\d+)$/.exec(req.url);
    if(!match || !files[+match[2]]){res.writeHead(404);res.end();return;}
    if(match[1]==='page'){
      res.writeHead(200,{'Content-Type':'text/html; charset=utf-8'});
      res.end('<!doctype html><style>body{margin:0;background:#000}video{width:100vw;height:100vh}</style><video muted playsinline src="/video/'+match[2]+'"></video>');return;
    }
    const file=files[+match[2]],size=fs.statSync(file).size;
    const range=/^bytes=(\d+)-(\d*)$/.exec(req.headers.range||'');
    const start=range?+range[1]:0,end=range&&range[2]?Math.min(+range[2],size-1):size-1;
    const headers={'Content-Type':'video/mp4','Accept-Ranges':'bytes','Content-Length':end-start+1};
    if(range)headers['Content-Range']='bytes '+start+'-'+end+'/'+size;
    res.writeHead(range?206:200,headers);fs.createReadStream(file,{start,end}).pipe(res);
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base='http://127.0.0.1:'+server.address().port;
  const browser = await chromium.launch({executablePath:'/usr/bin/chromium', headless:true,
    args:['--no-sandbox','--autoplay-policy=no-user-gesture-required','--disable-dev-shm-usage']});
  try {
    for (const [index,file] of files.entries()) {
      const page = await browser.newPage({viewport:{width:1280,height:720}});
      await page.goto(base+'/page/'+index);
      await page.waitForFunction(() => {const v=document.querySelector('video');return v.readyState>=2 || v.error;});
      const initial=await page.evaluate(async () => {
        const v=document.querySelector('video');if(v.error)throw new Error(v.error.message);
        window.framesSeen=0;function seen(){window.framesSeen++;v.requestVideoFrameCallback(seen)}
        v.requestVideoFrameCallback(seen);await v.play();
        return {width:v.videoWidth,height:v.videoHeight,duration:v.duration};
      });
      await page.waitForFunction(() => {const v=document.querySelector('video');return v.currentTime>=Math.min(.5,v.duration*.5) || v.ended;});
      await page.screenshot({path:file+'.playback.png'});
      await page.waitForFunction(() => document.querySelector('video').ended,{},{timeout:Math.ceil(initial.duration*1000)+15000});
      const last=await page.evaluate(() => {
        const v=document.querySelector('video'),q=v.getVideoPlaybackQuality();
        return {ended:v.ended,time:v.currentTime,error:v.error&&v.error.message,
          decodedFrames:q.totalVideoFrames,droppedFrames:q.droppedVideoFrames,callbacks:window.framesSeen};
      });
      if (last.error || !last.ended || last.decodedFrames<10 || last.callbacks<3) throw new Error(JSON.stringify(last));
      fs.writeFileSync(file+'.playback.json',JSON.stringify({file,...initial,...last,status:'ACTUAL_CHROMIUM_PLAYBACK_PASS',creative_acceptance:false},null,2));
      console.log('PLAYBACK PASS',path.basename(file),last.decodedFrames,'decoded frames');
      await page.close();
    }
  } finally {await browser.close();await new Promise(resolve=>server.close(resolve));}
})().catch(err=>{console.error(err);process.exit(1)});
