// Only a local SDP offer is created: no ICE server, media, credential or paid session.
export async function checkRealtimeSupport(environment=globalThis){
 let peer;
 try{
  if(typeof environment.RTCPeerConnection!=='function')return {ok:false,code:'WEBRTC_UNSUPPORTED'};
  peer=new environment.RTCPeerConnection({iceServers:[]});
  peer.addTransceiver('video',{direction:'recvonly'});
  const offer=await peer.createOffer();
  return offer?.sdp?{ok:true,code:'WEBRTC_READY'}:{ok:false,code:'WEBRTC_UNSUPPORTED'};
 }catch{return {ok:false,code:'WEBRTC_UNSUPPORTED'};}
 finally{peer?.close();}
}
