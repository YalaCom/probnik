const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
 const errors=[];page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
 assert.equal(await page.locator('#tiles .tile').count(),12);
 const ids=await page.evaluate(()=>games.map(g=>g[0]));
 for(const width of [390,320,768]){
   await page.setViewportSize({width,height:844});
   for(const id of ids){
     await page.evaluate(id=>go(id),id);
     assert.ok(await page.locator('#game').evaluate(el=>el.children.length>0),id+' empty');
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),id+' horizontal overflow at '+width);
     await page.locator('#back').click();
   }
   console.log('12 rooms opened at '+width+'px');
 }
 await page.setViewportSize({width:390,height:844});
 const media=await page.evaluate(async()=>{
   const entries=Object.entries(window.LAPKI_ANIMAL_MEDIA);
   const C=window.AudioContext||window.webkitAudioContext;const ctx=new C();
   const res=await Promise.all(entries.map(async ([id,m])=>{
      const response=await fetch(m.audio);const b=await ctx.decodeAudioData(await response.arrayBuffer());
      const image=await new Promise(resolve=>{const im=new Image();im.onload=()=>resolve(im.naturalWidth>0);im.onerror=()=>resolve(false);im.src=m.image});
      let peak=0;for(let i=0;i<b.numberOfChannels;i++)for(const v of b.getChannelData(i))peak=Math.max(peak,Math.abs(v));
      return {id,duration:b.duration,peak,image};
   }));await ctx.close();return res;
 });
 assert.equal(media.length,24);
 for(const m of media)assert.ok(m.duration>0.05&&m.peak>0.001&&m.image,'invalid animal asset '+m.id);
 console.log('24 animal MP3 decoded and 24 photos loaded');
 console.log(JSON.stringify(media.map(m=>({id:m.id,seconds:+m.duration.toFixed(2),peak:+m.peak.toFixed(3)}))));
 await page.evaluate(()=>go('listen'));
 let initial=await page.evaluate(()=>listenLast);
 const name=await page.evaluate(id=>listenAnimals.find(a=>a.id===id).name,initial);
 await page.getByRole('button',{name,exact:true}).click();
 await page.waitForFunction(id=>listenLast!==id,initial);
 assert.equal(await page.locator('.listen-card').count(),2);
 const bag=await page.evaluate(()=>{let out=[];listenBag=[];listenLast=null;const pool=listenAnimals;for(let i=0;i<48;i++)out.push(listenNext(pool).id);return out});
 assert.equal(new Set(bag.slice(0,24)).size,24);assert.equal(new Set(bag.slice(24)).size,24);assert.notEqual(bag[23],bag[24]);
 await page.evaluate(()=>go('animals'));
 assert.equal(await page.locator('.zoo-card').count(),24);
 await page.getByRole('button',{name:'Кошка',exact:true}).click();
 await page.evaluate(()=>go('phone'));
 assert.equal(await page.locator('.keys .key').count(),12);
 await page.getByRole('button',{name:'1',exact:true}).click();
 await page.getByRole('button',{name:'2',exact:true}).click();
 assert.equal(await page.locator('.digits').textContent(),'12');
 await page.getByRole('button',{name:'Позвонить',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.phone-status').textContent.includes('на связи'));
 assert.equal(await page.locator('.phone-status').textContent(),'Зайка на связи');
 await page.getByRole('button',{name:'Завершить звонок',exact:true}).click();
 assert.equal(await page.locator('.digits').textContent(),'');
 await page.getByRole('button',{name:'Позвонить: Котик',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.phone-status').textContent==='Котик на связи');
 await page.getByRole('button',{name:'Завершить звонок',exact:true}).click();
 assert.ok(await page.evaluate(()=>!soundUrls.bearVoice&&!soundUrls.chatter&&!soundUrls.laugh&&!soundUrls.laugh2));
 await page.evaluate(()=>go('bubbles'));await page.locator('.bubble').first().waitFor();await page.locator('.bubble').first().click();assert.ok((await page.locator('.bubble-count').textContent()).includes('1'));
 await page.evaluate(()=>go('count'));assert.equal(await page.locator('.number').count(),5);
 await page.evaluate(()=>go('music'));assert.equal(await page.locator('.note').count(),7);await page.locator('.note').first().click();
 await page.evaluate(()=>go('paint'));await page.locator('canvas').click({position:{x:50,y:50}});
 assert.deepEqual(errors,[]);
 console.log('Phone calls and hang-up, no-repeat quiz, bubbles, count, piano, drawing passed');
 await browser.close();
})().catch(err=>{console.error(err);process.exit(1)});
