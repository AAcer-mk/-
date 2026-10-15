// Real Chromium video playback: decoder frames + progression + screenshots.
// These are functional playback checks, not a substitute for sound/acting review.
const { chromium } = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');

(async () => {
  const files = process.argv.slice(2).map(p => path.resolve(p));
  if (!files.length) throw new Error('Pass one or more MP4 files');
  const browser = await chromium.launch({executablePath:'/usr/bin/chromium', headless:true,
    args:['--no-sandbox','--autoplay-policy=no-user-gesture-required','--disable-dev-shm-usage']});
  try {
    for (const file of files) {
      const html = file + '.playback.html';
      fs.writeFileSync(html, '<!doctype html><meta charset="utf-8"><style>body{margin:0;background:#000}video{width:100vw;height:100vh}</style><video muted playsinline></video><script>document.querySelector("video").src='+JSON.stringify(pathToFileURL(file).href)+'</script>');
      const page = await browser.newPage({viewport:{width:1280,height:720}});
      await page.goto(pathToFileURL(html).href);
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
      await page.close();fs.unlinkSync(html);
    }
  } finally {await browser.close();}
})().catch(err=>{console.error(err);process.exit(1)});
