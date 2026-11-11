"""Private 8x10 Y2K poster generator. Images sourced via Openverse; optional AI texture via OpenAI API."""
import base64, csv, io, json, math, os, random, re, time
from pathlib import Path
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from reportlab.pdfgen import canvas

W,H=2400,3000
OUT=Path('output'); OUT.mkdir(exist_ok=True)
SESSION=requests.Session(); SESSION.headers.update({'User-Agent':'PrivateY2KPosterMaker/1.0 (personal art project)'})
FONT='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'

def font(sz):
    try: return ImageFont.truetype(FONT,sz)
    except OSError: return ImageFont.load_default()

def rgb(h):
    h=h.strip().lstrip('#'); return tuple(int(h[i:i+2],16) for i in (0,2,4))

def slug(s): return re.sub(r'[^a-z0-9]+','-',s.lower()).strip('-')

def search_photos(query, max_photos=5):
    """Return downloaded candidate images and honest attribution metadata; never infer identity from image."""
    try:
        response=SESSION.get('https://api.openverse.org/v1/images/',params={'q':query,'page_size':20,'category':'photograph','mature':'false'},timeout=25)
        response.raise_for_status(); results=response.json().get('results',[])
    except Exception as e:
        print('Openverse search unavailable:',e); return [],[]
    photos=[]; credits=[]
    for r in results:
        if len(photos)>=max_photos: break
        if (r.get('width') or 0)<450 or (r.get('height') or 0)<450: continue
        url=r.get('url')
        if not url or not url.startswith('https://'): continue
        try:
            res=SESSION.get(url,timeout=15,stream=True)
            res.raise_for_status()
            buf=bytearray()
            for chunk in res.iter_content(65536):
                buf.extend(chunk)
                if len(buf)>12_000_000: raise ValueError('Photo too large')
            im=Image.open(io.BytesIO(buf)); im.load()
            if im.width<450 or im.height<450: continue
            photos.append(ImageOps.exif_transpose(im).convert('RGB'))
            credits.append({'title':r.get('title'),'creator':r.get('creator'),'license':r.get('license'),'license_url':r.get('license_url'),'source_page':r.get('foreign_landing_url'),'image_url':url,'note':'Search match only; identity and reuse rights NOT verified'})
        except Exception as e: print('Skipping inaccessible photo:',str(e)[:100])
    return photos,credits

def ai_texture(artist,album,palette):
    """Optional AI-generated decorative background. Never asks for a real person's likeness."""
    key=os.environ.get('OPENAI_API_KEY','').strip()
    if not key: return None
    prompt=(f'Original Y2K music scrapbook texture background for a personal collage inspired by the energy of {album}. '
            f'Colors {palette}. Torn paper, photocopy halftones, marker scribbles, doodle stars, abstract paint, vintage magazine texture. '
            'No text, no people, no portraits, no logos, no album-cover copies. Portrait 4:5.')
    try:
        r=SESSION.post('https://api.openai.com/v1/images/generations',headers={'Authorization':f'Bearer {key}'},json={
            'model':'gpt-image-1','prompt':prompt,'size':'1024x1536','n':1},timeout=180)
        r.raise_for_status(); data=r.json()['data'][0]
        if data.get('b64_json'):
            return Image.open(io.BytesIO(base64.b64decode(data['b64_json']))).convert('RGB')
        print('Image API returned no base64 image; using procedural background')
    except Exception as e: print('Optional AI background failed:',str(e)[:250])
    return None

def sticker(draw,x,y,r,color,seed):
    points=[]
    for i in range(16):
        a=i*math.pi/8; rr=r if i%2==0 else r*.30
        points.append((int(x+math.cos(a)*rr),int(y+math.sin(a)*rr)))
    draw.polygon(points,fill=color)

def background(palette,seed,ai=None):
    rng=random.Random(seed)
    if ai: return ImageOps.fit(ai,(W,H),method=Image.Resampling.LANCZOS).convert('RGB')
    im=Image.new('RGB',(W,H),palette[0]); d=ImageDraw.Draw(im)
    for i in range(24):
        x=rng.randint(-300,W); y=rng.randint(-300,H); w=rng.randint(250,1200)
        d.polygon([(x,y),(x+w,y-60),(x+w-90,y+120),(x-100,y+150)],fill=palette[(i%3)+1])
    for i in range(70):
        x=rng.randrange(W); y=rng.randrange(H); r=rng.randrange(12,100)
        if i%3==0: sticker(d,x,y,r,palette[2],seed)
        else: d.arc((x-r,y-r,x+r,y+r),rng.randrange(360),rng.randrange(360,720),fill=palette[3],width=rng.randint(4,14))
    return im

def cutout_mask(im):
    """Poster-style torn-paper cutout, not semantic background removal."""
    w,h=im.size
    mask=Image.new('L',(w,h),0); d=ImageDraw.Draw(mask)
    rng=random.Random(w*31+h)
    pts=[(int(w*(i/28)),int(rng.uniform(0,.055)*h)) for i in range(29)]
    pts += [(w,int(h*(i/28))) for i in range(29)]
    pts += [(int(w*(1-i/28)),int(h*(1-rng.uniform(0,.055)))) for i in range(29)]
    pts += [(0,int(h*(1-i/28))) for i in range(29)]
    d.polygon(pts,fill=255)
    return mask

def paste_photo(base,im,rect,angle,outline):
    x,y,w,h=rect
    photo=ImageOps.fit(im,(w,h),method=Image.Resampling.LANCZOS)
    paper=Image.new('RGBA',(w+36,h+36),(0,0,0,0))
    ImageDraw.Draw(paper).rectangle((0,0,w+35,h+35),fill=outline)
    photo=photo.convert('RGBA'); photo.putalpha(cutout_mask(photo))
    paper.alpha_composite(photo,(18,18))
    paper=paper.rotate(angle,expand=True,resample=Image.Resampling.BICUBIC)
    base.paste(paper,(x,y),paper)

def create(row,variant,photos,credits,ai):
    artist=row['artist'].strip(); album=row['album'].strip()
    colors=[rgb(s) for s in row.get('colors','#c9ff32|#111111|#ff7eb6|#70d9ff').split('|')]
    if len(colors)<4: colors=[(201,255,50),(17,17,17),(255,126,182),(112,217,255)]
    seed=variant*947+sum(ord(x) for x in artist+album)
    rng=random.Random(seed)
    base=background(colors,seed,ai if variant==1 else None).convert('RGBA')
    d=ImageDraw.Draw(base)
    # A strong focal panel plus two scrapbook secondary photo frames
    placements=[[(290,440,1600,1710,-7),(50,1750,850,940,13),(1520,1480,740,1000,-11)],
                [(400,280,1550,1880,6),(80,1700,900,1000,-12),(1450,1830,800,870,10)],
                [(280,500,1650,1690,-4),(20,1850,1000,950,-8),(1490,1600,800,1050,15)]][variant]
    if photos:
        for i,(x,y,w,h,angle) in enumerate(placements):
            paste_photo(base,photos[(i+variant)%len(photos)],(x,y,w,h),angle,colors[1] if i==0 else (250,245,235))
    else:
        # Never misrepresent abstract placeholders as photos of the musician
        d.rectangle((300,500,2100,2200),fill=(245,240,223),outline=colors[1],width=24)
        d.text((410,1180),'NO VERIFIED PHOTO',font=font(105),fill=colors[1])
        d.text((410,1320),'ADD / REVIEW SOURCES',font=font(75),fill=colors[1])
    # Hand-drawn overlays and punchy typography
    for i in range(45):
        x=rng.randint(0,W); y=rng.randint(0,H); r=rng.randint(25,105)
        if i%2: sticker(d,x,y,r,colors[2],seed+i)
        else: d.line([(x,y),(x+r,y-r),(x+r*2,y+r//2)],fill=colors[3],width=rng.randint(7,22),joint='curve')
    # Text on opaque paper strips for legibility
    d.rectangle((80,90,2320,340),fill=(248,244,225))
    d.text((130,115),artist.upper()[:25],font=font(145),fill=colors[1],stroke_width=1)
    d.rectangle((140,2560,2270,2860),fill=colors[1])
    d.text((205,2600),album.upper()[:26],font=font(120),fill=colors[0])
    d.text((1850,2850),f'VOL. 0{variant+1}',font=font(52),fill=colors[1])
    # Fine grain for printed scrapbook texture
    grain=Image.new('RGBA',(W,H),(0,0,0,0)); gd=ImageDraw.Draw(grain)
    for _ in range(13000):
        x=rng.randrange(W); y=rng.randrange(H)
        gd.point((x,y),fill=(20,20,20,rng.randint(10,60)))
    base=Image.alpha_composite(base,grain).convert('RGB')
    name=f'{slug(artist)}-{slug(album)}-scrapbook-{variant+1}'
    png=OUT/(name+'.png'); pdf=OUT/(name+'.pdf')
    base.save(png,dpi=(300,300),optimize=True)
    c=canvas.Canvas(str(pdf),pagesize=(8*72,10*72)); c.drawImage(str(png),0,0,width=8*72,height=10*72); c.showPage(); c.save()
    print('Saved',png,pdf)

def main():
    with open('albums.csv',newline='',encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
    for row in rows:
        if not row.get('artist') or not row.get('album'): continue
        artist=row['artist']; album=row['album']
        print('Searching Openverse for',artist)
        photos,credits=search_photos(row.get('search_query') or artist)
        ai=ai_texture(artist,album,row.get('colors',''))
        for variant in range(3): create(row,variant,photos,credits,ai)
        (OUT/f'{slug(artist)}-{slug(album)}-photo-sources.json').write_text(json.dumps({
            'artist':artist,'album':album,'search_results':credits,
            'warning':'Search matches are not identity-verified; license and publicity rights require independent review. Not cleared for merchandise.'},indent=2),encoding='utf-8')
    print('Finished')
if __name__=='__main__': main()
