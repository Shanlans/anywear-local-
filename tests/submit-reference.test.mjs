import test from 'node:test';
import assert from 'node:assert/strict';
import {submitReference} from '../src/submit-reference.js';
const snapshot=()=>({id:'local-pride',blob:new Blob(['image']),prompt:'Original garment request',enhance:false});
test('reference acceptance waits for set acknowledgement, not connection completion',async()=>{
 let acknowledge,accepted=false;const item=snapshot(),requests=[];
 const result=submitReference({set(request){requests.push(request);return new Promise(resolve=>acknowledge=resolve);}},item,()=>true).then(value=>{accepted=true;return value;});
 await Promise.resolve();assert.equal(accepted,false);assert.deepEqual(requests,[{image:item.blob,prompt:item.prompt,enhance:false}]);
 acknowledge();assert.equal((await result).id,item.id);assert.equal(accepted,true);
});
test('a rejected reference remains a request failure even if remote video is connected',async()=>{
 const error=Error('Cannot process image');const connection={isConnected:()=>true,set:async()=>{throw error;}};
 await assert.rejects(submitReference(connection,snapshot(),()=>true),value=>value===error);
});
test('a late acknowledgement after stop cannot mark a reference as accepted',async()=>{
 let acknowledge,current=true;const result=submitReference({set:()=>new Promise(resolve=>acknowledge=resolve)},snapshot(),()=>current);
 current=false;acknowledge();assert.equal(await result,null);
});
test('a pending request preserves its prompt snapshot while the next draft changes',async()=>{
 let acknowledge;const item=snapshot(),original=item.prompt;
 const result=submitReference({set:()=>new Promise(resolve=>acknowledge=resolve)},item,()=>true);
 item.prompt='Next draft';acknowledge();const accepted=await result;assert.equal(accepted.prompt,original);assert.ok(Object.isFrozen(accepted));
});
