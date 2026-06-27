/* Cloudera AI — The Agentic Era : editable PPTX generator (pptxgenjs) */
const pptxgen = require("pptxgenjs");
const p = new pptxgen();
p.layout = "LAYOUT_16x9";            // 10" x 5.625"
p.author = "Cloudera";
p.title = "Cloudera AI — The Agentic Era";

/* ---- palette ---- */
const C = {
  navy:"15154A", navyDeep:"0D0D34", navyMid:"23236B",
  orange:"EE5A29", orangeS:"F6814F", oBg:"FFF3EE",
  peri:"4F4FF5", periS:"6E6EF7", pBg:"E9E9FE",
  grey:"5A5A72", line:"E2E2EC", soft:"F6F6FB", white:"FFFFFF",
  ice:"C9C9E6", iceDim:"9A9AC4", warn:"C8870B", warnBg:"FBF3E0", ok:"1FA971"
};
const F = { head:"Arial", body:"Calibri", mono:"Consolas" };
const W=10, H=5.625, MX=0.62;

const sq=()=>({type:"outer",color:"000000",blur:7,offset:2,angle:135,opacity:0.10});

/* ---- Cloudera square motif (top-right) ---- */
function squares(s, ox, oy, scale, alpha){
  const cells=[[3,0],[4,0],[6,0],[7,0],[2,1],[3,1],[5,1],[6,1],[7,1],
    [2,2],[3,2],[4,2],[6,2],[7,2],[2,3],[5,3],[6,3],[7,3],[3,4],[5,4],[6,4]];
  const cols=[C.peri,C.periS,"6E6EF7","4242E0"];
  const u=0.30*scale, g=0.055*scale;
  cells.forEach(([x,y],i)=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{
      x:ox+x*(u+g), y:oy+y*(u+g), w:u, h:u, rectRadius:0.06*scale,
      fill:{color:cols[i%4], transparency:alpha||0}, line:{type:"none"}
    });
  });
}

/* ---- wordmark ---- */
function wordmark(s, dark){
  s.addText([
    {text:"CLOUD", options:{}},
    {text:"E", options:{}},
    {text:"RA", options:{}}
  ],{ x:W-2.5, y:0.32, w:1.9, h:0.32, align:"right", margin:0,
      fontFace:F.head, fontSize:13, bold:true, charSpacing:3, color:C.orange });
}
/* ---- footer + page no ---- */
function chrome(s, n, dark, footNote){
  s.addText(footNote||"©2026 Cloudera, Inc. All Rights Reserved.",
    { x:MX, y:H-0.42, w:7.5, h:0.28, margin:0, fontFace:F.body, fontSize:8,
      color: dark?C.iceDim:"9A9AB4" });
  s.addText(`${n} / 22`, { x:W-1.3, y:H-0.42, w:0.7, h:0.28, align:"right", margin:0,
      fontFace:F.body, fontSize:8, color: dark?C.iceDim:"9A9AB4" });
}
/* ---- eyebrow + title header ---- */
function header(s, eyebrow, title, dark){
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:0.46,w:0.30,h:0.045,fill:{color:C.orange},line:{type:"none"}});
  s.addText(eyebrow.toUpperCase(),{x:MX+0.40,y:0.30,w:7,h:0.30,margin:0,fontFace:F.body,
    fontSize:10.5,bold:true,charSpacing:2,color:C.orange,valign:"middle"});
  s.addText(title,{x:MX,y:0.62,w:8.8,h:0.72,margin:0,fontFace:F.head,fontSize:27,bold:true,
    color: dark?C.white:C.navy});
}
/* ---- card ---- */
function card(s,x,y,w,h,opt={}){
  const dark=opt.dark;
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y,w,h,rectRadius:0.09,
    fill:{color: dark?C.navyMid:(opt.fill||C.white), transparency: dark?40:0},
    line:{color: dark?"3A3A7A":C.line, width:1}, shadow: dark?undefined:sq()});
  if(opt.edge){ s.addShape(p.shapes.RECTANGLE,{x,y,w:w,h:0.05,fill:{color:opt.edge},line:{type:"none"}});}
}
function pill(s,x,y,txt,fg,bg){
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y,w:Math.max(0.9,0.12+txt.length*0.072),h:0.28,
    rectRadius:0.14,fill:{color:bg},line:{type:"none"}});
  s.addText(txt,{x:x,y:y,w:Math.max(0.9,0.12+txt.length*0.072),h:0.28,align:"center",valign:"middle",
    margin:0,fontFace:F.body,fontSize:9,bold:true,color:fg});
}

/* ===================================================== SLIDE 1 — TITLE */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  // deep radial feel via overlay block
  s.addShape(p.shapes.RECTANGLE,{x:0,y:0,w:W,h:H,fill:{color:C.navyDeep,transparency:55},line:{type:"none"}});
  squares(s, 7.1, 0.0, 1.18, 5);
  s.addText([{text:"CLOUD",options:{}},{text:"E",options:{}},{text:"RA",options:{}}],
    {x:MX,y:0.7,w:4,h:0.5,margin:0,fontFace:F.head,fontSize:21,bold:true,charSpacing:4,color:C.orange});
  s.addText([{text:"Cloudera ",options:{color:C.white}},{text:"AI",options:{color:C.orange}}],
    {x:MX,y:2.0,w:8,h:1.0,margin:0,fontFace:F.head,fontSize:54,bold:true});
  s.addText("The Agentic Era",{x:MX,y:3.02,w:8,h:0.7,margin:0,fontFace:F.head,fontSize:32,color:C.ice});
  s.addText("The latest in the AI landscape — and the anatomy of the AI agent: tools, memory, and control.",
    {x:MX,y:3.95,w:5.2,h:0.8,margin:0,fontFace:F.body,fontSize:13.5,color:C.ice,lineSpacingMultiple:1.1});
  s.addText("JUNE 2026",{x:MX,y:4.8,w:3,h:0.3,margin:0,fontFace:F.body,fontSize:12,bold:true,charSpacing:3,color:C.orange});
})();

/* ===================================================== SLIDE 2 — AGENDA */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  const items=["The Latest in the AI Landscape","Cloudera AI — Architecture & Overview",
    "AI Studios","Hands-on Lab & Demos","Q & A"];
  let y=1.15; const rh=0.74;
  items.forEach((t,i)=>{
    s.addText(String(i+1),{x:MX,y:y,w:0.7,h:rh,margin:0,fontFace:F.head,fontSize:30,bold:true,color:C.orange,valign:"middle"});
    s.addText(t,{x:MX+0.9,y:y,w:7.4,h:rh,margin:0,fontFace:F.body,fontSize:18,bold:true,color:C.navy,valign:"middle"});
    s.addShape(p.shapes.LINE,{x:MX,y:y+rh,w:8.2,h:0,line:{color:C.line,width:1}});
    y+=rh;
  });
  chrome(s,2,false);
})();

/* ===================================================== SLIDE 3 — SECTION DIVIDER */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  squares(s, 7.55, 0.15, 0.78, 28);
  s.addText("“",{x:MX-0.1,y:0.3,w:1.5,h:1.2,margin:0,fontFace:"Georgia",fontSize:90,bold:true,color:C.orange});
  s.addText("The Latest in the AI Landscape",{x:MX,y:2.0,w:8.6,h:1.0,margin:0,fontFace:F.head,fontSize:36,bold:true,color:C.white});
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:3.05,w:0.9,h:0.05,fill:{color:C.orange},line:{type:"none"}});
  s.addText("From foundation models to autonomous agents — what changed, why it matters, and how to build for production.",
    {x:MX,y:3.3,w:7.2,h:0.8,margin:0,fontFace:F.body,fontSize:14,color:C.ice});
  chrome(s,3,true);
})();

/* ===================================================== SLIDE 4 — TIMELINE */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"GenAI & Agent Development","Four Years of Increasing Autonomy",false);
  const data=[
    {yr:"2023",tag:"FOUNDATION",bd:"BFBFE0",items:["First LLM deployments","Basic cluster setup","System integration"]},
    {yr:"2024",tag:"EXPANSION",bd:C.periS,items:["RAG at scale","Multimodal (VLM)","First agents"]},
    {yr:"2025",tag:"COMPLEXITY",bd:C.orangeS,items:["Reasoning agents","Deep data & API integration","Fine-tuning at scale"]},
    {yr:"2026",tag:"AUTONOMY",bd:C.orange,fill:C.oBg,items:["Self-correcting loops","MCP & “computer use”","Context & harness engineering"]}
  ];
  const top=1.55, ch=2.7, gap=0.2, cw=(8.76-3*gap)/4;
  data.forEach((d,i)=>{
    const x=MX+i*(cw+gap);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:top,w:cw,h:ch,rectRadius:0.09,fill:{color:d.fill||C.soft},line:{type:"none"},shadow:sq()});
    s.addShape(p.shapes.RECTANGLE,{x,y:top+ch-0.06,w:cw,h:0.06,fill:{color:d.bd},line:{type:"none"}});
    s.addText(d.yr,{x:x+0.18,y:top+0.18,w:cw-0.3,h:0.55,margin:0,fontFace:F.head,fontSize:24,bold:true,color:C.navy});
    s.addText(d.tag,{x:x+0.18,y:top+0.74,w:cw-0.3,h:0.28,margin:0,fontFace:F.body,fontSize:9.5,bold:true,charSpacing:1.5,color:C.grey});
    s.addText(d.items.map((t,k)=>({text:t,options:{bullet:{code:"2022"},breakLine:true,paraSpaceAfter:6}})),
      {x:x+0.18,y:top+1.12,w:cw-0.34,h:ch-1.2,margin:0,fontFace:F.body,fontSize:10.5,bold:true,color:C.navy,
       lineSpacingMultiple:1.0});
  });
  // autonomy bar
  const by=top+ch+0.18;
  s.addText("INCREASING AUTONOMY",{x:MX,y:by,w:2.6,h:0.3,margin:0,fontFace:F.body,fontSize:11,bold:true,charSpacing:1,color:C.orange,valign:"middle"});
  s.addShape(p.shapes.RECTANGLE,{x:MX+2.7,y:by+0.13,w:5.5,h:0.06,fill:{color:C.peri},line:{type:"none"}});
  s.addShape(p.shapes.RECTANGLE,{x:MX+6.5,y:by+0.13,w:1.7,h:0.06,fill:{color:C.orange},line:{type:"none"}});
  s.addText("→",{x:MX+8.2,y:by,w:0.5,h:0.3,margin:0,fontFace:F.head,fontSize:15,bold:true,color:C.orange,valign:"middle"});
  chrome(s,4,false);
})();

/* ===================================================== SLIDE 5 — YEAR OF THE AGENT */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Why Now","2025–26: The Years of the Agent",false);
  // left column
  s.addText([
    {text:"AI agents",options:{bold:true,color:C.navy}},
    {text:" are autonomous software systems that ",options:{}},
    {text:"reason, plan, and act",options:{bold:true,color:C.navy}},
    {text:" on behalf of users — orchestrating multi-step workflows and choosing their own course of action.",options:{}}
  ],{x:MX,y:1.6,w:4.1,h:1.3,margin:0,fontFace:F.body,fontSize:13,color:C.grey,lineSpacingMultiple:1.15});
  const li=[["Highly interactive; manage complex, multi-step tasks"],
            ["Apply reasoning to pick the best next action"],
            ["The leap from chatbot to autonomous operator"]];
  s.addText(li.map(t=>({text:t[0],options:{bullet:{code:"2022"},breakLine:true,paraSpaceAfter:8,color:C.grey}})),
    {x:MX,y:3.05,w:4.1,h:1.6,margin:0,fontFace:F.body,fontSize:12});
  // right column — 2 stat cards + warn card
  const rx=5.1, rw=4.28;
  // two stat cards
  card(s,rx,1.55,2.06,1.35,{edge:C.orange});
  s.addText("80%",{x:rx+0.16,y:1.72,w:1.8,h:0.6,margin:0,fontFace:F.head,fontSize:34,bold:true,color:C.orange});
  s.addText("of common customer-service issues resolved autonomously by 2029",{x:rx+0.16,y:2.30,w:1.78,h:0.5,margin:0,fontFace:F.body,fontSize:8.5,color:C.grey,lineSpacingMultiple:0.95});
  s.addText("Gartner, Nov 2024",{x:rx+0.16,y:2.74,w:1.78,h:0.18,margin:0,fontFace:F.body,fontSize:7,italic:true,color:"A6A6BC"});
  card(s,rx+2.22,1.55,2.06,1.35,{edge:C.peri});
  s.addText("~45%",{x:rx+2.38,y:1.72,w:1.8,h:0.6,margin:0,fontFace:F.head,fontSize:34,bold:true,color:C.peri});
  s.addText("AI-agent market CAGR through the early 2030s",{x:rx+2.38,y:2.30,w:1.78,h:0.5,margin:0,fontFace:F.body,fontSize:8.5,color:C.grey,lineSpacingMultiple:0.95});
  s.addText("Grand View / Precedence, 2025",{x:rx+2.38,y:2.74,w:1.78,h:0.18,margin:0,fontFace:F.body,fontSize:7,italic:true,color:"A6A6BC"});
  // warn card
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx,y:3.05,w:rw,h:1.55,rectRadius:0.09,fill:{color:C.warnBg},line:{type:"none"}});
  s.addShape(p.shapes.RECTANGLE,{x:rx,y:3.05,w:0.06,h:1.55,fill:{color:C.warn},line:{type:"none"}});
  s.addText("⚠  THE REALITY CHECK",{x:rx+0.2,y:3.18,w:rw-0.4,h:0.28,margin:0,fontFace:F.body,fontSize:10.5,bold:true,color:C.warn});
  s.addText([
    {text:"Only ",options:{}},{text:"2%",options:{bold:true,color:C.navy}},
    {text:" of orgs run agents at scale; ",options:{}},{text:"61%",options:{bold:true,color:C.navy}},
    {text:" are still exploring (Capgemini, 2025). Gartner expects ",options:{}},
    {text:">40%",options:{bold:true,color:C.navy}},
    {text:" of agentic-AI projects to be scrapped by 2027 — on cost, unclear value, and weak controls.",options:{}}
  ],{x:rx+0.2,y:3.5,w:rw-0.4,h:1.0,margin:0,fontFace:F.body,fontSize:10,color:C.grey,lineSpacingMultiple:1.08});
  chrome(s,5,false,"©2026 Cloudera, Inc. · Governed, enterprise-grade data is what separates the 2% from the 40%.");
})();

/* ===================================================== SLIDE 6 — SINGLE → MULTI (CONTROL) */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Control & Orchestration","From Single-Agent to Multi-Agent",false);
  const cy=1.55, ch=1.45, cw=4.26;
  // left card: ReAct
  card(s,MX,cy,cw,ch);
  pill(s,MX+0.18,cy+0.16,"SINGLE AGENT · ReAct",C.peri,C.pBg);
  const flow1=["Reason","Act (tool)","Observe","Reflect"];
  drawFlow(s,MX+0.18,cy+0.6,flow1,[1]);
  s.addText("One model loops — reason, call a tool, observe, self-correct — until the task is done.",
    {x:MX+0.18,y:cy+1.02,w:cw-0.36,h:0.4,margin:0,fontFace:F.body,fontSize:9.5,color:C.grey});
  // right card: multi
  const r2=MX+cw+0.24;
  card(s,r2,cy,cw,ch);
  pill(s,r2+0.18,cy+0.16,"MULTI-AGENT · Orchestrated",C.orange,C.oBg);
  drawFlow(s,r2+0.18,cy+0.6,["Planner","Researcher","Writer","Reviewer"],[0]);
  s.addText("Specialized agents coordinate via a planner, with feedback loops between roles.",
    {x:r2+0.18,y:cy+1.02,w:cw-0.36,h:0.4,margin:0,fontFace:F.body,fontSize:9.5,color:C.grey});
  // table
  const rows=[
    [{text:"Dimension",options:hd()},{text:"Single Agent (ReAct)",options:hd()},{text:"Multi-Agent (Orchestrated)",options:hd()}],
    [c("Coordination cost",1),c("None"),c("Role allocation + inter-agent comms")],
    [c("Failure mode",1),c("Single-point hallucination"),c("Cascading misunderstanding")],
    [c("Best for",1),c("Simple, linear toolchains"),c("Creativity · review · negotiation · parallelism")]
  ];
  s.addTable(rows,{x:MX,y:3.25,w:8.76,colW:[2.3,3.0,3.46],rowH:[0.34,0.36,0.36,0.36],
    fontFace:F.body,fontSize:10,valign:"middle",border:{type:"solid",color:C.line,pt:0.5}});
  chrome(s,6,false,"©2026 Cloudera, Inc. · Patterns: ReAct (Yao 2022), Reflexion (Shinn 2023); frameworks: LangGraph, AutoGen, CrewAI.");
})();
function hd(){return {fill:{color:C.orange},color:C.white,bold:true,fontFace:F.body,fontSize:10,valign:"middle",margin:3};}
function c(t,b){return {text:t,options:{color:b?C.navy:C.grey,bold:!!b,fontFace:F.body,fontSize:10,valign:"middle",margin:3,fill:{color:C.white}}};}
function drawFlow(s,x,y,nodes,oIdx){
  let cx=x;
  nodes.forEach((n,i)=>{
    const w=Math.max(0.85,0.2+n.length*0.072), isO=oIdx.includes(i);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:cx,y:y,w:w,h:0.34,rectRadius:0.06,
      fill:{color:isO?C.oBg:C.white},line:{color:isO?C.orange:C.line,width:1.2}});
    s.addText(n,{x:cx,y:y,w:w,h:0.34,align:"center",valign:"middle",margin:0,fontFace:F.body,fontSize:9,bold:true,color:C.navy});
    cx+=w;
    if(i<nodes.length-1){ s.addText("→",{x:cx,y:y,w:0.26,h:0.34,align:"center",valign:"middle",margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.orange}); cx+=0.26; }
  });
}

/* ===================================================== SLIDE 7 — AUTONOMY SHIFT */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  s.addShape(p.shapes.RECTANGLE,{x:0,y:0,w:W,h:H,fill:{color:C.navyDeep,transparency:60},line:{type:"none"}});
  squares(s,7.5,0.0,0.85,45);
  header(s,"2026","The Autonomy Shift",true);
  const cards=[
    ["Autonomous loops","Self-correcting reason–act–observe cycles replace rigid, human-coded decision trees."],
    ["MCP — “USB-C for AI”","The Model Context Protocol standardizes tool/data connections. Adopted by OpenAI & Google; donated to the Linux Foundation (Dec 2025)."],
    ["Universal “computer use”","Agents drive GUIs, browsers & keyboards like humans. Still hard: ~22% vs ~72% human on OSWorld."],
    ["Context engineering","Curating the token budget beats prompt-tweaking. Beware context rot — more tokens ≠ better."],
    ["“Harm over failure” risk","Stress tests (Anthropic Agentic Misalignment, Jun 2025) show models may act harmfully to avoid failure — in the lab, not yet in deployment."],
    ["→ The takeaway","More autonomy demands more governance: observability, guardrails, and human oversight.",true]
  ];
  const gx=MX, gy=1.5, gw=2.78, gh=1.42, gapx=0.21, gapy=0.18;
  cards.forEach((cd,i)=>{
    const col=i%3, row=Math.floor(i/3);
    const x=gx+col*(gw+gapx), y=gy+row*(gh+gapy);
    const accent=cd[2];
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y,w:gw,h:gh,rectRadius:0.08,
      fill:{color:accent?C.orange:C.navyMid, transparency:accent?78:40},
      line:{color:accent?C.orange:"3A3A7A",width:1}});
    s.addText(cd[0],{x:x+0.16,y:y+0.13,w:gw-0.32,h:0.34,margin:0,fontFace:F.head,fontSize:12.5,bold:true,color:accent?C.orangeS:C.white});
    s.addText(cd[1],{x:x+0.16,y:y+0.5,w:gw-0.32,h:gh-0.6,margin:0,fontFace:F.body,fontSize:9.5,color:C.ice,lineSpacingMultiple:1.05});
  });
  chrome(s,7,true);
})();

/* ===================================================== SLIDE 8 — ANATOMY */
(function(){
  const s=p.addSlide(); s.background={color:C.soft};
  wordmark(s);
  header(s,"Anatomy of an Agent","Three Things Make an Agent Work",false);
  const cards=[
    ["Tools",C.orange,"How the agent acts on the world — APIs, search, code execution, MCP servers. Tool design directly drives task accuracy."],
    ["Memory",C.peri,"How the agent remembers — factual, experiential, and working memory across a task and over time."],
    ["Control",C.orange,"How the agent decides — the reasoning loop and orchestration that turn a model into an operator."]
  ];
  const cw=2.78, gap=0.21, top=1.7, ch=2.5;
  cards.forEach((cd,i)=>{
    const x=MX+i*(cw+gap);
    card(s,x,top,cw,ch,{edge:cd[1]});
    s.addShape(p.shapes.OVAL,{x:x+0.2,y:top+0.28,w:0.5,h:0.5,fill:{color:cd[1],transparency:85},line:{color:cd[1],width:1.3}});
    s.addText(String(i+1),{x:x+0.2,y:top+0.28,w:0.5,h:0.5,align:"center",valign:"middle",margin:0,fontFace:F.head,fontSize:18,bold:true,color:cd[1]});
    s.addText(cd[0],{x:x+0.2,y:top+0.92,w:cw-0.4,h:0.4,margin:0,fontFace:F.head,fontSize:18,bold:true,color:C.navy});
    s.addText(cd[2],{x:x+0.2,y:top+1.4,w:cw-0.4,h:1.0,margin:0,fontFace:F.body,fontSize:11,color:C.grey,lineSpacingMultiple:1.1});
  });
  s.addText([{text:"Next: a closer look at ",options:{color:C.grey}},{text:"Tools",options:{bold:true,color:C.navy}},{text:" and ",options:{color:C.grey}},{text:"Memory",options:{bold:true,color:C.navy}},{text:".",options:{color:C.grey}}],
    {x:MX,y:top+ch+0.2,w:8.76,h:0.4,align:"center",margin:0,fontFace:F.body,fontSize:12.5});
  chrome(s,8,false);
})();

/* ===================================================== SLIDE 9 — TOOLS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"From chatbot to real AI agent","Tools Are Important",false);
  const rows=[
    [hc("Concept"),hc("The challenge"),hc("Best practice"),hc("Impact")],
    [tc("Tool descriptions",1),tc("Injected into the system prompt — easily overlooked"),tc("Treat as prompt engineering: clear, specific, 3–4 sentences, with examples"),tc("“The most important factor in tool performance”")],
    [tc("Overlapping tools",1),tc("Models confuse similar tools (Web vs Drive search)"),tc("Consolidate & use namespace_ prefixes; scope each tool"),tc("Removes a key failure mode")],
    [tc("Tool-use examples",1),tc("JSON Schema shows structure, not when/how"),tc("Provide input_examples (now an official field)"),tcA("72% → 90%","on complex params")],
    [tc("Progressive disclosure",1),tc("Preloading all tools floods context (up to 134K tokens)"),tc("Load on demand via the Tool Search Tool (GA Nov 2025)"),tcA("77K → 8.7K tokens","49% → 74% accuracy")]
  ];
  s.addTable(rows,{x:MX,y:1.5,w:8.76,colW:[1.7,2.5,2.66,1.9],rowH:[0.32,0.62,0.52,0.6,0.62],
    fontFace:F.body,fontSize:9,valign:"middle",border:{type:"solid",color:C.line,pt:0.5}});
  // bottom mini cards
  const mini=[["Programmatic tool calling","Claude calls tools from sandboxed code — fewer round-trips, ~37% fewer tokens."],
    ["MCP connector","Attach whole MCP servers (200+ tools) with defer_loading to protect the cache."],
    ["Strict tool use","strict:true guarantees calls match your schema exactly."]];
  const cw=2.78, gap=0.21, top=4.32, ch=0.78;
  mini.forEach((m,i)=>{
    const x=MX+i*(cw+gap);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:top,w:cw,h:ch,rectRadius:0.07,fill:{color:C.soft},line:{type:"none"}});
    s.addText(m[0],{x:x+0.14,y:top+0.08,w:cw-0.28,h:0.26,margin:0,fontFace:F.head,fontSize:10,bold:true,color:C.navy});
    s.addText(m[1],{x:x+0.14,y:top+0.34,w:cw-0.28,h:0.4,margin:0,fontFace:F.body,fontSize:8.3,color:C.grey,lineSpacingMultiple:0.97});
  });
  chrome(s,9,false,"©2026 Cloudera, Inc. · Source: Anthropic Engineering — “Advanced Tool Use” & “Writing Tools for Agents”.");
})();
function hc(t){return {text:t,options:{fill:{color:C.orange},color:C.white,bold:true,fontFace:F.body,fontSize:9.5,valign:"middle",margin:3}};}
function tc(t,b){return {text:t,options:{color:b?C.navy:C.grey,bold:!!b,fontFace:F.body,fontSize:9,valign:"middle",margin:3,fill:{color:C.white}}};}
function tcA(a,b){return {text:[{text:a+"\n",options:{bold:true,color:C.orange,fontSize:10}},{text:b,options:{color:C.grey,fontSize:8}}],options:{valign:"middle",margin:3,fill:{color:C.white},fontFace:F.body}};}

/* ===================================================== SLIDE 10 — MEMORY DOMAINS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Memory","Four Overlapping Domains",false);
  const cards=[
    ["Agent memory",C.peri,"Persistent, self-evolving cognitive state — integrates factual knowledge & past experience over time."],
    ["LLM memory",C.orange,"Architectural optimizations — context-window expansion, KV compression/reuse, long-context processing."],
    ["RAG",C.peri,"Static knowledge access — retrieving fixed information from external databases to augment responses."],
    ["Context engineering",C.orange,"Transient resource management — the prompt, tools & protocols set up for one temporary task."]
  ];
  const cw=2.04, gap=0.2, top=1.7, ch=2.7;
  cards.forEach((cd,i)=>{
    const x=MX+i*(cw+gap);
    card(s,x,top,cw,ch,{edge:cd[1]});
    s.addShape(p.shapes.OVAL,{x:x+0.18,y:top+0.26,w:0.34,h:0.34,fill:{color:cd[1]},line:{type:"none"}});
    s.addText(cd[0],{x:x+0.18,y:top+0.7,w:cw-0.36,h:0.7,margin:0,fontFace:F.head,fontSize:13,bold:true,color:C.navy});
    s.addText(cd[2],{x:x+0.18,y:top+1.42,w:cw-0.36,h:1.2,margin:0,fontFace:F.body,fontSize:9.5,color:C.grey,lineSpacingMultiple:1.08});
  });
  chrome(s,10,false);
})();

/* ===================================================== SLIDE 11 — MEMORY FUNCTIONS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Memory","Three Functions of Memory",false);
  const cards=[
    ["Factual (semantic)","Objective truths & general knowledge; helps the agent understand entities. Often in the model’s parametric memory."],
    ["Experiential (episodic)","Specific past events & interactions; stored in a vector DB; key to personalization & learning from mistakes."],
    ["Working","Temporary scratchpad for the current task — intermediate reasoning; cleared or promoted to long-term after."]
  ];
  const cw=2.78, gap=0.21, top=1.65, ch=1.85;
  cards.forEach((cd,i)=>{
    const x=MX+i*(cw+gap);
    card(s,x,top,cw,ch);
    s.addText(cd[0],{x:x+0.18,y:top+0.16,w:cw-0.36,h:0.34,margin:0,fontFace:F.head,fontSize:13,bold:true,color:C.navy});
    s.addText(cd[1],{x:x+0.18,y:top+0.56,w:cw-0.36,h:1.2,margin:0,fontFace:F.body,fontSize:10.5,color:C.grey,lineSpacingMultiple:1.1});
  });
  // experiential subtypes strip
  const ty=top+ch+0.2;
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:MX,y:ty,w:8.76,h:0.95,rectRadius:0.08,fill:{color:C.soft},line:{type:"none"}});
  s.addText("Experiential memory comes in flavors",{x:MX+0.2,y:ty+0.12,w:8.4,h:0.28,margin:0,fontFace:F.head,fontSize:11,bold:true,color:C.navy});
  drawFlow(s,MX+0.2,ty+0.5,["Case-based","Skill-based","Strategy-based","Hybrid"],[]);
  chrome(s,11,false);
})();

/* ===================================================== SLIDE 12 — RECENT MEMORY METHODS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Memory","Recent Memory Mechanisms",false);
  const rows=[
    [{text:"Feature",options:{fill:{color:C.peri},color:C.white,bold:true,fontFace:F.body,fontSize:11,margin:4,valign:"middle"}},
     {text:"LightMem",options:{fill:{color:C.peri},color:C.white,bold:true,fontFace:F.body,fontSize:11,margin:4,valign:"middle"}},
     {text:"MemSearch",options:{fill:{color:C.peri},color:C.white,bold:true,fontFace:F.body,fontSize:11,margin:4,valign:"middle"}}],
    mr("Primary goal","Token efficiency & prompt compression","Data transparency & easy auditing"),
    mr("Source of truth","Vector database (summaries)","Local .md files (full text)"),
    mr("Vector-DB role","Core persistent storage","Disposable search index"),
    mr("Update mechanism","“Sleep-time” offline summaries","Real-time file-watcher syncing"),
    mr("Best feature","Massive API cost/latency reduction","Git-friendly, editable memory files")
  ];
  s.addTable(rows,{x:MX,y:1.7,w:8.76,colW:[2.4,3.18,3.18],rowH:[0.4,0.5,0.5,0.5,0.5,0.5],
    fontFace:F.body,fontSize:10.5,valign:"middle",border:{type:"solid",color:C.line,pt:0.5}});
  chrome(s,12,false);
})();
function mr(a,b,c){return [
  {text:a,options:{color:C.navy,bold:true,fontFace:F.body,fontSize:10.5,margin:4,valign:"middle",fill:{color:C.white}}},
  {text:b,options:{color:C.grey,fontFace:F.body,fontSize:10.5,margin:4,valign:"middle",fill:{color:C.white}}},
  {text:c,options:{color:C.grey,fontFace:F.body,fontSize:10.5,margin:4,valign:"middle",fill:{color:C.soft}}}
];}

/* ===================================================== SLIDE 13 — PROMPT → HARNESS */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  s.addShape(p.shapes.RECTANGLE,{x:0,y:0,w:W,h:H,fill:{color:C.navyDeep,transparency:60},line:{type:"none"}});
  squares(s,7.5,0.0,0.8,50);
  header(s,"The Engineering Evolution","From Prompt to Harness Engineering",true);
  // evolution flow centered
  const fy=1.55;
  drawFlowDark(s,2.0,fy,["Prompt engineering","Context engineering","Harness engineering"],[2]);
  const cards=[
    ["1 · Tiered context","Structured layers feed the model only what it needs."],
    ["2 · Specialized roles","Sub-agents with focused jobs and clean contexts."],
    ["3 · Persistent memory","File-based state that survives the context window."],
    ["4 · Structured execution","Plan → execute → verify, with feedback loops & guardrails."]
  ];
  const cw=2.08, gap=0.2, top=2.35, ch=1.7;
  cards.forEach((cd,i)=>{
    const x=MX+i*(cw+gap);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:top,w:cw,h:ch,rectRadius:0.08,fill:{color:C.navyMid,transparency:40},line:{color:"3A3A7A",width:1}});
    s.addText(cd[0],{x:x+0.16,y:top+0.16,w:cw-0.32,h:0.5,margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.white});
    s.addText(cd[1],{x:x+0.16,y:top+0.66,w:cw-0.32,h:0.9,margin:0,fontFace:F.body,fontSize:9.5,color:C.ice,lineSpacingMultiple:1.05});
  });
  s.addText([{text:"Build the ",options:{color:C.ice}},{text:"stage",options:{bold:true,color:C.white}},{text:" on which the model performs — not just the line it reads.",options:{color:C.ice}}],
    {x:MX,y:top+ch+0.18,w:8.76,h:0.4,align:"center",margin:0,fontFace:F.body,fontSize:12});
  chrome(s,13,true);
})();
function drawFlowDark(s,x,y,nodes,oIdx){
  let cx=x;
  nodes.forEach((n,i)=>{
    const w=Math.max(1.6,0.3+n.length*0.085), isO=oIdx.includes(i);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:cx,y:y,w:w,h:0.44,rectRadius:0.07,
      fill:{color:isO?C.orange:C.navyMid,transparency:isO?0:30},line:{color:isO?C.orange:"3A3A7A",width:1.2}});
    s.addText(n,{x:cx,y:y,w:w,h:0.44,align:"center",valign:"middle",margin:0,fontFace:F.body,fontSize:11,bold:true,color:C.white});
    cx+=w;
    if(i<nodes.length-1){ s.addText("→",{x:cx,y:y,w:0.4,h:0.44,align:"center",valign:"middle",margin:0,fontFace:F.head,fontSize:16,bold:true,color:C.orange}); cx+=0.4; }
  });
}

/* ===================================================== SLIDE 14 — TAKEAWAYS */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  squares(s,7.7,0.05,0.68,42);
  s.addText("IN SUMMARY",{x:MX+0.40,y:0.45,w:5,h:0.3,margin:0,fontFace:F.body,fontSize:10.5,bold:true,charSpacing:2,color:C.orange});
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:0.55,w:0.30,h:0.045,fill:{color:C.orange},line:{type:"none"}});
  s.addText("Five Things to Remember",{x:MX,y:0.9,w:8.6,h:0.7,margin:0,fontFace:F.head,fontSize:30,bold:true,color:C.white});
  const pts=[
    ["2026 is about autonomy","self-correcting loops, MCP connectivity, and “computer use”."],
    ["Agents = Tools + Memory + Control","master all three to go from chatbot to operator."],
    ["Tool design is the highest-leverage work","clear descriptions & progressive disclosure move accuracy double digits."],
    ["Memory is multi-layered","factual, experiential, and working — with new transparent & efficient mechanisms."],
    ["Production needs governance","only 2% are at scale; the gap is data, controls, and oversight."]
  ];
  let y=1.85; const rh=0.66;
  pts.forEach((pt,i)=>{
    s.addShape(p.shapes.RECTANGLE,{x:MX,y:y+0.05,w:0.10,h:0.42,fill:{color:C.orange},line:{type:"none"}});
    s.addText([{text:pt[0]+" — ",options:{bold:true,color:C.white}},{text:pt[1],options:{color:C.ice}}],
      {x:MX+0.28,y:y,w:8.3,h:rh,margin:0,fontFace:F.body,fontSize:13.5,valign:"middle",lineSpacingMultiple:1.0});
    y+=rh;
  });
  chrome(s,14,true);
})();

/* ===================================================== SLIDE 15 — SECTION: HARNESS */
(function(){
  const s=p.addSlide(); s.background={color:C.navy};
  squares(s,7.55,0.15,0.78,28);
  s.addText('"',{x:MX-0.1,y:0.3,w:1.5,h:1.2,margin:0,fontFace:"Georgia",fontSize:90,bold:true,color:C.orange});
  s.addText("Harness Engineering",{x:MX,y:2.0,w:8.6,h:0.9,margin:0,fontFace:F.head,fontSize:36,bold:true,color:C.white});
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:2.97,w:0.9,h:0.05,fill:{color:C.orange},line:{type:"none"}});
  s.addText("Intelligence is no longer the bottleneck. The new paradigm: build the environment that lets agents run reliably at scale.",
    {x:MX,y:3.22,w:7.2,h:0.8,margin:0,fontFace:F.body,fontSize:14,color:C.ice,lineSpacingMultiple:1.1});
  chrome(s,15,true);
})();

/* ===================================================== SLIDE 16 — BOTTLENECK IS INFRA */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"The Core Insight","The Bottleneck Is Infrastructure, Not Intelligence",false);
  const top=1.55, ch=2.65, hw=4.2, gap=0.36;
  // left: expectation
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:MX,y:top,w:hw,h:ch,rectRadius:0.09,
    fill:{color:"FFF4F1"},line:{color:C.orange,width:1.5}});
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:top,w:hw,h:0.05,fill:{color:C.orange},line:{type:"none"}});
  s.addText("THE EXPECTATION",{x:MX+0.2,y:top+0.16,w:hw-0.4,h:0.28,margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.orange});
  s.addText("Focusing purely on Model Intelligence",{x:MX+0.2,y:top+0.44,w:hw-0.4,h:0.24,margin:0,fontFace:F.body,fontSize:10,color:C.grey});
  s.addText([
    {text:"Power without route: ",options:{bold:true}},{text:"untethered capability, zero system integration. Potential trapped.\n",options:{}},
    {text:"MODEL_STATUS: ISOLATED_ENGINE  //  UTILIZATION: 0.0%",options:{color:C.orange,fontFace:F.mono,fontSize:8.5}}
  ],{x:MX+0.2,y:top+0.82,w:hw-0.4,h:1.7,margin:0,fontFace:F.body,fontSize:10,color:C.grey,lineSpacingMultiple:1.1});
  // right: reality
  const rx=MX+hw+gap;
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx,y:top,w:hw,h:ch,rectRadius:0.09,
    fill:{color:"F1FBF5"},line:{color:C.ok,width:1.5}});
  s.addShape(p.shapes.RECTANGLE,{x:rx,y:top,w:hw,h:0.05,fill:{color:C.ok},line:{type:"none"}});
  s.addText("THE REALITY",{x:rx+0.2,y:top+0.16,w:hw-0.4,h:0.28,margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.ok});
  s.addText("Focusing on System Infrastructure (Harness)",{x:rx+0.2,y:top+0.44,w:hw-0.4,h:0.24,margin:0,fontFace:F.body,fontSize:10,color:C.grey});
  s.addText([
    {text:"Can.ac benchmark: ",options:{bold:true,color:C.navy}},{text:"6.7% → 68.3%",options:{bold:true,color:C.ok}},{text:" by changing harness tool formats only — zero model changes.\n",options:{}},
    {text:"LangChain Terminal Bench 2.0: ",options:{bold:true,color:C.navy}},{text:"30th → 5th place (+13.7 pts)",options:{bold:true,color:C.ok}},{text:" purely through environmental constraints.",options:{}}
  ],{x:rx+0.2,y:top+0.82,w:hw-0.4,h:1.7,margin:0,fontFace:F.body,fontSize:10,color:C.grey,lineSpacingMultiple:1.25});
  chrome(s,16,false,"©2026 Cloudera, Inc. All Rights Reserved. · Empirical proof: harness adjustments alone, zero model weight changes.");
})();

/* ===================================================== SLIDE 17 — THREE ERAS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"The Engineering Evolution","The Three Eras of AI Engineering",false);
  const cols=[
    {label:"PROMPT ENGINEERING",q:"How do I ask?",meta:"Chatbot",bn:"Input expression",fix:"Chain-of-Thought, Few-Shot",active:false},
    {label:"CONTEXT ENGINEERING",q:"What do I show?",meta:"The Researcher (RAG)",bn:"Window overload",fix:"Vector search, Tool calling",active:false},
    {label:"HARNESS ENGINEERING",q:"How does it run?",meta:"Autonomous Worker",bn:"Environmental constraints",fix:"Execution loops, Memory, State",active:true}
  ];
  const cw=2.78,gap=0.21,top=1.55,ch=3.38;
  cols.forEach((c2,i)=>{
    const x=MX+i*(cw+gap), active=c2.active;
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:top,w:cw,h:ch,rectRadius:0.09,
      fill:{color:active?C.pBg:C.soft},line:{color:active?C.peri:C.line,width:active?2:1},
      shadow:sq()});
    s.addText(c2.label,{x:x+0.18,y:top+0.14,w:cw-0.36,h:0.42,margin:0,fontFace:F.head,fontSize:10.5,bold:true,
      color:active?C.peri:C.grey,charSpacing:0.5});
    s.addText("CORE QUESTION:",{x:x+0.18,y:top+0.62,w:cw-0.36,h:0.2,margin:0,fontFace:F.mono,fontSize:8,color:C.grey});
    s.addText(c2.q,{x:x+0.18,y:top+0.83,w:cw-0.36,h:0.34,margin:0,fontFace:F.head,fontSize:16,bold:true,color:active?C.navy:C.navy});
    s.addShape(p.shapes.RECTANGLE,{x:x+0.18,y:top+1.22,w:cw-0.36,h:0.02,fill:{color:C.line},line:{type:"none"}});
    s.addText("SYSTEM METAPHOR:",{x:x+0.18,y:top+1.3,w:cw-0.36,h:0.2,margin:0,fontFace:F.mono,fontSize:7.5,color:C.grey});
    s.addText(c2.meta,{x:x+0.18,y:top+1.5,w:cw-0.36,h:0.3,margin:0,fontFace:F.body,fontSize:10.5,bold:true,color:C.navy});
    s.addText("PRIMARY BOTTLENECK:",{x:x+0.18,y:top+1.88,w:cw-0.36,h:0.2,margin:0,fontFace:F.mono,fontSize:7.5,color:C.grey});
    s.addText(c2.bn,{x:x+0.18,y:top+2.08,w:cw-0.36,h:0.3,margin:0,fontFace:F.body,fontSize:10.5,bold:true,color:C.navy});
    s.addText("→  THE FIX:",{x:x+0.18,y:top+2.46,w:cw-0.36,h:0.2,margin:0,fontFace:F.mono,fontSize:7.5,color:active?C.peri:C.grey});
    s.addText(c2.fix,{x:x+0.18,y:top+2.66,w:cw-0.36,h:0.55,margin:0,fontFace:F.body,fontSize:10,bold:active,color:active?C.peri:C.navy});
  });
  chrome(s,17,false);
})();

/* ===================================================== SLIDE 18 — FOUR PILLARS */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Harness Engineering","The Four Pillars of a Production Harness",false);
  const pillars=[
    {n:"1",title:"Progressive Context Architecture",rule:"Give the agent only what it needs for this step.",
     tiers:["Tier 1 Always-On: AGENTS.md, project structure, dynamic feedback loop",
            "Tier 2 On-Demand: loaded by active skills & sub-agent roles",
            "Tier 3 Cold Storage: vector DBs, full codebase — queried via tools"]},
    {n:"2",title:"Agent Specialization & Parallelism",rule:"Focused agents with restricted toolsets outperform generalist 'god-mode' agents.",
     tiers:["Planner Agent: read-only (Grep, Glob) → outputs structural JSON plan",
            "Execution Agent: scoped write access, parallelizes tool calls",
            "Review Agent: read + flag access, critiques against the JSON plan"]},
    {n:"3",title:"Persistent Memory & State",rule:"Memory lives in the file system, not the prompt window.",
     tiers:["Boot → read git log → find next task via progress.json",
            "Execute → record state back to progress.json after every step",
            "Failure mode: 'one-shot' attempts lose context and declare premature victory"]},
    {n:"4",title:"Structured Execution & Backpressure",rule:"If a rule cannot be enforced mechanically, the agent will eventually deviate.",
     tiers:["Upstream: custom linters & ArchUnit guide before execution",
            "Downstream: CI/CD & browser tests reject invalid outputs",
            "Self-correction loop: reject → retry, separate thinking from execution"]}
  ];
  const cw=2.08,gap=0.20,top=1.52,ch=3.45;
  pillars.forEach((pl,i)=>{
    const x=MX+i*(cw+gap);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:top,w:cw,h:ch,rectRadius:0.09,fill:{color:C.soft},line:{type:"none"},shadow:sq()});
    s.addShape(p.shapes.OVAL,{x:x+0.18,y:top+0.18,w:0.40,h:0.40,fill:{color:C.peri},line:{type:"none"}});
    s.addText(pl.n,{x:x+0.18,y:top+0.18,w:0.40,h:0.40,align:"center",valign:"middle",margin:0,fontFace:F.head,fontSize:16,bold:true,color:C.white});
    s.addText(pl.title,{x:x+0.18,y:top+0.70,w:cw-0.36,h:0.56,margin:0,fontFace:F.head,fontSize:11,bold:true,color:C.navy,lineSpacingMultiple:0.97});
    s.addShape(p.shapes.RECTANGLE,{x:x+0.18,y:top+1.3,w:cw-0.36,h:0.02,fill:{color:C.line},line:{type:"none"}});
    s.addText("RULE: "+pl.rule,{x:x+0.18,y:top+1.37,w:cw-0.36,h:0.6,margin:0,fontFace:F.body,fontSize:8.5,color:C.orange,bold:true,lineSpacingMultiple:0.95});
    s.addText(pl.tiers.map((t,k)=>({text:t,options:{bullet:{code:"2022"},breakLine:true,paraSpaceAfter:5}})),
      {x:x+0.18,y:top+2.02,w:cw-0.36,h:1.3,margin:0,fontFace:F.body,fontSize:8,color:C.grey,lineSpacingMultiple:0.95});
  });
  chrome(s,18,false);
})();

/* ===================================================== SLIDE 19 — CONTEXT PARADOX + SMART ZONE */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Context Engineering","The Context Paradox: More Info ≠ More Intelligence",false);
  // smart/dumb zone diagram
  const bx=MX,by=1.55,bw=5.5,bh=3.1;
  // green zone
  s.addShape(p.shapes.RECTANGLE,{x:bx,y:by,w:bw*0.4,h:bh,fill:{color:"E8F5EE"},line:{type:"none"}});
  // orange zone
  s.addShape(p.shapes.RECTANGLE,{x:bx+bw*0.4,y:by,w:bw*0.6,h:bh,fill:{color:"FEF3E2"},line:{type:"none"}});
  // dashed divider
  s.addShape(p.shapes.LINE,{x:bx+bw*0.4,y:by,w:0,h:bh,line:{color:"9A9AB4",width:1.5,dashType:"dash"}});
  s.addText("THE SMART ZONE (0–40%)",{x:bx+0.14,y:by+0.16,w:bw*0.38,h:0.28,margin:0,fontFace:F.body,fontSize:10,bold:true,color:C.ok});
  s.addText("Focused & accurate reasoning.\nHigh signal-to-noise.",{x:bx+0.14,y:by+0.46,w:bw*0.38,h:0.52,margin:0,fontFace:F.body,fontSize:9,color:C.grey,lineSpacingMultiple:1.0});
  s.addText("THE DUMB ZONE (40–100%)",{x:bx+bw*0.42,y:by+0.16,w:bw*0.56,h:0.28,margin:0,fontFace:F.body,fontSize:10,bold:true,color:C.warn});
  s.addText("Hallucinations, infinite loops, context overload.\nReasoning quality collapses.",{x:bx+bw*0.42,y:by+0.46,w:bw*0.56,h:0.52,margin:0,fontFace:F.body,fontSize:9,color:C.grey,lineSpacingMultiple:1.0});
  // curve approximation via overlapping ellipses
  s.addShape(p.shapes.LINE,{x:bx+0.1,y:by+2.4,w:bw*0.35,h:-1.5,line:{color:C.ok,width:2.5}});
  s.addShape(p.shapes.LINE,{x:bx+bw*0.38,y:by+0.9,w:bw*0.6-0.1,h:1.8,line:{color:C.warn,width:2.5}});
  // x-axis
  s.addText("CONTEXT WINDOW FILLED",{x:bx,y:by+bh-0.22,w:bw,h:0.2,align:"center",margin:0,fontFace:F.mono,fontSize:8,color:C.grey});
  const pcts=["0%","20%","40%","60%","80%","100%"];
  pcts.forEach((t,i)=>s.addText(t,{x:bx+i*(bw/5)-0.15,y:by+bh-0.42,w:0.35,h:0.18,align:"center",margin:0,fontFace:F.mono,fontSize:7,color:C.grey}));
  // right column: insight cards
  const rx=bx+bw+0.28, rw=3.56;
  card(s,rx,by,rw,0.84,{fill:C.warnBg});
  s.addShape(p.shapes.RECTANGLE,{x:rx,y:by,w:rw,h:0.05,fill:{color:C.warn},line:{type:"none"}});
  s.addText("INDUSTRY CONSENSUS",{x:rx+0.16,y:by+0.1,w:rw-0.32,h:0.22,margin:0,fontFace:F.body,fontSize:9,bold:true,color:C.warn});
  s.addText("Context > 40% degrades reasoning. Constraints must be mechanical.",{x:rx+0.16,y:by+0.34,w:rw-0.32,h:0.44,margin:0,fontFace:F.body,fontSize:9,color:C.grey,lineSpacingMultiple:0.97});
  const fixes=[
    ["Progressive loading","Tool Search Tool, defer_loading — don't preload everything"],
    ["Context compaction","Summarize conversation mid-run before limits are hit"],
    ["Sub-agents","Each sub-agent gets a fresh, clean context window"],
    ["Structured notes","Write progress.json — memory outside the prompt"]
  ];
  let fy=by+0.98;
  fixes.forEach(f=>{
    card(s,rx,fy,rw,0.49,{fill:C.soft});
    s.addText(f[0],{x:rx+0.16,y:fy+0.06,w:rw-0.32,h:0.2,margin:0,fontFace:F.head,fontSize:9.5,bold:true,color:C.navy});
    s.addText(f[1],{x:rx+0.16,y:fy+0.26,w:rw-0.32,h:0.2,margin:0,fontFace:F.body,fontSize:8.5,color:C.grey});
    fy+=0.56;
  });
  chrome(s,19,false,"©2026 Cloudera, Inc. All Rights Reserved. · Source: Harness Engineering PDF; context degradation is a practitioner-community consensus, not a single paper.");
})();

/* ===================================================== SLIDE 20 — AGENTIC LOOP EVALS + MATURITY */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Evaluating & Operating Agents","Loop Evals, Observability & the Maturity Model",false);
  // left: eval benchmarks table
  s.addText("Key Agentic Eval Benchmarks",{x:MX,y:1.52,w:4.5,h:0.28,margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.navy});
  const rows=[
    [hc2("Benchmark"),hc2("What it tests")],
    [tc2("SWE-bench Verified",1),tc2("Real GitHub issues solved end-to-end (2294 tasks)")],
    [tc2("τ-bench",1),tc2("Tool-agent in retail/airline environments; pass^k metric")],
    [tc2("GAIA",1),tc2("Multi-step real-world web tasks; human ~92% vs AI ~15-30%")],
    [tc2("WebArena",1),tc2("Browser automation across e-commerce, reddit, gitlab")],
    [tc2("AgentBench",1),tc2("8 environments: OS, DB, web, code — measures task success rate")]
  ];
  s.addTable(rows,{x:MX,y:1.86,w:4.5,colW:[1.7,2.8],rowH:[0.30,0.44,0.44,0.44,0.44,0.44],
    fontFace:F.body,fontSize:8.5,valign:"middle",border:{type:"solid",color:C.line,pt:0.5}});
  // right: maturity model + observability
  const rx=MX+4.76, rw=4.0;
  s.addText("Harness Maturity Model",{x:rx,y:1.52,w:rw,h:0.28,margin:0,fontFace:F.head,fontSize:12,bold:true,color:C.navy});
  const levels=[
    {l:"L0",t:"Raw Interaction",d:"Direct prompts, manual coding, zero constraints",c:C.grey},
    {l:"L1",t:"Basic Constraints",d:"AGENTS.md, basic linters, manual testing",c:C.warn},
    {l:"L2",t:"Feedback Loops",d:"CI/CD, automated tests, progress.json state tracking",c:C.peri},
    {l:"L3",t:"Specialization",d:"Multi-agent routing, progressive context, role definitions",c:C.orangeS},
    {l:"L4",t:"Autonomy",d:"Unattended parallel execution, automated entropy management, self-healing",c:C.ok}
  ];
  let ly=1.86; const lh=0.54, lw=rw;
  levels.forEach((lv,i)=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx,y:ly,w:lw,h:lh,rectRadius:0.06,
      fill:{color:C.white},line:{color:C.line,width:1}});
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx,y:ly,w:0.48,h:lh,rectRadius:0.06,
      fill:{color:lv.c},line:{type:"none"}});
    s.addText(lv.l,{x:rx,y:ly,w:0.48,h:lh,align:"center",valign:"middle",margin:0,fontFace:F.head,fontSize:11,bold:true,color:C.white});
    s.addText(lv.t,{x:rx+0.58,y:ly+0.06,w:lw-0.68,h:0.22,margin:0,fontFace:F.head,fontSize:10,bold:true,color:C.navy});
    s.addText(lv.d,{x:rx+0.58,y:ly+0.28,w:lw-0.68,h:0.22,margin:0,fontFace:F.body,fontSize:8,color:C.grey});
    ly+=lh+0.02;
  });
  // observability strip at bottom
  const obs=[["LangSmith","LangChain tracing"],["Langfuse","Open-source LLM ops"],["Arize Phoenix","Evals + tracing"],["OTel GenAI","GenAI conventions"]];
  const ow=2.04, ogap=0.18, ox=MX;
  s.addShape(p.shapes.RECTANGLE,{x:MX,y:5.08,w:8.76,h:0.02,fill:{color:C.line},line:{type:"none"}});
  s.addText("Observability stack:",{x:MX,y:5.13,w:1.4,h:0.22,margin:0,fontFace:F.body,fontSize:8.5,bold:true,color:C.grey,valign:"middle"});
  obs.forEach((o,i)=>{
    const bx=MX+1.55+i*(ow*0.78+0.18);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:bx,y:5.1,w:ow*0.78,h:0.26,rectRadius:0.05,fill:{color:C.soft},line:{type:"none"}});
    s.addText(o[0]+" — "+o[1],{x:bx+0.06,y:5.1,w:ow*0.78-0.12,h:0.26,margin:0,valign:"middle",fontFace:F.body,fontSize:7.5,color:C.navy});
  });
  chrome(s,20,false,"©2026 Cloudera, Inc. All Rights Reserved. · Benchmarks: SWE-bench, τ-bench, GAIA, WebArena, AgentBench. Maturity model: Harness Engineering PDF.");
})();
function hc2(t){return {text:t,options:{fill:{color:C.peri},color:C.white,bold:true,fontFace:F.body,fontSize:9,valign:"middle",margin:3}};}
function tc2(t,b){return {text:t,options:{color:b?C.navy:C.grey,bold:!!b,fontFace:F.body,fontSize:8.5,valign:"middle",margin:3,fill:{color:C.white}}};}

/* ===================================================== SLIDE 21 — CLOUDERA AI AGENT STUDIO */
(function(){
  const s=p.addSlide(); s.background={color:C.white};
  wordmark(s);
  header(s,"Cloudera AI","Cloudera Agent Studio 3.0",false);
  // left: headline + capabilities
  const lw=4.6;
  s.addText("A flexible low-code to high-code platform to create AI agents, tools, and multi-agent workflows — all through an intuitive UI.",
    {x:MX,y:1.58,w:lw,h:0.72,margin:0,fontFace:F.head,fontSize:13,color:C.peri,bold:true,lineSpacingMultiple:1.05});
  const caps=[
    ["Agentic workflow builder","Create agents with tasks, tools & roles; AI-assisted authoring"],
    ["Tools Catalog","Built-in, custom Python, and MCP server tools — all reusable across workflows"],
    ["Multi-LLM support","CAI Inferencing, Azure OpenAI, Gemini, Anthropic, any OpenAI-compatible endpoint"],
    ["Test & debug","Logs, playback, and visual debugger in the Test panel"],
    ["Deploy as endpoint","Auto-generated UI; deploy workflows as APIs with one click"],
    ["Built-in observability","Phoenix (Arize) tracing integrated; monitor every agent run"],
    ["Guardrails","Secure workflows with configurable safety constraints"]
  ];
  let cy=2.44; const rh=0.375, cw2=lw;
  caps.forEach(c2=>{
    s.addShape(p.shapes.RECTANGLE,{x:MX,y:cy+0.08,w:0.06,h:0.28,fill:{color:C.orange},line:{type:"none"}});
    s.addText(c2[0],{x:MX+0.18,y:cy+0.05,w:cw2-0.2,h:0.20,margin:0,fontFace:F.head,fontSize:10,bold:true,color:C.navy});
    s.addText(c2[1],{x:MX+0.18,y:cy+0.23,w:cw2-0.2,h:0.18,margin:0,fontFace:F.body,fontSize:8.5,color:C.grey});
    cy+=rh;
  });
  // right: architecture diagram (simplified as shapes)
  const rx=MX+lw+0.3, rw2=3.86, ry=1.52;
  // outer box
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx,y:ry,w:rw2,h:3.6,rectRadius:0.10,
    fill:{color:C.soft},line:{color:C.line,width:1.5}});
  s.addText("AGENT STUDIO",{x:rx+0.2,y:ry+0.14,w:rw2-0.4,h:0.28,align:"center",margin:0,
    fontFace:F.head,fontSize:11,bold:true,charSpacing:1.5,color:C.navy});
  // three agent boxes
  const aw=1.08, ah=0.44, ax=[rx+0.18,rx+1.38,rx+2.58], ay=ry+0.58;
  ax.forEach((x,i)=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x,y:ay,w:aw,h:ah,rectRadius:0.07,
      fill:{color:i===1?C.pBg:C.white},line:{color:C.peri,width:1}});
    s.addText("Agent "+(i+1),{x,y:ay,w:aw,h:ah,align:"center",valign:"middle",margin:0,
      fontFace:F.body,fontSize:9,bold:true,color:C.peri});
    // tool tags
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:x+0.04,y:ay+0.52,w:0.46,h:0.26,rectRadius:0.04,
      fill:{color:C.oBg},line:{type:"none"}});
    s.addText("Tool 1",{x:x+0.04,y:ay+0.52,w:0.46,h:0.26,align:"center",valign:"middle",margin:0,
      fontFace:F.body,fontSize:7.5,color:C.orange});
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:x+0.58,y:ay+0.52,w:0.46,h:0.26,rectRadius:0.04,
      fill:{color:C.oBg},line:{type:"none"}});
    s.addText("Tool 2",{x:x+0.58,y:ay+0.52,w:0.46,h:0.26,align:"center",valign:"middle",margin:0,
      fontFace:F.body,fontSize:7.5,color:C.orange});
  });
  // task flow
  const tasks=["Task 1","Task 2","Task 3"];
  const ty=ry+1.55, tw=0.86;
  tasks.forEach((t,i)=>{
    const tx=rx+0.28+i*(tw+0.28);
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:tx,y:ty,w:tw,h:0.34,rectRadius:0.06,
      fill:{color:C.navy},line:{type:"none"}});
    s.addText(t,{x:tx,y:ty,w:tw,h:0.34,align:"center",valign:"middle",margin:0,
      fontFace:F.body,fontSize:9,bold:true,color:C.white});
    if(i<2){ s.addText("→",{x:tx+tw,y:ty,w:0.28,h:0.34,align:"center",valign:"middle",margin:0,
      fontFace:F.head,fontSize:10,bold:true,color:C.orange}); }
  });
  // test/deploy bar
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:rx+0.2,y:ry+2.1,w:rw2-0.4,h:0.36,rectRadius:0.07,
    fill:{color:C.navyMid,transparency:30},line:{type:"none"}});
  s.addText("Test  |  Deploy  |  Observe",{x:rx+0.2,y:ry+2.1,w:rw2-0.4,h:0.36,align:"center",
    valign:"middle",margin:0,fontFace:F.body,fontSize:10,bold:true,color:C.white});
  // form factor badges
  const badges=["Private Cloud GA (PVC 1.5.5-SP3)","Public Cloud (AWS, Azure — TP)"];
  let bx=rx+0.2, bw3=(rw2-0.6)/2;
  badges.forEach((b,i)=>{
    s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:bx+i*(bw3+0.18),y:ry+2.62,w:bw3,h:0.38,rectRadius:0.07,
      fill:{color:i===0?C.pBg:C.oBg},line:{type:"none"}});
    s.addText(b,{x:bx+i*(bw3+0.18),y:ry+2.62,w:bw3,h:0.38,align:"center",valign:"middle",margin:0,
      fontFace:F.body,fontSize:8,color:i===0?C.peri:C.orange,bold:true});
  });
  chrome(s,21,false,"©2026 Cloudera, Inc. All Rights Reserved. · Agent Studio v3.0.0-b28 (PVC) / v2.3.0-b40 (Public Cloud).");
})();

/* ===================================================== SLIDE 22 — AGENT STUDIO AS HARNESS */
(function(){
  const s=p.addSlide(); s.background={color:C.soft};
  wordmark(s);
  header(s,"From Theory to Product","Agent Studio — The Harness Pillars in Practice",false);
  const rows=[
    [hh("Harness Pillar"),hh("What it means"),hh("Agent Studio implementation")],
    [tp("Progressive Context Architecture"),tc3("Agent only sees the context for its immediate task"),tc3("Sequential workflow routing — each task receives only its declared prior-task context; input variables injected at run time")],
    [tp("Agent Specialization & Parallelism"),tc3("Focused agents with restricted toolsets outperform generalists"),tc3("Each agent gets its own Role, Goal, Backstory and an explicit scoped tool list — no god-mode access; Manager Agent pattern for hierarchical coordination")],
    [tp("Persistent Memory & State"),tc3("Memory lives outside the prompt window"),tc3("Artifact Files (shared virtual filesystem), workflow input variables, and progress.json-style state persist across tasks and sessions")],
    [tp("Structured Execution & Backpressure"),tc3("Mechanical constraints force correct behavior"),tc3("MCP guardrails, jailbreak tool, custom Python tools with typed parameters, CI/CD-ready deployment endpoints, and Phoenix observability for every run")]
  ];
  s.addTable(rows,{x:MX,y:1.52,w:8.76,colW:[2.4,2.6,3.76],rowH:[0.32,0.80,0.80,0.80,0.80],
    fontFace:F.body,fontSize:9,valign:"middle",border:{type:"solid",color:C.line,pt:0.5}});
  // bottom note
  s.addShape(p.shapes.ROUNDED_RECTANGLE,{x:MX,y:4.95,w:8.76,h:0.36,rectRadius:0.07,
    fill:{color:C.navy,transparency:0},line:{type:"none"}});
  s.addText([
    {text:"Agent Studio is Cloudera's production harness for AI agents",options:{bold:true,color:C.white}},
    {text:" — purpose-built to close the gap between the 2% deploying at scale and everyone else.",options:{color:C.ice}}
  ],{x:MX+0.2,y:4.95,w:8.4,h:0.36,valign:"middle",margin:0,fontFace:F.body,fontSize:10.5});
  chrome(s,22,false);
})();
function hh(t){return {text:t,options:{fill:{color:C.navy},color:C.white,bold:true,fontFace:F.head,fontSize:10,valign:"middle",margin:4}};}
function tp(t){return {text:t,options:{color:C.peri,bold:true,fontFace:F.body,fontSize:9,valign:"middle",margin:4,fill:{color:C.pBg}}};}
function tc3(t){return {text:t,options:{color:C.grey,fontFace:F.body,fontSize:9,valign:"middle",margin:4,fill:{color:C.white}}};}

p.writeFile({ fileName: "Cloudera_AI_Landscape.pptx" }).then(f=>console.log("WROTE", f));
