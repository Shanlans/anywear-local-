// Inspect a tiny local sample; never retain or send pixels.
export function classifyPixels(pixels){
 if(!pixels?.length||pixels.length%4)return 'unknown';
 let sum=0,dark=0;const count=pixels.length/4;
 for(let i=0;i<pixels.length;i+=4){const luma=.2126*pixels[i]+.7152*pixels[i+1]+.0722*pixels[i+2];sum+=luma;if(luma<16)dark++;}
 return sum/count<16&&dark/count>=.95?'black':'visible';
}
export function sampleVideo(video,canvas){
 if(video?.readyState<2||!video?.videoWidth)return 'unknown';
 try{canvas.width=32;canvas.height=18;const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(video,0,0,32,18);return classifyPixels(context.getImageData(0,0,32,18).data);}catch{return 'unknown';}
}
export class FrameVisibility {
 constructor(){this.reset();}
 reset(){this.state='waiting';this.black=0;this.visible=0;}
 update(sample){
  if(sample==='black'){this.black++;this.visible=0;if(this.black>=3)this.state='black';}
  else if(sample==='visible'){this.visible++;this.black=0;if(this.visible>=2)this.state='visible';}
  else{this.black=0;this.visible=0;this.state='unknown';}
  return this.state;
 }
}
