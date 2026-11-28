const { chromium } = require('playwright');
const assert = require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
 const page=await browser.newPage({viewport:{width:390,height:844},isMobile:true,hasTouch:true,deviceScaleFactor:2});
 const errors=[];
 page.on('pageerror',e=>errors.push(String(e)));
 await page.goto('http://127.0.0.1:8765/',{waitUntil:'domcontentloaded'});
 await page.locator('#tiles .tile').first().waitFor();
 assert.equal(await page.locator('#tiles .tile').count(),12);
 const ids=await page.evaluate(()=>games.map(g=>g[0]));
 for(const width of [390,320]){
   await page.setViewportSize({width,height:844});
   for(const id of ids){
     await page.evaluate(id=>go(id),id);
     await page.locator('.vroom').waitFor();
     assert.ok((await page.locator('.vtitle').first().textContent()).trim(),id+' no title');
     assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),id+' horizontal overflow at '+width);
     await page.locator('#back').click();
   }
   console.log('All rooms opened at '+width+'px');
 }
 await page.setViewportSize({width:390,height:844});
 await page.evaluate(()=>go('listen'));
 await page.getByRole('button',{name:'Все 24',exact:true}).click();
 let idsSeen=[];
 for(let i=0;i<5;i++){
   const id=await page.evaluate(()=>vLastAnimal);
   idsSeen.push(id);
   const name=await page.evaluate(id=>listenAnimals.find(a=>a.id===id).name,id);
   if(i===0){const wrong=page.locator('.vcard').filter({hasNotText:name});await wrong.click();assert.equal(await page.locator('.vcard.vhint').count(),1);}
   await page.getByRole('button',{name,exact:true}).click();
   await page.locator('.vnext').filter({hasText:i===4?'Готово':'Дальше'}).click();
 }
 assert.equal(new Set(idsSeen).size,5);
 assert.equal(await page.locator('.vtitle').textContent(),'Отлично поиграли!');
 const media=await page.evaluate(async()=>{
   const entries=Object.entries(window.LAPKI_ANIMAL_MEDIA);
   const AudioClass=window.AudioContext||window.webkitAudioContext;
   const ctx=new AudioClass();
   const res=await Promise.all(entries.map(async ([id,m])=>{
      const response=await fetch(m.audio);
      const b=await ctx.decodeAudioData(await response.arrayBuffer());
      const image=await new Promise(resolve=>{const im=new Image();im.onload=()=>resolve(im.naturalWidth>0);im.onerror=()=>resolve(false);im.src=m.image});
      return {id,audio:response.ok&&b.duration>0,image};
   }));
   await ctx.close();
   return res;
 });
 assert.equal(media.length,24);
 for(const m of media)assert.ok(m.audio&&m.image,'invalid animal asset '+m.id);
 console.log('24 animal MP3 decoded and 24 photos loaded');
 await page.evaluate(()=>go('count'));
 const objects=page.locator('.vcount button');
 const n=await objects.count();for(let i=0;i<n;i++)await objects.nth(i).click();
 assert.equal(await page.locator('.vcount .counted').count(),n);
 assert.equal(await page.locator('.vnext').isVisible(),true);
 await page.evaluate(()=>go('phone'));
 await page.getByRole('button',{name:'☎️ Набрать номер'}).click();
 await page.getByRole('button',{name:'1',exact:true}).click();
 await page.getByRole('button',{name:'📞 Позвонить'}).click();
 assert.equal(await page.locator('.vtitle').textContent(),'Алло!');
 await page.getByRole('button',{name:'📞 Алло',exact:true}).click();
 await page.getByRole('button',{name:'👋 Пока',exact:true}).click();
 assert.equal(await page.locator('.vtitle').textContent(),'Кому позвоним?');
 await page.evaluate(()=>go('paint'));
 const canvas=page.locator('canvas');assert.ok(await canvas.isVisible());
 await canvas.click({position:{x:50,y:50}});
 await page.getByRole('button',{name:'🧽 Очистить'}).click();
 await page.evaluate(()=>go('build'));
 await page.getByRole('button',{name:'По образцу',exact:true}).click();
 for(const name of ['красный','жёлтый','синий'])await page.getByRole('button',{name,exact:true}).click();
 assert.equal(await page.locator('.vbrick').count(),3);
 assert.equal(await page.locator('.vnext').isVisible(),true);
 assert.deepEqual(errors,[]);
 console.log('Guided interactions and JavaScript error checks passed');
 await browser.close();
})().catch(err=>{console.error(err);process.exit(1)});
