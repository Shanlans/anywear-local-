from PIL import Image,ImageDraw,ImageFilter
from pathlib import Path
out=Path('public/products');out.mkdir(parents=True,exist_ok=True)
def make(name,color,kind):
 im=Image.new('RGB',(768,768),'#f6f5f1');layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer)
 fill=color;line='#52605c'
 if kind=='tee':
  pts=[(298,178),(238,191),(132,299),(206,361),(266,315),(264,600),(504,600),(502,315),(562,361),(636,299),(530,191),(470,178),(444,216),(324,216)]
  d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill=line,width=3);d.arc((309,155,459,241),0,180,fill='#b6b6af',width=10);d.line((279,580,489,580),fill='#c5c4bc',width=3)
 elif kind=='hoodie':
  pts=[(300,218),(240,248),(183,326),(144,582),(218,598),(279,397),(279,619),(490,619),(490,397),(550,598),(624,582),(585,326),(528,248),(468,218)]
  d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill=line,width=3);d.rounded_rectangle((293,125,475,271),radius=75,fill=fill,outline=line,width=3);d.ellipse((324,160,444,265),fill='#7d987e');d.polygon([(310,473),(459,473),(472,551),(297,551)],fill='#91aa93');d.line((344,265,338,350),fill='#e3dfc7',width=5);d.line((423,265,430,350),fill='#e3dfc7',width=5);d.line((286,594,484,594),fill='#758d74',width=5)
 elif kind=='shirt':
  pts=[(295,181),(234,214),(182,300),(140,589),(219,599),(280,366),(276,619),(492,619),(488,366),(549,599),(628,589),(586,300),(534,214),(473,181)]
  d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill=line,width=3);d.polygon([(297,178),(346,161),(384,231),(343,280)],fill='#6e95ac');d.polygon([(471,178),(422,161),(384,231),(425,280)],fill='#6e95ac');d.line((384,231,384,614),fill='#a4bbca',width=5)
  for x in [302,407]:d.rectangle((x,311,x+62,388),fill='#6a8fa6',outline='#a4bbca',width=3);d.polygon([(x,311),(x+62,311),(x+31,333)],fill='#789fb4')
  for y in range(270,594,51):d.ellipse((379,y,390,y+11),fill='#dddad1')
 elif kind in ['jeans','trousers']:
  pts=[(256,143),(512,143),(530,316),(507,647),(401,647),(384,353),(367,647),(261,647),(238,316)]
  if kind=='trousers':pts=[(264,145),(504,145),(520,287),(548,646),(402,646),(384,338),(366,646),(220,646),(248,287)]
  d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill=line,width=3);d.rectangle((263,151,503,179),fill=fill,outline='#a5aa9b',width=3);d.line((384,181,384,311),fill='#aca58d',width=3)
  for x in [286,478]:d.line((x,170,x,200),fill='#c6bb99',width=5)
  d.arc((254,177,350,265),0,90,fill='#b8bfae',width=3);d.arc((418,177,514,265),90,180,fill='#b8bfae',width=3)
  d.line((267,626,360,626),fill='#adb5b0',width=3);d.line((408,626,503,626),fill='#adb5b0',width=3)
 elif kind=='shoes':
  for off in [0,172]:
   d.rounded_rectangle((125,340+off,646,411+off),radius=24,fill='#d9d7ce',outline='#888e86',width=3)
   pts=[(141,350+off),(153,233+off),(223,215+off),(297,258+off),(367,273+off),(455,304+off),(580,322+off),(637,365+off),(627,379+off),(152,379+off)]
   d.polygon(pts,fill=fill);d.line(pts+[pts[0]],fill='#8a9287',width=3);d.ellipse((156,221+off,247,275+off),fill='#c1c7bc');d.line((445,316+off,461,374+off),fill='#c7cac2',width=3)
   for i in range(5):d.line((280+i*26,261+off+i*8,309+i*26,287+off+i*8),fill='#b8bdb3',width=5)
 # soft studio shadow, original illustration (not a photograph)
 shadow=Image.new('RGBA',im.size);sd=ImageDraw.Draw(shadow);sd.ellipse((188,645,587,682),fill=(50,65,44,28));shadow=shadow.filter(ImageFilter.GaussianBlur(16));im=Image.alpha_composite(im.convert('RGBA'),shadow);im=Image.alpha_composite(im,layer);im.convert('RGB').save(out/f'{name}.png')
for a in [('tee','#e9e6dc','tee'),('hoodie','#a7bea8','hoodie'),('shirt','#7296af','shirt'),('jeans','#607b91','jeans'),('trousers','#c6b79c','trousers'),('sneakers','#f0f0e8','shoes')]:make(*a)
print('Created six original 768×768 garment illustrations')
