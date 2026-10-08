// User-supplied product photos stay local. Only descriptive metadata is versioned.
const preserve=' Apply only the garment, preserving the camera subject and background.';
export const localProducts=[
 {id:'local-mexico66',name:'MEXICO 66 黄黑运动鞋',category:'shoes',detail:'黄黑皮面 · 鞋类实验',file:'MEXICO 66 .webp',prompt:'Substitute the footwear with yellow low-top sneakers with black crossing side stripes, yellow laces and thin yellow soles with a white midsole strip.'+preserve},
 {id:'local-pace',name:'Pace Breaker 5英寸短裤',category:'bottoms',detail:'深灰 · 松紧腰短裤',file:'Pace Breaker Linerless Short 5".png',prompt:'Substitute the lower body garment with dark grey loose athletic shorts, an elastic waistband and above-knee hems, matching the reference shorts only.'+preserve},
 {id:'local-pride',name:'Pride 蓝色印花 T 恤',category:'tops',detail:'蓝色 · 胸前白色文字',file:'Heavyweight Cotton Jersey T-Shirt Pride.png',prompt:'Substitute the upper body garment with a loose bright light-blue cotton crew-neck t-shirt with white LOVE YOUR LIGHT lettering and smaller white text as visible in the reference.'+preserve},
 {id:'local-keyhole',name:'All It Takes 黑色罗纹上衣',category:'tops',detail:'贴身短款 · 正反面参考',views:[
  {label:'正面参考',file:'All It Takes Ribbed Keyhole Short-Sleeve Shirt.png',prompt:'Substitute the upper body garment with a fitted black ribbed crew-neck short-sleeve cropped shirt with a plain front. The supplied reference is the front view.'+preserve},
  {label:'背面参考',file:'All It Takes Ribbed Keyhole Short-Sleeve Shirt-back.png',prompt:'Substitute the upper body garment with a fitted black ribbed short-sleeve cropped shirt. Its back has a center seam and a horizontal lower-back cutout above the waistband. The reference is a rear view; place the cutout on the back only.'+preserve}
 ]},
 {id:'local-dance',name:'Dance Studio 拼色阔腿裤',category:'bottoms',detail:'米白拼色 · 抽绳阔腿',file:'Dance Studio Mid-Rise Oversized-Fit Pant Colourblock.png',prompt:'Substitute the lower body garment with oversized beige wide-leg trousers, a white elastic waistband, long white drawstrings and white outer side panels, matching the reference trousers only.'+preserve},
 {id:'local-meta2',name:'黑框绿片太阳镜',category:'accessories',detail:'黑色厚框 · 绿色镜片 · 配件实验',file:'meta2.webp',prompt:'Add sunglasses to the person\'s face, matching the reference: thick black rectangular frames, green tinted lenses and black temples. Fit the glasses naturally over the eyes and nose with the temples along the ears. Preserve the person\'s facial identity, existing clothing and background.'}
];
