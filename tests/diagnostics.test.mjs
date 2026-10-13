import {test} from 'node:test';import assert from 'node:assert/strict';import {sanitizeEvent} from '../diagnostics.mjs';
test('diagnostics accepts only defined metadata and rejects credential or media payloads',()=>{assert.deepEqual(sanitizeEvent({event:'connect-error',code:'WEBRTC_ICE_ERROR',reason:'ice',durationMs:25000}),{event:'connect-error',code:'WEBRTC_ICE_ERROR',reason:'ice',durationMs:25000});for(const payload of [{event:'test',apiKey:'secret'},{event:'test',prompt:'private'},{event:'test',url:'https://example/?key=secret'},{event:'test',image:'pixels'},{event:'test',code:'https://unsafe'},{event:'test',durationMs:NaN}])assert.equal(sanitizeEvent(payload),null);});

test('connection signatures discard URLs, identifiers and credentials while keeping diagnosis',async()=>{const {errorSignature,errorReason}=await import('../src/diagnostics.js');const message='could not establish signal connection: server was not reachable https://example.test/?token=private dct_privateSecret12345';assert.equal(errorSignature(Error(message)),'could not establish signal connection server not reachable');assert.equal(errorReason(Error(message)),'network');assert.equal(errorReason(Error('Failed to create LiveKit frame-metadata worker')),'worker');assert.equal(errorSignature(Error('customer photograph password privateValue')), '');});

test('camera device failures never look like ICE negotiation failures',async()=>{const {errorReason}=await import('../src/diagnostics.js');for(const name of ['NotAllowedError','NotFoundError','NotReadableError','OverconstrainedError'])assert.equal(errorReason(Object.assign(Error('Requested device not found'),{name})),'camera');assert.equal(errorReason(Error('device not found')),'unknown');assert.equal(errorReason(Error('ICE connection failed')),'ice');assert.equal(errorReason({code:'WEBRTC_ICE_ERROR',message:'Negotiation failed'}),'ice');});
test('wrapped SDK signaling errors retain a safe cause and never imply a camera failure',async()=>{
 const {errorReason,errorSignature}=await import('../src/diagnostics.js');
 const wrapped={code:'WEBRTC_SIGNALING_ERROR',message:'Signaling error',cause:Error('Cannot decode image https://private.example/file dct_privateSecret12345 Alice 12.34')};
 assert.equal(errorReason(wrapped),'signaling');assert.equal(errorSignature(wrapped),'signaling error cannot decode image');
 assert.equal(sanitizeEvent({event:'sdk-error',reason:'signaling',signature:errorSignature(wrapped)})?.reason,'signaling');
 wrapped.cause=Error('Insufficient credits');assert.equal(errorReason(wrapped),'credit');
});
test('cyclic error causes are bounded and never serialize arbitrary details',async()=>{
 const {errorReason,errorSignature}=await import('../src/diagnostics.js');const error={code:'WEBRTC_SIGNALING_ERROR',message:'Signaling error'};error.cause=error;
 assert.equal(errorReason(error),'signaling');assert.equal(errorSignature(error),'signaling error');
});
test('nested signatures fit the backend field limit without losing the entire event',async()=>{
 const {errorSignature}=await import('../src/diagnostics.js');const error={message:'initialization '.repeat(40),cause:Error('processing '.repeat(40))};
 const signature=errorSignature(error);assert.ok(signature.length>0&&signature.length<=240);
 assert.ok(sanitizeEvent({event:'sdk-error',reason:'signaling',signature}));
});
