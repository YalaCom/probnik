import concurrent.futures, hashlib, html, json, os, pathlib, re, shutil, subprocess, tempfile, urllib.parse
ROOT=pathlib.Path('.')
AUDIO=ROOT/'assets/audio/animal-quiz'
IMAGES=ROOT/'assets/images/animal-quiz'
AUDIO.mkdir(parents=True,exist_ok=True)
IMAGES.mkdir(parents=True,exist_ok=True)
SOURCES=json.loads((ROOT/'assets/animal-quiz-sources.json').read_text())
USER_AGENT='LapkiAnimalQuiz/2.0 (https://github.com/YalaCom/probnik)'
COMMONS='https://commons.wikimedia.org/w/api.php'
WIKI='https://en.wikipedia.org/w/api.php'
def get(url):
    return subprocess.check_output(['curl','-fLsS','--retry','1','--max-time','35','-A',USER_AGENT,url],stderr=subprocess.PIPE)
def api(base,**params):
    return json.loads(get(base+'?'+urllib.parse.urlencode(dict(format='json',formatversion=2,**params))))
def image_info(file,width=None):
    params=dict(action='query',titles='File:'+file,prop='imageinfo',iiprop='url|extmetadata|mime')
    if width: params['iiurlwidth']=width
    page=api(COMMONS,**params)['query']['pages'][0]
    return page['imageinfo'][0]
def stripped(s):
    return html.unescape(re.sub('<[^>]*>','',s or '')).strip()
def credit(info,file):
    meta=info.get('extmetadata',{})
    def val(k):return stripped(meta.get(k,{}).get('value',''))
    license=val('LicenseShortName')
    if not license or not (license.startswith(('CC BY','CC0','Public domain','GFDL')) or 'public domain' in license.lower()):
        raise ValueError('Unverified or incompatible license '+license)
    if 'NC' in license or 'ND' in license:raise ValueError('Nonfree license '+license)
    return dict(file=file,author=val('Artist') or 'See source page',license=license,license_url=val('LicenseUrl'),source=info.get('descriptionurl') or 'https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(file.replace(' ','_')))
def direct(file):
    name=file.replace(' ','_'); digest=hashlib.md5(name.encode()).hexdigest()
    return 'https://upload.wikimedia.org/wikipedia/commons/'+digest[0]+'/'+digest[:2]+'/'+urllib.parse.quote(name)
def mp3_valid(b):return len(b)>100 and (b[:3]==b'ID3' or (b[0]==255 and b[1]&224==224))
def audio_valid(b):return len(b)>44 and ((b[:4]==b'RIFF' and b[8:12]==b'WAVE') or b[:4]==b'OggS' or mp3_valid(b))
def image_valid(b):return len(b)>200 and (b[:3]==b'\xff\xd8\xff' or b[:8]==b'\x89PNG\r\n\x1a\n' or (b[:4]==b'RIFF' and b[8:12]==b'WEBP'))
def save_photo(id,item):
    # English Wikipedia's lead photograph, then license and source checked at Commons.
    overrides={'cricket':'Feldgrille Gryllus campestris.jpg','dog':'GoldenRetrieverStanding.JPG','hen':'Hen chicken.jpg','rooster':'Domestic Rooster.jpg','duck':'Anas platyrhynchos domesticus 001.jpg'}
    if id in overrides:
        file=overrides[id]
        page={}
    else:
        q=api(WIKI,action='query',titles=item['article'],redirects=1,prop='pageimages',piprop='name|thumbnail',pithumbsize=640,pilicense='free')
        page=q['query']['pages'][0]
        file=page['pageimage']
    info=image_info(file,640)
    c=credit(info,file)
    url=info.get('thumburl') or page.get('thumbnail',{}).get('source') or info['url']
    b=get(url)
    if not image_valid(b):raise ValueError('Invalid photo bytes')
    ext='.jpg' if b[:3]==b'\xff\xd8\xff' else '.png' if b[:8]==b'\x89PNG\r\n\x1a\n' else '.webp'
    dest=IMAGES/(id+ext);dest.write_bytes(b)
    return './'+dest.as_posix(),c
# Grounded fallback metadata for the sources verified from their file descriptions.
MANUAL={
'crow':('Oona Räisänen (Mysid)','Public domain',''),
'goat':('stephan','Public domain',''),
'hen':('alys','Public domain',''),
'pigeon':('mary905','Public domain',''),
'bee':('Free Sounds Library','CC BY 3.0','https://creativecommons.org/licenses/by/3.0/'),
'donkey':('felix-blume','CC0','https://creativecommons.org/publicdomain/zero/1.0/')
}
FFMPEG=shutil.which('ffmpeg')
if not FFMPEG:
    try:
        import imageio_ffmpeg
        FFMPEG=imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:pass
def save_audio(id,item):
    file=item['file']
    if item['existing']:
        source=ROOT/'assets/audio'/file
        b=source.read_bytes()
        if not audio_valid(b):raise ValueError('Existing audio invalid')
        # Keep original file references unchanged unless conversion is possible.
        url='./'+source.as_posix()
        if FFMPEG:
            dest=AUDIO/(id+'.mp3')
            p=subprocess.run([FFMPEG,'-nostdin','-v','error','-y','-i',str(source),'-t','4.5','-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(dest)],capture_output=True)
            if p.returncode==0 and mp3_valid(dest.read_bytes()):url='./'+dest.as_posix()
            else:dest.unlink(missing_ok=True)
        return url,None
    try:
        info=image_info(file)
        c=credit(info,file)
        url=info['url']
    except Exception:
        if id not in MANUAL:raise
        author,lic,licurl=MANUAL[id]
        c=dict(file=file,author=author,license=lic,license_url=licurl,source='https://commons.wikimedia.org/wiki/File:'+urllib.parse.quote(file.replace(' ','_')))
        url=direct(file)
    b=get(url)
    if not audio_valid(b):raise ValueError('Invalid original audio')
    ext='.wav' if b[:4]==b'RIFF' else '.mp3' if mp3_valid(b) else '.ogg'
    dest=AUDIO/(id+ext)
    if FFMPEG:
        with tempfile.TemporaryDirectory() as td:
            src=pathlib.Path(td)/('source'+ext);src.write_bytes(b)
            mp3=AUDIO/(id+'.mp3')
            p=subprocess.run([FFMPEG,'-nostdin','-v','error','-y','-i',str(src),'-t','4.5','-ac','1','-ar','44100','-codec:a','libmp3lame','-b:a','96k',str(mp3)],capture_output=True)
            if p.returncode==0 and mp3_valid(mp3.read_bytes()):
                c['changes']='Converted to mono MP3, first 4.5 seconds.'
                return './'+mp3.as_posix(),c
            mp3.unlink(missing_ok=True)
    # Wikimedia MP3 transcode, useful on older iOS Safari, without a new dependency.
    if ext!='.mp3':
        name=file.replace(' ','_'); d=hashlib.md5(name.encode()).hexdigest()
        trans='https://upload.wikimedia.org/wikipedia/commons/transcoded/'+d[0]+'/'+d[:2]+'/'+urllib.parse.quote(name)+'/'+urllib.parse.quote(name)+'.mp3'
        try:
            mp=get(trans)
            if mp3_valid(mp):
                dest=AUDIO/(id+'.mp3');b=mp;c['changes']='Wikimedia MP3 transcode.'
        except Exception:pass
    dest.write_bytes(b)
    return './'+dest.as_posix(),c
def process(pair):
    id,item=pair
    result={};errors={};credits={}
    try: result['audio'],c=save_audio(id,item);credits['audio']=c
    except Exception as e: errors['audio']=str(e)[:250]
    try: result['image'],c=save_photo(id,item);credits['image']=c
    except Exception as e: errors['image']=str(e)[:250]
    print(id, result, errors,flush=True)
    return id,result,credits,errors
# Refresh only curated photos on subsequent runs.
previous_path=ROOT/'assets/animal-quiz-report.json'
if previous_path.exists():
    previous=json.loads(previous_path.read_text())
    oldmedia=previous['media']
    edits=['cricket','dog','hen','rooster','duck']
    oldcredits=(ROOT/'assets/animal-quiz-credits.md').read_text()
    def photo_refresh(id):
        try:
            path,c=save_photo(id,SOURCES[id])
            return id,path,c,None
        except Exception as e:return id,None,None,str(e)[:250]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        changes=list(pool.map(photo_refresh,edits))
    for id,path,c,error in changes:
        if path:
            oldmedia.setdefault(id,{})['image']=path
            if id in previous['errors']:
                previous['errors'][id].pop('image',None)
                previous['errors'][id].pop('image_refresh',None)
                if not previous['errors'][id]:previous['errors'].pop(id)
            name=SOURCES[id]['name']
            start=oldcredits.index('## '+name+'\n')
            end=oldcredits.find('\n## ',start+1)
            if end<0:end=len(oldcredits)
            block=oldcredits[start:end]
            block=re.sub(r'^- image:.*(?:\n(?!- |## |\s*$)[^\n]*)*','',block,flags=re.M)
            block=re.sub(r'^- Не удалось получить: image\s*','',block,flags=re.M)
            line=f'- image: [{c["file"]}]({c["source"]}); автор: {c["author"]}; лицензия: {c["license"]} {c.get("license_url","")}.'
            oldcredits=oldcredits[:start]+block.rstrip()+'\n'+line+'\n\n'+oldcredits[end:].lstrip('\n')
        else:
            previous['errors'].setdefault(id,{})['image_refresh']=error
    previous['image_count']=sum('image' in r for r in oldmedia.values())
    (ROOT/'assets/animal-quiz-media.js').write_text('window.LAPKI_ANIMAL_MEDIA = '+json.dumps(oldmedia,ensure_ascii=False,indent=2)+';\n')
    previous_path.write_text(json.dumps(previous,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'assets/animal-quiz-credits.md').write_text(oldcredits)
    print(json.dumps(previous,ensure_ascii=False),flush=True)
    raise SystemExit(0)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    records=list(pool.map(process,SOURCES.items()))
media={id:r for id,r,c,e in records if r}
report={'audio_count':sum('audio' in r for _,r,_,_ in records),'image_count':sum('image' in r for _,r,_,_ in records),'errors':{id:e for id,r,c,e in records if e},'media':media}
(ROOT/'assets/animal-quiz-media.js').write_text('window.LAPKI_ANIMAL_MEDIA = '+json.dumps(media,ensure_ascii=False,indent=2)+';\n')
(ROOT/'assets/animal-quiz-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
lines=['# Угадай животное — источники медиа','', 'Фотографии и записи хранятся локально. Исходные звуки старых животных указаны в AUDIO-CREDITS.md.','']
for id,r,credits,e in records:
    lines += ['## '+SOURCES[id]['name'],'']
    for kind,c in credits.items():
        if not c:continue
        lines += [f'- {kind}: [{c["file"]}]({c["source"]}); автор: {c["author"]}; лицензия: {c["license"]} {c.get("license_url","")}. {c.get("changes","")}']
    if e:lines += ['- Не удалось получить: '+', '.join(e)]
    lines+=['']
(ROOT/'assets/animal-quiz-credits.md').write_text('\n'.join(lines))
print(json.dumps(report,ensure_ascii=False),flush=True)
