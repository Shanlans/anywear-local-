import Phaser from 'phaser';

const COLOR={control:0x4a7774,anywear:0x567952,queue:0xd99047,preview:0x9278ba,fit:0x487fa8};
const words={zh:{control:'未提供 Anywear',anywear:'提供 Anywear',racks:'商品区',fitting:'实体试衣间',
  mirror:'普通镜子',preview:'Anywear 预览',checkout:'收银',exit:'出口',window:'观察窗口'},
en:{control:'Without Anywear',anywear:'With Anywear',racks:'Catalogue',fitting:'Fitting rooms',
  mirror:'Ordinary mirror',preview:'Anywear preview',checkout:'Checkout',exit:'Exit',window:'Observation window'}};

export class StoreScene extends Phaser.Scene{
  state:any=null; language:'zh'|'en'='zh'; people=new Map<string,Phaser.GameObjects.Container>();
  labels:Phaser.GameObjects.Text[]=[]; board?:Phaser.GameObjects.Graphics;
  stations?:Phaser.GameObjects.Graphics; heat?:Phaser.GameObjects.Graphics;
  selected=''; showHeat=false; speed=1; follow=false; ready=false;
  onSelect:(world:string,agent:string)=>void;
  drag?:{x:number,y:number,sx:number,sy:number};
  constructor(onSelect:(world:string,agent:string)=>void){super('stores');this.onSelect=onSelect;}
  create(){
    this.board=this.add.graphics();this.heat=this.add.graphics();this.stations=this.add.graphics();
    this.cameras.main.setBounds(0,0,1120,430);
    this.input.on('pointerdown',(p:Phaser.Input.Pointer,objects:Phaser.GameObjects.GameObject[])=>{if(!objects.length)this.drag={x:p.x,y:p.y,sx:this.cameras.main.scrollX,sy:this.cameras.main.scrollY};});
    this.input.on('pointerup',()=>this.drag=undefined);
    this.input.on('pointermove',(p:Phaser.Input.Pointer)=>{if(this.drag&&p.isDown){this.cameras.main.scrollX=this.drag.sx-(p.x-this.drag.x)/this.cameras.main.zoom;this.cameras.main.scrollY=this.drag.sy-(p.y-this.drag.y)/this.cameras.main.zoom;}});
    this.ready=true;this.drawBoard();if(this.state)this.renderState(this.state);
  }
  xy(world:string,point:number[]){return {x:(world==='control'?26:584)+point[0]*15,y:66+point[1]*15};}
  text(x:number,y:number,text:string,size=12,color='#60736c'){
    const label=this.add.text(x,y,text,{fontFamily:'system-ui, sans-serif',fontSize:size,color});this.labels.push(label);return label;
  }
  drawBoard(){
    if(!this.ready)return;
    this.labels.forEach(t=>t.destroy());this.labels=[];const g=this.board!;g.clear();
    const lang=words[this.language];
    for(const world of ['control','anywear']){
      const left=world==='control'?16:574;const accent=COLOR[world as keyof typeof COLOR];
      g.fillStyle(0xfafbf6);g.fillRoundedRect(left,12,530,402,18);g.lineStyle(1,0xdce3d9);g.strokeRoundedRect(left,12,530,402,18);
      g.fillStyle(accent);g.fillRoundedRect(left+18,30,7,25,3);
      this.text(left+36,29,lang[world as 'control'|'anywear'],17,'#244238');
      this.text(left+36,52,world==='control'?'A · CONTROL':'B · TREATMENT',9);
      g.lineStyle(1,0xeef1e9,.8);
      for(let x=1;x<=32;x++){const p=this.xy(world,[x,1]);g.lineBetween(p.x,p.y,p.x,p.y+270);}
      for(let y=1;y<=19;y++){const p=this.xy(world,[1,y]);g.lineBetween(p.x,p.y,p.x+465,p.y);}
      for(let i=0;i<6;i++){
        const p=this.xy(world,[4+i*3,3]);g.fillStyle(0xe3e9df);g.fillRoundedRect(p.x,p.y,40,28,5);
        g.fillStyle(0xb8c9b8);g.fillRoundedRect(p.x+7,p.y+7,26,5,2);
        this.text(p.x+11,p.y+14,'S'+(i+1),9);
      }
      this.text(left+389,91,lang.fitting,9);
      const rack=this.xy(world,[5,2]);this.text(rack.x,rack.y-12,lang.racks,10);
      const mirror=this.xy(world,[6,10]);g.fillStyle(0xdcebea);g.fillRoundedRect(mirror.x,mirror.y,14,32,5);
      g.lineStyle(2,0xa3bfbb);g.strokeRoundedRect(mirror.x,mirror.y,14,32,5);
      this.text(mirror.x-12,mirror.y+39,lang.mirror,9);
      const preview=this.xy(world,[20,11]);
      if(world==='anywear'){
        g.fillStyle(0xe3dcef);g.fillRoundedRect(preview.x,preview.y,28,36,6);g.fillStyle(0xab95c5);g.fillRoundedRect(preview.x+6,preview.y+6,16,22,3);
        this.text(preview.x-18,preview.y+42,lang.preview,9,'#806496');
      }
      const checkout=this.xy(world,[25,16]);g.fillStyle(0xe1dfd0);g.fillRoundedRect(checkout.x,checkout.y,40,26,6);
      this.text(checkout.x-2,checkout.y+30,lang.checkout,9);
      const entrance=this.xy(world,[2,14]);this.text(entrance.x-6,entrance.y+20,lang.window,9);
      const exit=this.xy(world,[29,18]);this.text(exit.x-5,exit.y+18,lang.exit,9);
    }
  }
  setLanguage(language:'zh'|'en'){this.language=language;this.drawBoard();if(this.state)this.renderState(this.state);}
  renderState(state:any){
    this.state=state;if(!this.ready)return;
    const g=this.stations!;g.clear();this.heat!.clear();const visible=new Set<string>();
    for(const world of ['control','anywear']){
      const data=state.worlds[world];
      for(let i=0;i<data.resources.fitting.capacity;i++){
        const p=this.xy(world,[26+(Math.floor(i/4)*1.8),4+(i%4)*2]);
        g.fillStyle(data.resources.fitting.busy[String(i)]?0xc7dbe6:0xe4e9e2);
        g.fillRoundedRect(p.x,p.y,34,23,4);g.lineStyle(1,0xb8c8bc);g.strokeRoundedRect(p.x,p.y,34,23,4);
      }
      if(this.showHeat){const max=Math.max(1,...Object.values(data.heat) as number[]);
        for(const [key,count] of Object.entries(data.heat)){
          const p=this.xy(world,key.split(',').map(Number));this.heat!.fillStyle(0xd8a76b,Math.min(.55,(count as number)/max*.55));this.heat!.fillRect(p.x-7,p.y-7,14,14);
        }
      }
      for(const a of Object.values(data.agents) as any[]){
        if(a.status==='NOT_ARRIVED')continue;
        const key=world+'/'+a.id;visible.add(key);
        let pos=[...a.position];const terminal=['PURCHASED','LEFT','TIME_LIMIT','CENSORED'].includes(a.status);
        if(terminal){const index=Number(a.id.slice(1))-1;pos=[28+(index%7)*.42,18.2+Math.floor(index/7)*.045];}
        if(a.movement){const m=a.movement;const i=Math.min(m.path.length-1,Math.max(0,state.t-m.start));pos=m.path[Math.floor(i)];}
        if(a.queue){const queue=data.resources[a.queue.resource].queue;const i=queue.findIndex((q:any)=>q.agent===a.id);
          pos=a.queue.resource==='fitting'?[24-Math.floor(i/12)*.8,5+(i%12)*.65]:a.queue.resource==='preview'?[19,11+i*.6]:[24,17+i*.3];}
        const p=this.xy(world,pos);let marker=this.people.get(key);
        if(!marker){
          const color=Phaser.Display.Color.HSLToColor((Number(a.id.slice(1))*.137)%1,.28,.43).color;
          const shadow=this.add.ellipse(0,5,13,5,0x294137,.15);
          const body=this.add.circle(0,2,5.3,color);const head=this.add.circle(0,-3.4,3.2,0xead9bd);
          const status=this.add.circle(5,-5,2.3,0xffffff);marker=this.add.container(p.x,p.y,[shadow,body,head,status]);
          marker.setSize(19,21).setInteractive({useHandCursor:true});marker.on('pointerdown',()=>{this.selected=key;this.onSelect(world,a.id);});
          this.people.set(key,marker);
        }
        this.tweens.killTweensOf(marker);
        this.tweens.add({targets:marker,x:p.x,y:p.y,duration:450/this.speed,ease:'Sine.easeOut'});
        marker.setAlpha(terminal ? 0.28 : 1).setDepth(10+p.y/1000);
        const status=marker.list[3] as Phaser.GameObjects.Arc;
        status.setFillStyle(a.status.includes('QUEUED')?COLOR.queue:a.status==='PREVIEW'?COLOR.preview:a.status==='FITTING'?COLOR.fit:0xe9eee4);
        const body=marker.list[1] as Phaser.GameObjects.Arc;body.setStrokeStyle(key===this.selected?2:0,0x192f26);
        if(this.follow&&key===this.selected)this.cameras.main.centerOn(p.x,p.y);
      }
    }
    for(const [key,marker] of this.people)if(!visible.has(key)){marker.destroy();this.people.delete(key);}
  }
  zoom(delta:number){const camera=this.cameras.main;camera.setZoom(Phaser.Math.Clamp(camera.zoom+delta,1,2.5));}
  reset(){this.cameras.main.setZoom(1).setScroll(0,0);this.follow=false;}
}

export function createStoreGame(parent:HTMLElement,onSelect:(world:string,agent:string)=>void){
  const scene=new StoreScene(onSelect);
  const game=new Phaser.Game({type:Phaser.AUTO,parent,backgroundColor:'#edf1e8',width:1120,height:430,
    scene:[scene],scale:{mode:Phaser.Scale.FIT,autoCenter:Phaser.Scale.CENTER_BOTH},
    render:{antialias:true,roundPixels:false},fps:{target:60,forceSetTimeOut:false},banner:false});
  return {scene,game};
}
