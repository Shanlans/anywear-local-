// A media connection is not an acknowledgement of the garment request.
export async function submitReference(connection,snapshot,current){
 const submitted=Object.freeze({...snapshot});
 await connection.set({image:submitted.blob,prompt:submitted.prompt,enhance:false});
 return current()?submitted:null;
}
