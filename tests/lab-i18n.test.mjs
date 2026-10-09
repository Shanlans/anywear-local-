import {test} from 'node:test';
import assert from 'node:assert/strict';
import {dictionaries,escapeHtml} from '../src/lab/i18n.js';
test('consumer lab supplies matching Chinese and English dynamic labels',()=>{
 assert.deepEqual(Object.keys(dictionaries.zh).sort(),Object.keys(dictionaries.en).sort());
 for(const [key,value] of Object.entries(dictionaries.zh)) assert.ok(value.length,key);
});
test('model reasons are rendered as text',()=>assert.equal(escapeHtml('<img onerror="alert(1)">'),'&lt;img onerror=&quot;alert(1)&quot;&gt;'));
