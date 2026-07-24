document.addEventListener("DOMContentLoaded", () => {
  const form=document.getElementById("chatForm"); if(!form) return;
  const input=document.getElementById("chatInput"), messages=document.getElementById("chatMessages"), send=document.getElementById("sendButton"), stop=document.getElementById("stopButton"), status=document.getElementById("aiStatus"), pond=document.getElementById("pondSelect"), charCount=document.getElementById("charCount");
  let controller=null;
  const csrf=()=>form.querySelector("[name=csrfmiddlewaretoken]").value;
  const scroll=()=>{messages.scrollTop=messages.scrollHeight};
  function append(role,content=""){
    const row=document.createElement("div"); row.className=`ai-message ${role==="user"?"is-user":"is-assistant"}`;
    const avatar=document.createElement("div"); avatar.className="ai-avatar"; avatar.innerHTML=`<i class="fa-solid ${role==="user"?"fa-user":"fa-robot"}"></i>`;
    const body=document.createElement("div"); body.className="ai-message-body";
    const title=document.createElement("b"); title.textContent=role==="user"?"Anda":"Smart Shrimp AI";
    const text=document.createElement("div"); text.className="ai-message-text"; text.textContent=content;
    body.append(title,text); row.append(avatar,body); messages.append(row); scroll(); return text;
  }
  function parse(block){let event="message",data=[]; for(const line of block.split("\n")){if(line.startsWith("event:"))event=line.slice(6).trim();if(line.startsWith("data:"))data.push(line.slice(5).trim())} if(!data.length)return null; try{return{event,data:JSON.parse(data.join("\n"))}}catch(e){console.error("Paket SSE tidak valid",e);return null}}
  input.addEventListener("input",()=>charCount.textContent=input.value.length);
  input.addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();form.requestSubmit()}});
  stop.addEventListener("click",()=>controller?.abort());
  form.addEventListener("submit",async e=>{
    e.preventDefault(); const question=input.value.trim(); if(!question||controller)return;
    append("user",question); const answer=append("assistant",""); input.value="";charCount.textContent="0"; input.disabled=true;send.disabled=true;stop.hidden=false;status.textContent="Menganalisis"; controller=new AbortController();
    try{
      const response=await fetch(form.dataset.streamUrl,{method:"POST",headers:{"Content-Type":"application/json","X-CSRFToken":csrf()},body:JSON.stringify({message:question,pond_id:pond.value||null}),signal:controller.signal});
      if(!response.ok){let detail={};try{detail=await response.json()}catch(_e){}throw new Error(detail.error||`Permintaan gagal (${response.status})`)}
      if(!response.body)throw new Error("Browser tidak mendukung streaming.");
      const reader=response.body.getReader(), decoder=new TextDecoder("utf-8"); let buffer="",complete="";
      while(true){const {value,done}=await reader.read();if(done)break;buffer+=decoder.decode(value,{stream:true}).replace(/\r\n/g,"\n");const blocks=buffer.split("\n\n");buffer=blocks.pop()||"";for(const block of blocks){const packet=parse(block);if(!packet)continue;if(packet.event==="status")status.textContent=packet.data.message||"Menganalisis";if(packet.event==="token"){complete+=packet.data.content||"";answer.textContent=complete;scroll()}if(packet.event==="error")throw new Error(packet.data.message||"Kesalahan layanan AI");if(packet.event==="done")status.textContent="Selesai"}}
      if(!complete)answer.textContent="AI tidak menghasilkan jawaban.";
    }catch(error){if(error.name==="AbortError"){answer.textContent+=(answer.textContent?"\n\n":"")+"[Jawaban dihentikan]";status.textContent="Dihentikan"}else{answer.textContent=`Terjadi kesalahan: ${error.message}`;status.textContent="Gagal"}}
    finally{controller=null;input.disabled=false;send.disabled=false;stop.hidden=true;input.focus()}
  });
  scroll();
});