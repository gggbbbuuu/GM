/* Small WASI Preview1 host for the isolated Go/Python TCP bridge probe.
 * Not a general WASI implementation; has no filesystem/network access except
 * the explicitly provided host imports backed by Python localhost callbacks.
 */
var __goBridge = (function () {
 'use strict';
 var wasmBytes = null, memory = null, output = '', module = null, instance = null;
 var digits = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
 var argv = ['go-request-api-v0.8'];
 var inputBytes = null, inputOffset=0;
 function ensureMemory() { if (!memory) throw Error('Go module memory not ready'); }
 function U8() { ensureMemory(); return new Uint8Array(memory.buffer); }
 function DV() { ensureMemory(); return new DataView(memory.buffer); }
 function check(ptr, n) {
   var m = U8();
   if (ptr < 0 || n < 0 || ptr + n > m.length || n > 1048576) throw Error('WASM memory OOB '+ptr+'/'+n);
   return m;
 }
 function put32(ptr, val) { check(ptr,4); DV().setUint32(ptr, val >>> 0, true); }
 function get32(ptr) { check(ptr,4); return DV().getUint32(ptr,true); }
 function put64(ptr, value) { check(ptr,8); DV().setBigUint64(ptr, BigInt(value), true); }
 function toUtf8(str) {
   var result = [];
   // Probe only uses ASCII argv. Encode UTF-8 for completeness.
   var s = unescape(encodeURIComponent(str));
   for (var i=0;i<s.length;i++) result.push(s.charCodeAt(i));
   return result;
 }
 function bytesToText(ptr,n) {
   var b=check(ptr,n), out='';
   for(var i=0;i<n;i++) out+=String.fromCharCode(b[ptr+i]);
   return out;
 }
 function bytesToHex(ptr,n) {
   var b=check(ptr,n), out='',d='0123456789abcdef';
   for(var i=0;i<n;i++){ var v=b[ptr+i];out+=d[(v>>4)&15]+d[v&15]; }
   return out;
 }
 function hexToBytes(hex,ptr,limit) {
   if(hex.length%2 || hex.length/2>limit) throw Error('Invalid TCP hex reply');
   var b=check(ptr,hex.length/2);
   for(var i=0;i<hex.length;i+=2) { var v=parseInt(hex.substring(i,i+2),16); if(isNaN(v)) throw Error('Invalid TCP byte'); b[ptr+i/2]=v; }
   return hex.length/2;
 }
 function b64decode(s) {
   if(s.length % 4 !== 0) throw Error('Invalid Base64 length');
   var pad = s.length>0 && s.charAt(s.length-1)==='=' ? (s.charAt(s.length-2)==='='?2:1) : 0;
   var b=new Uint8Array((s.length/4)*3-pad), k=0;
   for(var i=0;i<s.length;i+=4){
     var a=digits.indexOf(s.charAt(i)),c=digits.indexOf(s.charAt(i+1));
     var d=s.charAt(i+2)==='='?0:digits.indexOf(s.charAt(i+2));
     var e=s.charAt(i+3)==='='?0:digits.indexOf(s.charAt(i+3));
     if(a<0 || c<0 || d<0 || e<0) throw Error('Invalid Base64 chunk');
     var n=(a<<18)|(c<<12)|(d<<6)|e;
     if(k<b.length)b[k++]=(n>>16)&255;
     if(k<b.length)b[k++]=(n>>8)&255;
     if(k<b.length)b[k++]=n&255;
   }
   return b;
 }
 function adler(b) {
   var a=1,c=0;
   for(var i=0;i<b.length;i++){ a=(a+b[i])%65521; c=(c+a)%65521; }
   return (((c<<16)>>>0)|a)>>>0;
 }
 function transfer(size, expectedAdler) {
   var arr=new Uint8Array(size), off=0;
   while(off<size){
     var count=Math.min(3072,size-off);
     var s=__python_chunk(off,count);
     var bb=b64decode(s);
     if(bb.length !== count) throw Error('Invalid decoded chunk at '+off+': '+bb.length+' expected '+count);
     arr.set(bb,off);off+=count;
   }
   if(adler(arr)!==(expectedAdler>>>0)) throw Error('WASM Adler32 mismatch');
   wasmBytes=arr;
   return 'PASS ('+size+' bytes, Adler32 verified)';
 }
 function setInput(size,expectedAdler) {
   if(size<1 || size>262144)throw Error('Invalid input length');
   var data=new Uint8Array(size),off=0;
   while(off<size){var n=Math.min(3072,size-off);var s=__python_input_chunk(off,n);var b=b64decode(s);
     if(b.length!==n)throw Error('Invalid input chunk');data.set(b,off);off+=n;}
   if(adler(data)!==(expectedAdler>>>0))throw Error('Request payload checksum mismatch');
   inputBytes=data;inputOffset=0;return 'PASS ('+size+' bytes)';
 }
 function hostCommand(cmd, a, b) { return __python_net(String(cmd),String(a===undefined?'':a),String(b===undefined?'':b)); }
 function tcp_connect(ptr,len) {
   var addr=bytesToText(ptr,len);
   return Number(hostCommand('C',addr));
 }
 function tcp_write(fd,ptr,len) {
   var n=Math.min(len,256);
   return Number(hostCommand('W',fd,bytesToHex(ptr,n)));
 }
 function tcp_read(fd,ptr,len) {
   var n=Math.min(len,256), rep=hostCommand('R',fd,n);
   if(rep==='~2') return -2;
   if(rep==='~1') return -1;
   return hexToBytes(rep,ptr,n);
 }
 function tcp_close(fd) { return Number(hostCommand('X',fd)); }
 var wasi = {
   args_sizes_get: function(pCount,pSize) {
     var total=0;for(var i=0;i<argv.length;i++) total+=toUtf8(argv[i]).length+1;
     put32(pCount,argv.length);put32(pSize,total);return 0;
   },
   args_get: function(pPtrs,pBuffer) {
     var at=pBuffer,b=U8();
     for(var i=0;i<argv.length;i++){
       var v=toUtf8(argv[i]);put32(pPtrs+i*4,at);check(at,v.length+1);
       for(var j=0;j<v.length;j++)b[at+j]=v[j];b[at+v.length]=0;at+=v.length+1;
     }
     return 0;
   },
   environ_sizes_get: function(pCount,pSize){put32(pCount,0);put32(pSize,0);return 0;},
   environ_get: function(){return 0;},
   fd_write: function(fd, pIovs, nIovs, pWritten) {
     var total=0;
     for(var i=0;i<nIovs;i++){var p=get32(pIovs+i*8), n=get32(pIovs+i*8+4); if(n>1048576)return 28;
       var s=bytesToText(p,n); if(fd===1||fd===2){output+=s;if(output.length>2097152)throw Error('Go output exceeded probe limit');}total+=n;
     }
     put32(pWritten,total);return 0;
   },
   fd_close: function(){return 8;},
   fd_read: function(fd,pIovs,nIovs,pRead){
     if(fd!==0)return 8; if(!inputBytes)throw Error('Input not set');
     var total=0;for(var i=0;i<nIovs;i++){
       var ptr=get32(pIovs+i*8),n=get32(pIovs+i*8+4);
       if(n>1048576)return 28;var k=Math.min(n,inputBytes.length-inputOffset);
       if(k>0)check(ptr,k).set(inputBytes.subarray(inputOffset,inputOffset+k),ptr);
       inputOffset+=k;total+=k;if(k<n)break;
     }put32(pRead,total);return 0;
   },
   fd_readdir: function(){return 8;},
   fd_filestat_get: function(){return 8;},
   path_filestat_get: function(){return 44;},
   path_readlink: function(){return 44;},
   path_open: function(){return 44;},
   fd_fdstat_get: function(fd,ptr){if(fd>2) return 8;var b=check(ptr,24);for(var j=0;j<24;j++)b[ptr+j]=0;b[ptr]=2;return 0;},
   fd_fdstat_set_flags: function(){return 0;},
   fd_prestat_get: function(){return 8;},
   fd_prestat_dir_name: function(){return 8;},
   clock_time_get: function(id,precision,pTime){put64(pTime,BigInt(Date.now())*1000000n);return 0;},
   random_get: function(ptr,n){
     if(n<0 || n>65536)return 28;
     var offset=0;
     while(offset<n){var count=Math.min(256,n-offset),hex=hostCommand('N',count);
       if(hex.length!==count*2)return 29;
       hexToBytes(hex,ptr+offset,count);offset+=count;
     }return 0;
   },
   sched_yield: function(){return 0;},
   poll_oneoff: function(pSubs,pEvents,count,pOut) {
     // Minimal clock/timer poll for Go's sleep runtime, which retries timeouts.
     if(count===0)return 28;
     var v=DV(), userdata=v.getBigUint64(pSubs,true), type=v.getUint8(pSubs+8);
     // For clock subscriptions, allow the wall clock to advance.
     var stop=Date.now()+1;while(Date.now()<stop){}
     check(pEvents,32);var mem=U8();for(var i=0;i<32;i++)mem[pEvents+i]=0;
     DV().setBigUint64(pEvents,userdata,true);DV().setUint16(pEvents+8,0,true);
     DV().setUint8(pEvents+10,type===0?0:type);
     put32(pOut,1);return 0;
   },
   proc_exit: function(code) {throw Error('__WASI_EXIT__'+code);}
 };
 function compile() {
   if(!wasmBytes)throw Error('No WASM bytes transferred');
   module=new WebAssembly.Module(wasmBytes);
   wasmBytes=null; // retain compiled module, drop the temporary 21MB transfer buffer
   return 'PASS ('+WebAssembly.Module.imports(module).length+' imports)';
 }
 function instantiate(){
   instance=null; memory=null; output='';
   if(!module)throw Error('Not compiled');
   instance = new WebAssembly.Instance(module,{wasi_snapshot_preview1:wasi,host:{
      tcp_connect:tcp_connect,tcp_write:tcp_write,tcp_read:tcp_read,tcp_close:tcp_close
   }});
   memory=instance.exports.memory;
   return 'PASS ('+memory.buffer.byteLength+' memory bytes)';
 }
 function start() {
   output=''; var code=0;
   try {instance.exports._start();}
   catch(e){
     var s=String(e);
     if(s.indexOf('__WASI_EXIT__')!==-1){code=Number(s.split('__WASI_EXIT__')[1]);}
     else throw e;
   }
   return 'EXIT '+code;
 }
 function stdoutLength(){return output.length;}
 function stdoutChunk(off,size){if(off<0 || size<0 || size>4096 || off>output.length)throw Error('invalid stdout chunk');return output.substring(off,off+size);}
 function releaseInstance(){instance=null;memory=null;inputBytes=null;inputOffset=0;output='';return 'RELEASED';}
 return {transfer:transfer,setInput:setInput,compile:compile,instantiate:instantiate,start:start,releaseInstance:releaseInstance,
         stdout:function(){return output;},stdoutLength:stdoutLength,stdoutChunk:stdoutChunk, imports:function(){return WebAssembly.Module.imports(module).length;}};
})();
