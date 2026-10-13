import test from 'node:test';
import assert from 'node:assert/strict';
import {classifyPixels,FrameVisibility,sampleVideo} from '../src/video-content.js';
function image(count,color){return Uint8ClampedArray.from(Array.from({length:count},()=>[...color,255]).flat());}
test('black video with a small watermark is distinct from visible dark clothing',()=>{
 const black=image(100,[0,0,0]);assert.equal(classifyPixels(black),'black');
 black.set([255,255,255,255],0);assert.equal(classifyPixels(black),'black');
 const darkClothing=image(100,[0,0,0]);darkClothing.set(image(40,[170,140,100]),0);assert.equal(classifyPixels(darkClothing),'visible');
 assert.equal(classifyPixels(image(100,[20,110,60])),'visible');
});
test('frame visibility ignores one transitional frame and requires actual visible content',()=>{
 const monitor=new FrameVisibility();assert.equal(monitor.update('black'),'waiting');assert.equal(monitor.update('black'),'waiting');assert.equal(monitor.update('black'),'black');
 assert.equal(monitor.update('visible'),'black');assert.equal(monitor.update('visible'),'visible');assert.equal(monitor.update('black'),'visible');assert.equal(monitor.update('visible'),'visible');
 monitor.reset();assert.equal(monitor.state,'waiting');assert.equal(monitor.update('unknown'),'unknown');
});
test('sampling only returns a classification and handles unreadable video safely',()=>{
 const pixels=image(32*18,[0,0,0]);let draws=0;const canvas={getContext:()=>({drawImage(){draws++;},getImageData:()=>({data:pixels})})};
 assert.equal(sampleVideo({readyState:2,videoWidth:1280},canvas),'black');assert.equal(canvas.width,32);assert.equal(canvas.height,18);assert.equal(draws,1);
 assert.equal(sampleVideo({readyState:0,videoWidth:0},canvas),'unknown');
 assert.equal(sampleVideo({readyState:2,videoWidth:1280},{getContext(){throw Error('Unavailable');}}),'unknown');
});
test('invalid samples never establish usable video',()=>{assert.equal(classifyPixels(null),'unknown');assert.equal(classifyPixels(new Uint8ClampedArray(3)),'unknown');});
