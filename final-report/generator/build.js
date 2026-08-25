const P = require('pptxgenjs');
const path = require('path');
// 이 스크립트(generator/)의 부모, 곧 final-report/ 를 기준으로 삼는다.
const OUT = path.resolve(__dirname, '..');
const A = OUT + '/assets', PV = OUT + '/previews';

const F = 'Apple SD Gothic Neo', M = 'Menlo';
const NAVY='1B2A41', INK='24303F', BLUE='2E6FB7', LBLUE='E8F0F9', RED='C0392B',
      AMBER='E08A1E', GREEN='2E7D5B', GREY='6B7280', LINE='D8DEE6', BG='FFFFFF', SOFT='F5F7FA';

const pptx = new P();
pptx.defineLayout({ name:'W16x9', width:13.333, height:7.5 });
pptx.layout = 'W16x9';
pptx.author='가만있어도SANDI'; pptx.company='경희대학교';
pptx.title='2026ESWContest 자유공모 가만있어도SANDI 개발완료보고서';

const SEC = {
  1:'Ⅰ. 개발 개요', 2:'Ⅰ. 개발 개요', 3:'Ⅰ. 개발 개요',
  4:'Ⅱ. 개발 환경 설명', 5:'Ⅱ. 개발 환경 설명',
  6:'Ⅲ. 개발 프로그램 설명', 7:'Ⅲ. 개발 프로그램 설명', 8:'Ⅲ. 개발 프로그램 설명',
  9:'Ⅲ. 개발 프로그램 설명', 10:'Ⅲ. 개발 프로그램 설명', 11:'Ⅲ. 개발 프로그램 설명',
  12:'Ⅳ. 장애요인과 해결방안', 13:'Ⅳ. 장애요인과 해결방안',
  14:'Ⅴ. 개발 결과물의 차별성', 15:'Ⅴ. 개발 결과물의 차별성', 16:'Ⅴ. 개발 결과물의 차별성',
  17:'Ⅵ. 파급력 및 기대효과', 18:'Ⅵ. 파급력 및 기대효과',
  19:'Ⅶ. 개발 일정 및 업무 분장', 20:'Ⅶ. 개발 일정 및 업무 분장'
};

function page(n, title, sub){
  const s = pptx.addSlide();
  s.background = { color: BG };
  s.addShape(pptx.ShapeType.rect, { x:0, y:0, w:13.333, h:0.09, fill:{color:NAVY} });
  s.addText(SEC[n], { x:0.55, y:0.26, w:6.5, h:0.28, fontFace:F, fontSize:11.5, color:BLUE, bold:true, charSpacing:0.5 });
  s.addText(title, { x:0.55, y:0.58, w:12.23, h:0.52, fontFace:F, fontSize:23, bold:true, color:NAVY, valign:'top' });
  if (sub) s.addText(sub, { x:0.55, y:1.02, w:12.23, h:0.32, fontFace:F, fontSize:13.5, color:GREY, valign:'top' });
  // 구분선은 제목에 가깝게 붙이고, 좌측에 짧은 강조 세그먼트를 겹쳐 제목 블록에 묶는다.
  const ly = sub ? 1.36 : 1.16;
  s.addShape(pptx.ShapeType.line, { x:0.55, y:ly, w:12.23, h:0, line:{color:LINE, width:0.75} });
  s.addShape(pptx.ShapeType.line, { x:0.55, y:ly, w:1.15, h:0, line:{color:BLUE, width:2.25} });
  s.addText(String(n), { x:12.4, y:6.98, w:0.42, h:0.28, fontFace:F, fontSize:11, color:GREY, align:'right' });
  s.addText('SafeNest · 가만있어도SANDI', { x:0.55, y:6.98, w:5, h:0.28, fontFace:F, fontSize:9.5, color:GREY });
  return { s, y: ly + 0.22 };
}
function note(s, txt, y){
  s.addText(txt, { x:0.55, y:y||6.62, w:11.7, h:0.28, fontFace:F, fontSize:9.5, color:GREY });
}
function badge(s, x, y, label, kind){
  const map = { ok:[GREEN,'FFFFFF'], sw:[BLUE,'FFFFFF'], hw:[NAVY,'FFFFFF'], warn:[AMBER,'FFFFFF'], no:[RED,'FFFFFF'], grey:['9AA5B1','FFFFFF'] };
  const c = map[kind]||map.grey;
  s.addShape(pptx.ShapeType.roundRect, { x, y, w:1.32, h:0.30, fill:{color:c[0]}, rectRadius:0.14, line:{color:c[0]} });
  s.addText(label, { x, y, w:1.32, h:0.30, fontFace:F, fontSize:10, bold:true, color:c[1], align:'center', valign:'middle' });
}
function box(s, x,y,w,h, fill, line){
  s.addShape(pptx.ShapeType.roundRect, { x,y,w,h, fill:{color:fill||SOFT}, line:{color:line||LINE, width:1}, rectRadius:0.06 });
}
function sub(s, x, y, t){
  s.addText(t, { x, y, w:7, h:0.30, fontFace:F, fontSize:14.5, bold:true, color:NAVY, valign:'middle' });
}
function cap(s, x, y, w, t){
  s.addText(t, { x, y, w, h:0.26, fontFace:F, fontSize:9.5, color:GREY, align:'center' });
}
function down(s, x, y, w){
  s.addText('▼', { x, y, w, h:0.26, fontFace:F, fontSize:11, color:BLUE, align:'center' });
}
const TB = { fontFace:F, fontSize:12, color:INK, valign:'middle', border:{type:'solid',color:LINE,pt:0.5} };
function hdr(t){ return { text:t, options:{ bold:true, color:'FFFFFF', fill:{color:NAVY}, fontSize:12, align:'center' } }; }

/* ================= COVER ================= */
{
  const s = pptx.addSlide(); s.background={color:BG};
  s.addShape(pptx.ShapeType.rect,{x:0,y:0,w:13.333,h:0.5,fill:{color:NAVY}});
  s.addShape(pptx.ShapeType.rect,{x:0,y:7.16,w:13.333,h:0.34,fill:{color:NAVY}});
  s.addText('제24회 임베디드SW경진대회 개발완료보고서',
    {x:1.0,y:1.55,w:11.3,h:0.5,fontFace:F,fontSize:22,color:GREY,align:'center'});
  s.addShape(pptx.ShapeType.roundRect,{x:5.42,y:2.22,w:2.5,h:0.42,fill:{color:LBLUE},line:{color:BLUE,width:1},rectRadius:0.2});
  s.addText('자 유 공 모 부 문',{x:5.42,y:2.22,w:2.5,h:0.42,fontFace:F,fontSize:13.5,bold:true,color:BLUE,align:'center',valign:'middle'});
  s.addText('SafeNest',{x:1.0,y:2.96,w:11.3,h:1.0,fontFace:F,fontSize:60,bold:true,color:NAVY,align:'center'});
  s.addText('엣지 AI 기반 밀폐공간·차량 생명감지 및 위험도 자동경보 시스템',
    {x:1.0,y:4.02,w:11.3,h:0.5,fontFace:F,fontSize:20,color:INK,align:'center'});
  s.addShape(pptx.ShapeType.line,{x:5.17,y:4.82,w:3.0,h:0,line:{color:LINE,width:1.5}});
  s.addText('가만있어도SANDI',{x:1.0,y:5.12,w:11.3,h:0.50,fontFace:F,fontSize:24,bold:true,color:NAVY,align:'center'});
  s.addText('경희대학교 전자공학과',{x:1.0,y:5.64,w:11.3,h:0.36,fontFace:F,fontSize:16,color:GREY,align:'center'});
  s.addText('김진수 · 강유나 · 김태균 · 유승하 · 한준우',
    {x:1.0,y:6.06,w:11.3,h:0.34,fontFace:F,fontSize:14,color:GREY,align:'center'});
}

/* ============ P1 ============ */
{
  const {s,y} = page(1,'1.1  밀폐공간 질식재해 현황과 개발 필요성');
  sub(s,0.55,y,'재해 통계 (최근 10년, 2014~2023)');
  s.addImage({ path: PV+'/chart_victims.png', x:0.55, y:y+0.40, w:3.20, h:2.75 });
  const st=[['174건','밀폐공간 질식재해 발생 건수'],['338명','재해자'],['136명','사망자'],['85.7%','검찰 송치 중대재해 중\n산소·유해가스 농도 미측정 상태에서 발생']];
  st.forEach((v,i)=>{
    const yy=y+0.36+i*0.66;
    box(s,4.05,yy,3.55,0.58,i===3?'FBE9E7':SOFT,i===3?RED:LINE);
    s.addText(v[0],{x:4.20,y:yy,w:1.15,h:0.58,fontFace:F,fontSize:20,bold:true,color:i===3?RED:NAVY,valign:'middle'});
    s.addText(v[1],{x:5.42,y:yy,w:2.05,h:0.58,fontFace:F,fontSize:i===3?9.5:11.5,color:INK,valign:'middle',lineSpacing:13});
  });
  box(s,7.85,y+0.36,4.93,2.62,SOFT,LINE);
  s.addText('제도와 현실의 간극',{x:8.05,y:y+0.46,w:4.5,h:0.34,fontFace:F,fontSize:13.5,bold:true,color:NAVY});
  const law=['산업안전보건법 제619조는 밀폐공간 작업 시 산소·유해가스 농도 측정과 감시인 배치를 사업주 의무로 규정한다.',
             '중대재해처벌법 확대 적용으로 소규모 사업장까지 예방 설비 수요가 늘었다.',
             '감시인 상시 배치가 어려운 소규모 사업장이 대다수여서, 사람의 상태까지 자동으로 확인하는 무인 감시 수단이 필요하다.'];
  law.forEach((t,i)=>{
    s.addText([{text:'· ',options:{bold:true,color:BLUE}},{text:t,options:{color:INK}}],
      {x:8.05,y:y+0.82+i*0.70,w:4.55,h:0.66,fontFace:F,fontSize:12,lineSpacing:17,valign:'top'});
  });
  sub(s,0.55,y+3.22,'사고 진행 단계와 현재 감시 수단의 공백');
  const fy=y+3.64;
  const flow=[['작업자 진입','밀폐공간 내부'],['이상 발생','산소결핍·유해가스'],['움직임 정지','스스로 신고 불가'],['발견 지연','감시인 부재'],['사고 확정','구조 골든타임 경과']];
  flow.forEach((f,i)=>{
    const x=0.55+i*2.47;
    box(s,x,fy+0.46,2.24,0.90, i>=2&&i<=3?'FBE9E7':LBLUE, i>=2&&i<=3?RED:BLUE);
    s.addText(f[0],{x,y:fy+0.54,w:2.24,h:0.30,fontFace:F,fontSize:13.5,bold:true,color:i>=2&&i<=3?RED:NAVY,align:'center'});
    s.addText(f[1],{x,y:fy+0.84,w:2.24,h:0.30,fontFace:F,fontSize:11,color:GREY,align:'center'});
    if(i<4) s.addText('▶',{x:x+2.26,y:fy+0.78,w:0.22,h:0.28,fontFace:F,fontSize:12,color:GREY,align:'center'});
  });
  s.addShape(pptx.ShapeType.roundRect,{x:5.49,y:fy,w:4.7,h:0.40,fill:{color:'FDF3E3'},line:{color:AMBER,width:1.25},rectRadius:0.06});
  s.addText('가스 감지기·PIR·CCTV가 사람의 상태를 놓치는 구간',{x:5.49,y:fy,w:4.7,h:0.40,fontFace:F,fontSize:11.5,bold:true,color:'9A5B0B',align:'center',valign:'middle'});
  s.addText('▼',{x:6.55,y:fy+0.34,w:0.3,h:0.20,fontFace:F,fontSize:9,color:AMBER,align:'center'});
  s.addText('▼',{x:8.85,y:fy+0.34,w:0.3,h:0.20,fontFace:F,fontSize:9,color:AMBER,align:'center'});
  s.addText('SafeNest 는 법정 산소·유해가스 측정 설비와 감시인을 대체하지 않는다. 이 구간에서 사람의 존재와 상태를 보조적으로 확인해 경보를 낸다.',
    {x:0.55,y:fy+1.38,w:12.23,h:0.30,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  note(s,'※ 출처 : 고용노동부 밀폐공간 질식재해 예방 보도자료(2024), 경향신문 밀폐공간 중대재해 분석 보도(2025). 법령 : 산업안전보건법 제619조.');
}

/* ============ P2 ============ */
{
  const {s,y} = page(2,'1.2  기존 감지 방식의 한계');
  const rows=[[hdr('감지 방식'),hdr('정지 인체'),hdr('사생활 보호'),hdr('착용 불필요'),hdr('환경 위험 감시'),hdr('한계')],
    ['가스 감지기','×','○','○','○','공기질만 측정하므로 사람의 존재를 알지 못한다'],
    ['CCTV','△','×','○','×','정지 인체 판별이 어렵고 사생활 침해 소지가 크다'],
    ['PIR 센서','×','○','○','×','움직일 때만 감지하여 쓰러진 사람을 놓친다'],
    ['웨어러블','○','○','×','×','착용과 충전에 의존하며 미착용 시 무력하다'],
    ['단일 mmWave','○','○','○','×','환경 위험을 모르고 비생체 반사와 구분이 어렵다'],
    ['단일 열화상','△','○','○','×','히터·기계 열원과 사람의 구분이 어렵다']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    const mk=(c==='○'||c==='×'||c==='△');
    return {text:c,options:{align:mk?'center':'left', bold:(mk||ci===0),
      fontSize:mk?15:12, color: mk?(c==='×'?RED:(c==='△'?AMBER:GREEN)):INK}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[1.95,1.30,1.40,1.40,1.55,4.63],rowH:0.46,...TB});
  sub(s,0.55,y+3.58,'공백의 성격');
  s.addText([
    {text:'여섯 가지 방식은 서로 다른 이유로 한계를 갖지만 공통점이 하나 있다. ',options:{color:INK}},
    {text:'센서가 값을 내지 못하거나 값이 오래된 상황을 스스로 인지하지 못한다.',options:{bold:true,color:NAVY}},
    {text:'\n값이 도착하지 않아도 시스템은 아무 신호를 내지 않으며, 이 상태는 정상으로 해석된다. SafeNest 는 서로 다른 성질의 증거를 함께 수집하고 그 증거를 지금 신뢰할 수 있는지까지 판정하여 이 공백에 대응한다.\n',options:{color:INK}},
    {text:'센서 선정도 이 표에서 도출하였다. ',options:{bold:true,color:NAVY}},
    {text:'정지 인체는 mmWave 의 미세 움직임과 열화상의 열 분포로, 환경 위험은 CO₂ 의 농도 추세로, 움직임 이벤트는 PIR 로 덮는다. 한 센서가 놓치는 것을 다른 센서가 보도록 조합하였다.',options:{color:INK}}
  ],{x:0.55,y:y+3.90,w:12.23,h:1.22,fontFace:F,fontSize:11.5,lineSpacing:17,valign:'top'});
  note(s,'○ 충족 · △ 조건부 충족 · × 미충족. 비교는 감지 방식의 범주를 기준으로 하며 특정 제품의 성능을 단정하지 않는다. 유사 제품과의 비교는 15페이지에 별도로 제시한다.');
}

/* ============ P3 ============ */
{
  const {s,y} = page(3,'1.3  개발 목표 및 시스템 구성');
  sub(s,0.55,y,'시스템 구성도');
  const D0=0.55, DW=7.05;
  const sen=[['mmWave\nMR60BHA2','UART2','resp_rate_bpm\nheart_rate_bpm'],
             ['Thermal-90\n(80×62)','I²C + SPI','80×62 uint16\n프레임 (UDP)'],
             ['PIR','GPIO','pir_motion'],
             ['SCD40\n(CO₂)','I²C','co2_ppm']];
  let dy=y+0.38;
  sen.forEach((v,i)=>{
    const x=D0+i*1.79;
    box(s,x,dy,1.70,0.94,LBLUE,BLUE);
    s.addText(v[0],{x,y:dy+0.06,w:1.70,h:0.36,fontFace:F,fontSize:11.5,bold:true,color:NAVY,align:'center',lineSpacing:14});
    s.addText(v[1],{x,y:dy+0.44,w:1.70,h:0.20,fontFace:M,fontSize:9,color:BLUE,align:'center'});
    s.addText(v[2],{x,y:dy+0.64,w:1.70,h:0.28,fontFace:M,fontSize:8.5,color:GREY,align:'center',lineSpacing:11});
    down(s,x,dy+0.96,1.70);
  });
  dy+=1.22;
  box(s,D0,dy,DW,0.56,SOFT,NAVY);
  s.addText([{text:'ESP32 Dev Module',options:{bold:true,fontSize:13,color:NAVY}},
             {text:'   4센서 수집 · 유효성 판정 · 패킷화',options:{fontSize:11.5,color:INK}}],
    {x:D0,y:dy,w:DW,h:0.56,fontFace:F,align:'center',valign:'middle'});
  dy+=0.58;
  s.addText('▼   SafeNest TCP protocol v1  (16 B 헤더 · Wi-Fi · valid{} 동봉)',
    {x:D0,y:dy,w:DW,h:0.30,fontFace:F,fontSize:11,bold:true,color:BLUE,align:'center',valign:'middle'});
  dy+=0.32;
  box(s,D0,dy,DW,0.74,SOFT,NAVY);
  s.addText([{text:'Raspberry Pi 5',options:{bold:true,fontSize:13,color:NAVY}},
             {text:'\n유효성·신선도 재검사  →  INT8 TFLite 추론  →  Risk Engine 가중 융합',options:{fontSize:11.5,color:INK}}],
    {x:D0,y:dy,w:DW,h:0.74,fontFace:F,align:'center',valign:'middle',lineSpacing:17});
  dy+=0.76; down(s,D0,dy,DW); dy+=0.24;
  const lv=[['NORMAL','R < 30',GREEN],['CAUTION','30 ≤ R < 60',AMBER],['DANGER','R ≥ 60',RED],['판단 보류','risk = None',GREY]];
  lv.forEach((v,i)=>{
    const x=D0+i*1.79;
    s.addShape(pptx.ShapeType.roundRect,{x,y:dy,w:1.70,h:0.50,fill:{color:v[2]},line:{color:v[2]},rectRadius:0.06});
    s.addText(v[0],{x,y:dy+0.02,w:1.70,h:0.26,fontFace:F,fontSize:11.5,bold:true,color:'FFFFFF',align:'center'});
    s.addText(v[1],{x,y:dy+0.26,w:1.70,h:0.22,fontFace:M,fontSize:9,color:'FFFFFF',align:'center'});
    down(s,x,dy+0.52,1.70);
  });
  dy+=0.78;
  const out=[['부저','GPIO18 · 880 Hz'],['LCD','상태 6종 표시'],['Web 관제','QR 공간코드 · 실시간 대시보드']];
  out.forEach((v,i)=>{
    const x=D0+i*2.39;
    box(s,x,dy,2.30,0.52,LBLUE,BLUE);
    s.addText(v[0],{x,y:dy+0.03,w:2.30,h:0.26,fontFace:F,fontSize:12,bold:true,color:NAVY,align:'center'});
    s.addText(v[1],{x,y:dy+0.27,w:2.30,h:0.22,fontFace:F,fontSize:9.5,color:GREY,align:'center'});
  });

  sub(s,7.90,y,'개발 목표 (중간계획서 기준 초기 목표)');
  const goals=['① mmWave와 열화상 융합으로 정지 상태의 인체를 비영상 방식으로 감지한다.',
    '② 다중 센서 증거 융합과 온디바이스 AI로 정상·주의·위험 3단계를 자동 판단한다.',
    '③ 위험 감지 시 현장 경보·상태 표시·이벤트 기록을 자동 수행한다.',
    '④ Raspberry Pi 단일 노드 MVP를 완성하고 다중 노드로 확장 가능한 구조를 갖춘다.'];
  goals.forEach((g,i)=>{
    s.addText(g,{x:7.90,y:y+0.40+i*0.60,w:4.88,h:0.56,fontFace:F,fontSize:12,color:INK,lineSpacing:17,valign:'top'});
  });
  box(s,7.90,y+2.90,4.88,0.94,'FFFFFF',BLUE);
  s.addText('소스코드 (GitHub)',{x:8.10,y:y+2.98,w:4.5,h:0.24,fontFace:F,fontSize:11,bold:true,color:BLUE});
  s.addShape(pptx.ShapeType.line,{x:8.10,y:y+3.42,w:4.48,h:0,line:{color:LINE,width:1}});
  s.addText('시연동영상 (YouTube)',{x:8.10,y:y+3.48,w:4.5,h:0.24,fontFace:F,fontSize:11,bold:true,color:BLUE});
  s.addShape(pptx.ShapeType.line,{x:8.10,y:y+3.76,w:4.48,h:0,line:{color:LINE,width:1}});
  s.addText('SafeNest는 mmWave·열화상·PIR·CO₂ 센서의 서로 다른 정보를 결합하고, 각 값의 유효성과 신선도를 확인한 뒤 위험도를 판단하여 현장 경보와 화면으로 전달하는 임베디드 안전 시스템이다.',
    {x:7.90,y:y+4.02,w:4.88,h:0.98,fontFace:F,fontSize:12,color:INK,lineSpacing:17,valign:'top'});
  note(s,'표기 원칙 : 검증 수준을 SW 검증 / 실기기 검증 / 실기기 E2E 로 구분해 표기한다. 초기 개발 목표와 달성 결과는 16페이지 구현 결과 표에 증거와 함께 제시한다.');
}

/* ============ P4 ============ */
{
  const {s,y} = page(4,'2.1  시스템 계층 구조 및 개발 환경');
  sub(s,0.55,y,'4계층 역할 분담');
  const lay=[['감지','MR60BHA2 · Thermal-90 · SCD40 · PIR'],
             ['수집·검증','ESP32 Dev Module. 버스 판독, valid·freshness 판정, CRC, 패킷화'],
             ['판단','Raspberry Pi 5. 센서 상태 관리, INT8 TFLite 추론, Risk Engine'],
             ['대응','부저·LCD·Web 관제. 등급별 경보와 상태 표시']];
  lay.forEach((L,i)=>{
    const yy=y+0.38+i*0.38;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.35,h:0.34,fill:{color:i%2?NAVY:BLUE},line:{color:i%2?NAVY:BLUE},rectRadius:0.05});
    s.addText(L[0],{x:0.55,y:yy,w:1.35,h:0.34,fontFace:F,fontSize:12,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    s.addText(L[1],{x:2.02,y:yy,w:10.76,h:0.34,fontFace:F,fontSize:12.5,color:INK,valign:'middle'});
  });
  sub(s,0.55,y+1.98,'개발 환경');
  const env=[[hdr('구분'),hdr('사용 기술'),hdr('대상 기기'),hdr('저장소 근거 경로')],
   ['MCU 펌웨어','Arduino (C++) / FreeRTOS 태스크','ESP32 Dev Module','ESP32/Arduino/esp32_sensor_node/'],
   ['수신·표시 서버','Python 3 표준 라이브러리 (http.server, socket, struct)','Raspberry Pi 5','RaspberryPi/LCD/server.py'],
   ['온디바이스 AI','TensorFlow Lite INT8 추론 / 학습·검증 TensorFlow 2.19.1','Raspberry Pi 5','RaspberryPi/Ondevice_AI/inference/, models/'],
   ['위험도 엔진','Python + NumPy','Raspberry Pi 5','RaspberryPi/Ondevice_AI/risk/'],
   ['관제 백엔드·웹','Python FastAPI + Uvicorn, qrcode, SQLite 영속화','Raspberry Pi 5','RaspberryPi/Runtime/backend/ · RaspberryPi/Web/'],
   ['센서 계약','Python 추상 인터페이스','전 영역 공통','RaspberryPi/Ondevice_AI/sensors/base_sensor.py'],
   ['외함','3D CAD → STL 4종','FDM 출력','hardware/3d_models/']];
  s.addTable(env.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+2.34,w:12.23,colW:[1.72,4.13,1.82,4.56],rowH:0.36,...TB,fontSize:10.5});
  note(s,'저장소 전체 파일 수 4,316개 (main 8413d2f 기준). 이 중 2,253개는 archive/ 에 보존한 과거 구현과 측정 증거이며, 위 표는 개발 환경에 해당하는 구성만 발췌한 것이다.');
}

/* ============ P5 ============ */
{
  const {s,y} = page(5,'2.2  센서 구성 및 하드웨어 인터페이스');
  const pin=[[hdr('센서'),hdr('인터페이스'),hdr('ESP32 핀 / 주소'),hdr('수집 값')],
   ['MR60BHA2\n(mmWave)','UART2\n115200 bps','RX GPIO16 / TX GPIO17','호흡수, 심박수,\n재실, phase'],
   ['SCD40\n(CO₂)','I²C\n100 kHz','SDA 21 / SCL 22 / 0x62','co2_ppm'],
   ['PIR','GPIO 디지털 입력','GPIO 13 (20 ms 폴링)','pir_motion\n+ 전이 event_id'],
   ['Thermal-90\n(MI48xx)','I²C 제어\n+ SPI','0x40 · 0x41 / SCLK18 MISO19\nMOSI23 CS27 READY26 RESET25','80×62 uint16\n프레임']];
  s.addTable(pin.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{bold:ci===0,color:ci===0?NAVY:INK}}:c)),
    {x:0.55,y:y+0.04,w:6.55,colW:[1.55,1.45,2.30,1.25],rowH:0.52,...TB,fontSize:10.5});
  sub(s,0.55,y+2.86,'설계상 중요한 점');
  const pts=['열화상 RESET(GPIO25)을 단독 핀으로 확보해 부팅 시퀀스와 무프레임 자동 재초기화를 구현하였다.',
             '버스 속도는 보드·펌웨어 시험 조건에 따라 다르다. 최종 제출 기준 통합 노드 펌웨어는 SPI 1 MHz · I²C 100 kHz 설정이다.',
             '실행 루프에서 delay()를 사용하지 않고 millis() 주기 판정과 FreeRTOS 네트워크 태스크로 분리하였다.',
             '10개 신호선이 서로 다른 버스에 물리므로 핀 상수를 펌웨어 상단에 모아 배선도와 1:1로 대응시켰다.',
             'CO₂ 는 환기 상태와 재실 추세를 보는 지표이며, 산소·유해가스 법정 측정을 대신하지 않는다.'];
  pts.forEach((p,i)=>{
    s.addText([{text:'· ',options:{bold:true,color:BLUE}},{text:p,options:{color:INK}}],
      {x:0.58,y:y+3.18+i*0.40,w:6.52,h:0.38,fontFace:F,fontSize:11,lineSpacing:14.5,valign:'top'});
  });
  s.addImage({ path:A+'/hw_wiring_diagram.png', x:7.35, y:y+0.04, w:5.43, h:4.38 });
  s.addShape(pptx.ShapeType.rect,{x:7.35,y:y+0.04,w:5.43,h:4.38,fill:{type:'none'},line:{color:LINE,width:1}});
  cap(s,7.35,y+4.46,5.43,'[그림 1] ESP32 4센서 결선도. 좌측 표의 핀 배정과 1:1로 대응한다.');
  note(s,'근거 : esp32_sensor_node.ino 핀 상수 PIN_*, THERMAL_ADDRESS_A·B.   코드의 Thermal44Sensor · thermal44_* 는 레거시 식별자이며, 하드웨어 명칭은 Thermal-90 이다.');
}

/* ============ P6 ============ */
{
  const {s,y} = page(6,'3.1  파일 구성과 함수별 기능');
  sub(s,0.55,y,'파일 구성');
  const mod=[[hdr('경로'),hdr('역할')],
   ['ESP32/Arduino/esp32_sensor_node/','4센서 수집, 유효성 판정, 패킷화 (1,042줄)'],
   ['RaspberryPi/LCD/server.py','TCP 9000 수신, HTTP 8080 API, 상태 6종, 부저'],
   ['RaspberryPi/Ondevice_AI/sensors/','센서별 어댑터·mock, 공용 계약 base_sensor.py'],
   ['RaspberryPi/Ondevice_AI/inference/','TFLite Interpreter, 모델 레지스트리, 검증기'],
   ['RaspberryPi/Ondevice_AI/risk/','가중 융합 위험도, fail-closed 판정'],
   ['RaspberryPi/Ondevice_AI/integrated_node/','통합 실행 노드, 외부 provider 주입'],
   ['RaspberryPi/Runtime/backend/','관제 API, QR 공간 식별, 상태 영속화'],
   ['RaspberryPi/Web/','관제 화면, 방문자 화면, 실시간 대시보드'],
   ['hardware/3d_models/','외함 CAD STL 4종 + 설계사양 2종']];
  s.addTable(mod.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{fontFace:ci===0?M:F,fontSize:ci===0?8.5:10}}:c)),
    {x:0.55,y:y+0.36,w:6.03,colW:[2.95,3.08],rowH:0.30,...TB});

  sub(s,6.85,y,'핵심 함수별 기능');
  const fn=[[hdr('함수'),hdr('기능')],
   ['formatNullableFloat()','유효하지 않은 수치를 0으로 대체하지 않고 null 로 직렬화'],
   ['makePacketHeader()','SNST 16 B 헤더 생성 (magic·version·type·seq·length)'],
   ['sendThermalUdp()','payload 9,936 B 를 1,200 B 데이터그램 9 조각으로 분할 송신'],
   ['thermalFrameCrc32()','프레임 CRC32 계산, 모든 UDP 조각 헤더에 반복 기록'],
   ['recoverThermalIfStale()','30 s 무프레임 시 GPIO RESET 토글로 센서 재초기화'],
   ['telemetryTcpTask() /\nthermalUdpTask()','TCP·UDP 송신을 FreeRTOS 태스크로 분리해 상호 블로킹 차단'],
   ['recv_exact()','TCP 경계 없음을 전제로 헤더·payload 길이만큼 정확 수신'],
   ['record_telemetry()','채널별 valid·수신 시각 기록, 5 s 기준 신선도 판정'],
   ['evaluate_sensor_health_\nand_risk()','유효 채널 가중치 재정규화 후 위험도 산출, 전부 무효면 None'],
   ['logHealth()','Wi-Fi·채널값·프레임수·CRC 오류·UDP 실패·free heap 주기 출력']];
  s.addTable(fn.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{fontFace:ci===0?M:F,fontSize:ci===0?7.5:9.5}}:c)),
    {x:6.85,y:y+0.36,w:5.93,colW:[2.10,3.83],rowH:0.27,...TB});

  box(s,0.55,y+4.00,12.23,1.12,SOFT,AMBER);
  s.addText('외부 오픈소스 및 데이터셋 고지 (대회 규정 제10조 ③)',{x:0.78,y:y+4.06,w:7,h:0.28,fontFace:F,fontSize:12,bold:true,color:'9A5B0B'});
  s.addText([
    {text:'데이터셋 : ',options:{bold:true,color:NAVY}},
    {text:'Zenodo mmWave vital-sign (DOI 10.5281/zenodo.18599983, CC BY 4.0) · UCI Occupancy Detection (ID 357, CC BY 4.0) · SDT Thermal (TU Wien / Zenodo 4124309)\n',options:{color:INK}},
    {text:'라이브러리 : ',options:{bold:true,color:NAVY}},
    {text:'TensorFlow Lite, Sensirion SCD4x, Seeed mmWave, FastAPI · Uvicorn, gpiozero, NumPy.  위 자산은 학습·추론·통신에 활용하였으며, 센서 통합 펌웨어와 통신 프로토콜, 상태 관리, 위험도 엔진은 팀 자체 구현이다.',options:{color:INK}}
  ],{x:0.78,y:y+4.32,w:11.77,h:0.74,fontFace:F,fontSize:10,lineSpacing:14,valign:'top'});
  note(s,'저장소는 파일 종류 대신 기기와 책임 영역을 기준으로 분할하였다. 각 디렉터리의 소유자는 .github/CODEOWNERS 에 정의되어 있다.');
}

/* ============ P7 ============ */
{
  const {s,y} = page(7,'3.2  통신 프로토콜 설계','SafeNest TCP protocol v1. 모든 정수는 network byte order');
  sub(s,0.55,y,'16 B 고정 헤더 구조');
  const fields=[['magic','4 B','"SNST"',1],['version','1 B','1',0],['type','1 B','1=JSON, 2=열화상',0],
                ['flags','2 B','0',0],['sequence','4 B','uint32',0],['payload_length','4 B','uint32',1]];
  let px=0.55;
  fields.forEach((f,i)=>{
    const w=[1.55,1.25,1.85,1.25,1.55,2.35][i];
    box(s,px,y+0.38,w,0.86,f[3]?LBLUE:SOFT,f[3]?BLUE:LINE);
    s.addText(f[0],{x:px,y:y+0.44,w,h:0.26,fontFace:M,fontSize:11,bold:true,color:NAVY,align:'center'});
    s.addText(f[1],{x:px,y:y+0.68,w,h:0.24,fontFace:F,fontSize:10.5,color:BLUE,align:'center'});
    s.addText(f[2],{x:px,y:y+0.94,w,h:0.24,fontFace:F,fontSize:10,color:GREY,align:'center'});
    px+=w+0.06;
  });
  sub(s,0.55,y+1.42,'전송 흐름과 페이로드');
  const fl=['센서 판독','유효성 판정','SNST 16 B 헤더 + payload','TCP 9000 송신','Pi 수신·재검사'];
  fl.forEach((t,i)=>{
    const x=0.55+i*1.42;
    box(s,x,y+1.82,1.28,0.44,SOFT,LINE);
    s.addText(t,{x:x+0.04,y:y+1.82,w:1.20,h:0.44,fontFace:F,fontSize:10,color:INK,align:'center',valign:'middle',lineSpacing:12});
    if(i<4) s.addText('▶',{x:x+1.28,y:y+1.90,w:0.14,h:0.26,fontFace:F,fontSize:10,color:GREY,align:'center'});
  });
  box(s,7.60,y+1.82,2.55,0.44,SOFT,LINE);
  s.addText([{text:'Type 1  ',options:{bold:true,color:NAVY}},{text:'스칼라 JSON, 1초 주기',options:{color:INK}}],
    {x:7.60,y:y+1.82,w:2.55,h:0.44,fontFace:F,fontSize:10.5,align:'center',valign:'middle'});
  box(s,10.25,y+1.82,2.53,0.44,SOFT,LINE);
  s.addText([{text:'Type 2  ',options:{bold:true,color:NAVY}},{text:'열화상 프레임 (별도 UDP)',options:{color:INK}}],
    {x:10.25,y:y+1.82,w:2.53,h:0.44,fontFace:F,fontSize:10.5,align:'center',valign:'middle'});
  box(s,0.55,y+2.40,6.05,1.30,SOFT,LINE);
  s.addText('Type 1 페이로드 (schema safenest.telemetry.v1)',{x:0.75,y:y+2.46,w:5.7,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('device_id · boot_id · seq · uptime_ms\nresp_rate_bpm · heart_rate_bpm · co2_ppm\npir_motion · pir_event_id\npir_last_transition_monotonic_ms\nvalid { respiration, heart, co2 } · mmwave{} · health{}',
    {x:0.75,y:y+2.70,w:5.7,h:0.96,fontFace:M,fontSize:9,color:INK,lineSpacing:13.5});
  box(s,6.75,y+2.40,6.03,1.30,SOFT,LINE);
  s.addText('열화상 프레임 전송 (12페이지 구조 개선 결과, UDP 5005)',{x:6.95,y:y+2.46,w:5.7,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('SafeNest Thermal UDP v1 (magic "SNTU", version 1)\n32 B 헤더 : frame id · chunk index · offset ·\nlength · CRC32 (모든 조각이 프레임 CRC32 반복)\n논리 payload 9,936 B = 메타 16 B + 4,960 × uint16\n→ 1,200 B 데이터그램 9 조각 분할 · 재조립',
    {x:6.95,y:y+2.70,w:5.7,h:0.96,fontFace:M,fontSize:9,color:INK,lineSpacing:13.5});
  sub(s,0.55,y+3.80,'무효값 처리');
  s.addText('void formatNullableFloat(char *output, size_t outputSize, bool valid, float value) {\n  if (valid && isfinite(value)) snprintf(output, outputSize, "%.2f", value);\n  else                          strlcpy(output, "null", outputSize);   // 0으로 대체하지 않는다\n}',
    {x:0.55,y:y+4.16,w:8.35,h:0.86,fontFace:M,fontSize:10,color:INK,lineSpacing:16});
  s.addText('0 ppm과 측정 실패를 같은 숫자로 보내면 수신 측은 둘을 구분할 수 없다. 값과 valid 플래그를 함께 보내야 판단 계층이 결측을 정상값으로 오해하지 않는다.',
    {x:9.05,y:y+4.16,w:3.73,h:0.86,fontFace:F,fontSize:11,color:INK,lineSpacing:15,valign:'top'});
  note(s,'근거 : esp32_sensor_node.ino 프로토콜 정의 L113–124, formatNullableFloat L546–553 · RaspberryPi/LCD/server.py 의 PACKET_HEADER, recv_exact.', 6.72);
}

/* ============ P8 ============ */
{
  const {s,y} = page(8,'3.3  센서 유효성 및 신선도 검사');
  sub(s,0.55,y,'수신부터 상태 확정까지');
  const steps=[['패킷 수신','recv_exact()로 헤더 16 B를 읽고\npayload_length 만큼 정확히 수신'],
               ['형식 검사','magic·version·flags 확인\npayload 20,000 B 초과 시 종료'],
               ['스키마 검사','safenest.telemetry.v1 확인\nvalid{} 객체 존재 확인'],
               ['신선도 검사','ESP32 : mmWave 5 s / CO₂ 15 s / 열화상 30 s\nPi : 5 s 독립 판정'],
               ['상태 확정','LIVE · STALE · INVALID\nDISCONNECTED · WAITING']];
  steps.forEach((st,i)=>{
    const x=0.55+i*2.47;
    box(s,x,y+0.38,2.26,1.18,i===4?LBLUE:SOFT,i===4?BLUE:LINE);
    s.addText(st[0],{x,y:y+0.46,w:2.26,h:0.28,fontFace:F,fontSize:12.5,bold:true,color:NAVY,align:'center'});
    s.addText(st[1],{x:x+0.09,y:y+0.74,w:2.08,h:0.78,fontFace:F,fontSize:9.5,color:INK,align:'center',lineSpacing:13});
    if(i<4) s.addText('▶',{x:x+2.28,y:y+0.86,w:0.18,h:0.26,fontFace:F,fontSize:12,color:GREY,align:'center'});
  });
  sub(s,0.55,y+1.62,'열화상 프레임 무결성 검사 (센서 → MCU 계층)');
  const ig=[[hdr('검사'),hdr('방법'),hdr('불합격 시 처리'),hdr('구현 위치')],
   ['CRC-16/CCITT-FALSE','poly 0x1021, init 0xFFFF 로 계산해 헤더 기록값과 대조.\nMCU → Pi 의 UDP 조각 재조립은 별도 계층인 프레임 CRC32 로 확인한다','프레임 폐기','thermalFrameCrc()'],
   ['헤더 범위 재계산','min/max 를 픽셀에서 다시 계산해 헤더 값과 대조','프레임 폐기','server.py'],
   ['시퀀스 교차 확인','외부 헤더 sequence 와 내부 frame_sequence 일치 확인','프레임 폐기','server.py'],
   ['죽은 화소 배제','raw 2332–4231 (약 −40~150 ℃) 범위 밖 화소 제외','사용 가능 화소 32개 미만이면 폐기','.ino / server.py'],
   ['무프레임 자동 복구','30 s 무프레임 시 GPIO RESET LOW 20 ms → HIGH 300 ms','센서 재초기화','recoverThermalIfStale()']];
  s.addTable(ig.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+1.98,w:12.23,colW:[2.35,5.25,2.55,2.08],rowH:0.36,...TB,fontSize:11});
  s.addText([{text:'설계 원칙 : ',options:{bold:true,color:NAVY}},
    {text:'센서가 정해진 시간 안에 갱신되지 않으면 해당 입력을 STALE로 분리하고, 마지막 정상값을 현재 증거로 다시 쓰지 않는다. 유효하지 않은 증거는 0으로 대체하지 않고 판단에서 제외한다.  PIR 은 레벨 판독 입력이라 TTL 을 두지 않고, 상태가 바뀔 때마다 pir_event_id 를 증가시켜 이벤트 누락을 확인한다.\n',options:{color:INK}},
    {text:'자기진단 : ',options:{bold:true,color:NAVY}},
    {text:'ESP32 는 큐 덮어쓰기·TCP·UDP 송신·CO₂ 판독·열화상 조회 실패 카운터 9종을 telemetry health 블록에 함께 실어 보내고, boot_id 로 재부팅과 재접속을 구분한다.',options:{color:INK}}],
    {x:0.55,y:y+4.24,w:12.23,h:0.92,fontFace:F,fontSize:11,lineSpacing:15,valign:'top'});
  note(s,'검증 : 본 문서 작성 시점에 RaspberryPi/LCD 테스트 4건을 실행해 전부 통과하였다. 텔레메트리·열화상 패킷 수신, 스키마 위반 거부, 연결 종료 시 STALE 전환, 최신값 스냅샷이 포함된다.');
}

/* ============ P9 ============ */
{
  const {s,y} = page(9,'3.4  온디바이스 AI 모델 구성과 검증 범위');
  const m=[[hdr('기능'),hdr('모델'),hdr('입력 → 출력'),hdr('양자화'),hdr('검증 범위'),hdr('상태')],
   ['열화상 기반\n인체 자세 분석','thermal_fall_int8\nv0.1.0 (Production)','62×80×1 프레임 → 3-class\nNOT_HUMAN / HUMAN_NORMAL / HUMAN_FALL','full INT8\n318 KB','Production 경로 · 실제 프레임을\nRaspberry Pi 5 INT8 TFLite 로 관통','허용'],
   ['CO₂ 기반\n재실 분석','co2_occupancy_int8\nv0.1.0','CO₂ slope · 습도 · ppm → 2-class\nVACANT / OCCUPIED','full INT8\n4.4 KB','공개 데이터셋 기반 오프라인 검증\n(실센서 데이터는 검증 범위 밖)','허용\n(제한)'],
   ['mmWave 기반\n호흡 패턴 분석','mmwave_resp_int8\nv0.1.0','300샘플 30 s 창 → 3-class\nNORMAL / RAPID / APNEA','full INT8\n466 KB','재현 검증에서 클래스 붕괴 확인\nacc 0.3996 · macro-F1 0.19 · recall 0.0','차단'],
   ['mmWave 기반\n호흡 패턴 분석','mmwave_resp_int8\nv0.2.0 후보','동일','full INT8\n22 KB','합성 데이터 468샘플 한정 smoke\n실센서 성능 검증 불가','후보']];
  s.addTable(m.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:0.55,y:y+0.04,w:7.30,colW:[1.10,1.15,1.90,0.70,1.80,0.65],rowH:0.70,...TB,fontSize:9});
  badge(s,7.97,y+0.74,'실기기 E2E','hw');
  badge(s,7.97,y+1.44,'오프라인','sw');
  badge(s,7.97,y+2.14,'배포 차단','no');
  badge(s,7.97,y+2.84,'합성 한정','warn');
  // 우측 : AI 와 안전 판단 계층의 역할 분리.
  box(s,9.41,y+0.04,3.37,3.34,SOFT,LINE);
  s.addText('AI 와 안전 판단의 역할 분리',{x:9.58,y:y+0.12,w:3.03,h:0.26,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('Edge AI 가 하는 일',{x:9.58,y:y+0.44,w:3.03,h:0.22,fontFace:F,fontSize:10,bold:true,color:BLUE});
  s.addText('· 열화상 인체·자세 특징 판단\n· CO₂ 재실 보조 분석\n· 검증을 통과한 모델에 한해 증거 생성',
    {x:9.58,y:y+0.68,w:3.03,h:0.52,fontFace:F,fontSize:8.5,color:INK,lineSpacing:11.5,valign:'top'});
  s.addText('안전 판단 계층이 하는 일',{x:9.58,y:y+1.26,w:3.03,h:0.22,fontFace:F,fontSize:10,bold:true,color:NAVY});
  s.addText('· 유효성·신선도 검사\n· Sensor Health 판정\n· 유효 증거만 가중치 재정규화\n· 전부 무효면 판단 보류 (fail-closed)\n· 최종 위험도와 경보 등급 결정',
    {x:9.58,y:y+1.50,w:3.03,h:1.00,fontFace:F,fontSize:8.5,color:INK,lineSpacing:11.5,valign:'top'});
  box(s,9.55,y+2.56,3.09,0.74,'FFFFFF',BLUE);
  s.addText('AI 출력도 센서 값과 같은 하나의 증거로 다룬다. AI 또는 센서가 신뢰할 수 없는 상태이면 그 입력을 최종 위험 판단에서 제외한다.',
    {x:9.68,y:y+2.62,w:2.83,h:0.62,fontFace:F,fontSize:8.5,color:NAVY,lineSpacing:11.5,valign:'top'});
  box(s,0.55,y+3.62,12.23,1.42,'FDF3E3',AMBER);
  s.addText('적용 범위 및 현재 Production 경로',{x:0.78,y:y+3.68,w:5,h:0.26,fontFace:F,fontSize:12,bold:true,color:'9A5B0B'});
  s.addText('① Production 열화상 경로는 per-frame min-max 전처리와 thermal_fall_int8 v0.1.0 추론으로 구성한다. ℃ 변환 → P1 z-score → FULL_INT8(B5) 는 오프라인 진단·호환성 검증 경로이며 제품 경로와 분리해 관리한다.\n② FPN 및 die-temperature drift 보정식은 오프라인 검증 경로에서 구현·확인하였으며 Production 추론 경로와 분리해 운용한다.\n③ HUMAN_FALL 은 눕기(LYING) 정적 자세를 기준으로 학습한 자세 분류이며, 열화상이 산출하는 값은 표면 온도이다.\n④ 필드 관측에서 열화상 수신·저장·추론 경로의 정상 동작을 확인하였다. NOT_HUMAN 편향은 전처리·도메인 정합 과제로 분리해 관리한다.\n⑤ mmWave 호흡 신호는 임상 진단 용도가 아니며, v0.2.0 후보 지표는 합성 데이터 기준값이다.',
    {x:0.78,y:y+3.94,w:11.77,h:1.06,fontFace:F,fontSize:10,color:INK,lineSpacing:14.5,valign:'top'});
  note(s,'근거 : RaspberryPi/Ondevice_AI/models/model_manifest.json · archive/legacy_main_repo/docs/thermal/v5_validation/reports/phase4_6_inference_report.md · research/thermal_ai/ 의 T-B1·T-B5 리포트 및 정적 세션 검토(2026-08-16).');
}

/* ============ P10 ============ */
{
  const {s,y} = page(10,'3.5  위험도 산출 알고리즘');
  s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:y+0.02,w:12.23,h:0.56,fill:{color:LBLUE},line:{color:BLUE,width:1},rectRadius:0.06});
  s.addText('R = 100 × ( 0.35 · mmWave + 0.35 · CO₂ + 0.15 · PIR + 0.15 · Thermal )      NORMAL R < 30   ·   CAUTION 30 ≤ R < 60   ·   DANGER R ≥ 60',
    {x:0.55,y:y+0.02,w:12.23,h:0.56,fontFace:F,fontSize:12.5,bold:true,color:NAVY,align:'center',valign:'middle'});
  sub(s,0.55,y+0.68,'센서 상태에 따른 산출 방식');
  badge(s,11.46,y+0.68,'SW 검증','sw');
  const cases=[
    ['모든 센서 유효','HEALTHY','4채널 가중 융합으로 위험도를 산출한다.',GREEN],
    ['일부 무효 또는 STALE','DEGRADED','유효한 센서의 가중치만 재정규화하여 산출한다.\n무효 입력을 마지막 정상값으로 대체하지 않는다.',AMBER],
    ['전부 무효 또는 결측','FAILED','risk_score = None, risk_level = None.\n위험도를 산출하지 않으며 정상으로 표시하지 않는다.',RED]];
  cases.forEach((c,i)=>{
    const x=0.55+i*4.13;
    box(s,x,y+1.02,3.86,1.32,'FFFFFF',c[3]);
    s.addShape(pptx.ShapeType.rect,{x,y:y+1.02,w:3.86,h:0.34,fill:{color:c[3]}});
    s.addText(c[1],{x,y:y+1.02,w:3.86,h:0.34,fontFace:F,fontSize:12.5,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    s.addText(c[0],{x:x+0.12,y:y+1.42,w:3.62,h:0.26,fontFace:F,fontSize:12,bold:true,color:NAVY,align:'center'});
    s.addText(c[2],{x:x+0.12,y:y+1.70,w:3.62,h:0.60,fontFace:F,fontSize:11,color:INK,align:'center',lineSpacing:16});
  });
  sub(s,0.55,y+2.46,'계산 예시 : 열화상이 STALE 로 떨어진 경우');
  box(s,0.55,y+2.82,7.35,1.52,SOFT,LINE);
  s.addText([
    {text:'입력   ',options:{bold:true,color:NAVY}},
    {text:'mmWave 0.00 (valid) · CO₂ 1.00 (valid, 1,500 ppm 초과) · PIR 1.00 (valid, 무움직임) · Thermal STALE\n',options:{color:INK}},
    {text:'재정규화   ',options:{bold:true,color:NAVY}},
    {text:'유효 가중치 합 0.35 + 0.35 + 0.15 = 0.85  →  0.412 / 0.412 / 0.176\n',options:{color:INK}},
    {text:'산출   ',options:{bold:true,color:NAVY}},
    {text:'R = 100 × (0.00×0.412 + 1.00×0.412 + 1.00×0.176) = ',options:{color:INK}},
    {text:'58.82  →  CAUTION',options:{bold:true,color:AMBER}},
    {text:'\nsystem_health = DEGRADED, stale_sensors = [thermal]',options:{fontFace:M,fontSize:10,color:GREY}}
  ],{x:0.75,y:y+2.92,w:6.95,h:1.34,fontFace:F,fontSize:11.5,lineSpacing:19,valign:'top'});
  box(s,8.10,y+2.82,4.68,1.52,'FFFFFF',RED);
  s.addText('fail-closed 구현 (RaspberryPi/Ondevice_AI/risk/fallback.py)',{x:8.30,y:y+2.90,w:4.38,h:0.24,fontFace:F,fontSize:10,bold:true,color:RED});
  s.addText('if system_health == "FAILED":\n    risk_score = None   # 0점으로 대체하지 않는다\n    risk_level = None   # 등급 자체를 내지 않는다\n    reasons.insert(0,\n        "ALL_SENSORS_FAULT_OR_MISSING")',
    {x:8.30,y:y+3.14,w:4.3,h:1.14,fontFace:M,fontSize:10,color:INK,lineSpacing:16});
  s.addText([
    {text:'임계값의 근거   ',options:{bold:true,color:NAVY}},
    {text:'CO₂ 1,500 ppm 은 실내공기질 관리법 시행규칙 별표2가 정한 기계환기 시설의 유지기준과 같은 값이다. 산업안전보건기준에 관한 규칙 제618조의 적정공기 기준(CO₂ 1.5 %, 곧 15,000 ppm 미만)보다 훨씬 낮은 조기경보 지점에 해당한다.  ',options:{color:INK}},
    {text:'위험도 30 / 60 및 CO₂ 2,000 ppm 은 팀 내부 실험 기준값이며 대외 공인 기준이 아니다.',options:{bold:true,color:RED}}
  ],{x:0.55,y:y+4.48,w:12.23,h:0.68,fontFace:F,fontSize:11.5,lineSpacing:18,valign:'top'});
  note(s,'계산 예시는 정본 fallback.py 를 그대로 실행해 얻은 값이다. 열화상 판정은 다른 센서의 상태·신선도와 함께 최종 위험도를 결정하는 입력으로 쓰인다. 검증 : 위험도 테스트 22건 실행 전부 통과.');
}

/* ============ P11 ============ */
{
  const {s,y} = page(11,'3.6  실측 검증 결과','서로 다른 조건에서 채널별로 수행하였으며, 통합 시스템 성능으로 합산하지 않는다');
  sub(s,0.55,y,'① CO₂ 센서 연속 수신 검증');
  s.addText('ESP32 192.168.1.16 → Pi 5 192.168.1.44:9000, TCP 실경로, 2026-08-12',
    {x:3.05,y:y+0.02,w:3.55,h:0.26,fontFace:F,fontSize:9.5,color:GREY,valign:'middle'});
  s.addImage({ path: PV+'/chart_co2.png', x:0.55, y:y+0.34, w:6.03, h:2.48 });
  const co2=[[hdr('세션'),hdr('유효 표본'),hdr('결측률'),hdr('판정')],
    ['프리플라이트 30초','30 / 30','0 %','PASS'],
    ['baseline 5분 (최초)','277 / 300','7.67 %','FAIL'],
    ['baseline 5분 (재측정)','300 / 300','0 %','PASS'],
    ['호기 6분','329 / 360','8.61 %','PASS']];
  s.addTable(co2.map(r=>r.map(c=>typeof c==='string'?{text:c,options:{align:c==='PASS'||c==='FAIL'?'center':'left',
    bold:c==='PASS'||c==='FAIL', color:c==='FAIL'?RED:(c==='PASS'?GREEN:INK)}}:c)),
    {x:0.55,y:y+2.92,w:6.03,colW:[2.34,1.40,1.19,1.10],rowH:0.32,...TB,fontSize:11});
  s.addText('최초 baseline 의 결측은 채우거나 삭제하지 않고 원본 그대로 보존한 뒤 재측정하였다. 호기 세션 최고 1,493 ppm, 종료 634 ppm.\nESP32 펌웨어 빌드 자원 : RAM 32,356 / 327,680 B (9.9 %), Flash 268,765 / 1,310,720 B (20.5 %).',
    {x:0.55,y:y+4.58,w:6.03,h:0.80,fontFace:F,fontSize:10.5,color:INK,lineSpacing:15,valign:'top'});

  sub(s,6.85,y,'② mmWave 수신 안정성 및 리플레이 결과');
  s.addImage({ path: PV+'/chart_mmwave.png', x:6.85, y:y+0.34, w:5.93, h:1.98 });
  box(s,6.85,y+2.42,5.93,0.92,SOFT,LINE);
  s.addText('라이브 UART 수신 (2026-08-08)',{x:7.03,y:y+2.46,w:5.6,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('9.990 Hz · 1,201 레코드 · 199/199 창 파싱 · 시퀀스 누락 0 · UART / checksum / parser 오류 0 / 0 / 0',
    {x:7.03,y:y+2.72,w:5.6,h:0.56,fontFace:F,fontSize:11,color:INK,lineSpacing:17,valign:'top'});
  sub(s,6.85,y+3.46,'③ Thermal 실기기 E2E (Production 경로)');
  box(s,6.85,y+3.78,5.93,1.46,SOFT,LINE);
  s.addText('Raspberry Pi 5, 30.06 s / 138회 측정',{x:7.03,y:y+3.82,w:5.6,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:NAVY});
  s.addText('p50 162.70 ms · p95 173.90 ms · 평균 167.92 ms  (per-frame min-max)\n유효 프레임 135 / 138 (97.8 %) · 처리량 4.6 FPS\nfail-closed 6종 실기기 PASS (순서위반 · NaN/Inf · 형식오류 · 단선 · 복구 · close 후 read)',
    {x:7.03,y:y+4.06,w:5.6,h:1.12,fontFace:F,fontSize:10.5,color:INK,lineSpacing:16,valign:'top'});
}

/* ============ P12 ============ */
{
  const {s,y} = page(12,'4.1  열화상 전송 구조 개선');
  const st=[
    ['문제', '열화상 프레임을 계속 전송하면 1초 주기 telemetry(호흡·심박·CO₂·PIR)가 밀린다. 화면 값이 갱신되지 않거나 stale 로 떨어졌다.', RED],
    ['원인', '패킷 하나가 9,952 B (메타 16 B + 4,960 × 2 B + 헤더 16 B). 당시 분주비 4로 25 FPS 센서에서 초당 약 6.25 프레임을 요청하여 약 60 KB/s 를 ESP32 Wi-Fi 단일 TCP 연결에 투입하였다. 열화상 write 가 블로킹되면 뒤의 telemetry write 도 함께 지연된다.', NAVY],
    ['시도', '① TCP write 를 별도 FreeRTOS 태스크로 분리   ② 열화상 큐를 길이 1로 두고 xQueueOverwrite 로 최신 프레임만 유지   ③ 512 B 청크 분할 전송   ④ 분주비 4 → 8 (약 3.125 FPS)   ⑤ SPI 8 MHz → 1 MHz', GREY],
    ['실패', '수집이 네트워크 때문에 멈추는 현상은 사라졌지만, 스트리밍을 켠 상태에서 1초 주기는 여전히 유지되지 않았다. 큐를 줄인 것은 지연을 감춘 것이지 전송량을 줄인 것이 아니었다. 링크에 실리는 총 바이트는 그대로였다.', AMBER],
    ['해결', '열화상을 1초 telemetry 와 같은 TCP 연결에 싣지 않고 전송 경로를 분리하였다. 80×62 uint16 프레임(payload 9,936 B)을 SafeNest Thermal UDP v1 로 UDP 5005 에 실어 1,200 B 데이터그램 9 조각으로 나누어 보내고, 32 B 헤더의 frame id · chunk index · offset · length · CRC32 로 조각 단위 무결성을 확인한 뒤 재조립한다.', GREEN]];
  st.forEach((r,i)=>{
    const yy=y+0.02+i*0.72;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.05,h:0.66,fill:{color:r[2]},line:{color:r[2]},rectRadius:0.06});
    s.addText(r[0],{x:0.55,y:yy,w:1.05,h:0.66,fontFace:F,fontSize:13,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.68,yy,11.10,0.66,i===4?'EAF5EF':SOFT,i===4?GREEN:LINE);
    s.addText(r[1],{x:1.86,y:yy,w:10.74,h:0.66,fontFace:F,fontSize:12,color:INK,valign:'middle',lineSpacing:16.5});
  });
  const yy=y+3.74;
  box(s,0.55,yy,6.05,1.10,'FBE9E7',RED);
  s.addText('개선 전',{x:0.75,y:yy+0.06,w:2,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:RED});
  s.addText('열화상 프레임을 1초 telemetry 와 같은 TCP 연결로 초당 약 6.25회 전송 시도\n→ 1초 telemetry 주기 붕괴, 화면 값 지연',
    {x:0.75,y:yy+0.34,w:5.65,h:0.68,fontFace:F,fontSize:11.5,color:INK,lineSpacing:17});
  box(s,6.73,yy,6.05,1.10,'EAF5EF',GREEN);
  s.addText('개선 후',{x:6.93,y:yy+0.06,w:2,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:GREEN});
  s.addText('열화상은 UDP 5005 전용 경로로 분리. telemetry TCP 9000 은 1초 주기 유지\n프레임은 조각 CRC32 검증 후 재조립하며, 분주비 4로 대역폭을 통제한다.',
    {x:6.93,y:yy+0.34,w:5.65,h:0.68,fontFace:F,fontSize:11.5,color:INK,lineSpacing:17});
  note(s,'근거 : ESP32/Arduino/esp32_sensor_node/esp32_sensor_node.ino 의 THERMAL_UDP_MAGIC "SNTU" · THERMAL_UDP_VERSION 1 · 32 B 헤더 · 1,200 B 데이터그램 · CRC32 · ESP32/docs/COMMUNICATION_PROTOCOL.md.', 6.66);
}

/* ============ P13 ============ */
{
  const {s,y} = page(13,'4.2  자원·버스·재현성 장애요인');
  const cases=[
    ['① GPIO 자원 제약으로 자동 복구 기능이 막힌 문제', 1.52, NAVY,
     'XIAO ESP32-C6 의 외부 디지털 핀 11개 중 D6/D7 은 보드 내부에서 MR60BHA2 와 UART 로 묶여 외부 사용이 불가능하고, D3 은 레이더 부트·리셋 회로에, D1 은 온보드 RGB LED 에 물려 있었다.',
     'nRESET 을 연결하지 않는 방안을 시도하였으나, 초기화가 I²C 주소를 찾기 전에 RESET 을 LOW 20 ms → HIGH 300 ms 로 토글해야 해서 부팅 시퀀스가 성립하지 않았다. 사람이 버튼을 눌러야 복구되는 장치는 무인 감시에 쓸 수 없다.',
     'ESP32 DevKit V1(30-pin)으로 교체하고 10개 신호선을 모두 단독 핀에 배정하였다. RESET(GPIO25) 제어를 확보하여 30초 무프레임 자동 재초기화가 동작한다.'],
    ['② 브레드보드 배선이 버스 속도를 견디지 못한 문제', 1.38, NAVY,
     'SPI 8 MHz, I²C 400 kHz 에서 MI48 과 SCD4x 양쪽에서 판독 누락이 재현되었다. 배선을 다시 꽂고 길이를 줄여도 동일하였다.',
     '속도를 낮추면 프레임 판독 시간이 늘어 요청 주기를 넘길 위험이 있었으므로, 시간 예산 안에 들어오는지를 함께 계산해야 했다.',
     'SPI 1 MHz, I²C 100 kHz 로 조정하였다. 1 MHz 에서 한 프레임 판독이 약 81 ms 로, 분주비 8이 요구하는 160 ms 예산 안에 들어가 READOUT_TOO_SLOW 정지가 사라졌다.'],
    ['③ 학습이 끝난 모델이 재현 검증을 통과하지 못한 문제', 1.58, RED,
     'mmWave 호흡 이상 분류 모델 v0.1.0 을 저장소 데이터로 재현 평가한 결과, 468개 표본 전부를 NORMAL 로 예측하는 클래스 붕괴가 확인되었다. 정확도 0.3996, macro-F1 0.19, RAPID·APNEA 재현율 0.0 이다.',
     '아티팩트는 존재하였고 SHA-256 과 텐서 계약도 일치하였다. 모델 파일의 존재만으로 검증 통과를 판단할 수 없음을 확인하였다.',
     '매니페스트에 deployment_allowed = false 와 차단 사유 CLASS_COLLAPSE_ON_REPOSITORY_NPZ 를 기록해 배포를 차단하고 후보를 다시 세웠다.']];
  let cy=y+0.04;
  cases.forEach((c)=>{
    const H=c[1];
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:cy,w:12.23,h:0.36,fill:{color:c[2]}});
    s.addText(c[0],{x:0.72,y:cy,w:12,h:0.36,fontFace:F,fontSize:12.5,bold:true,color:'FFFFFF',valign:'middle'});
    const labs=['문제·원인','시도·실패','해결'];
    for(let k=0;k<3;k++){
      const x=0.55+k*4.13;
      box(s,x,cy+0.40,3.86,H-0.44,k===2?'EAF5EF':SOFT,k===2?GREEN:LINE);
      s.addText(labs[k],{x:x+0.14,y:cy+0.45,w:2,h:0.22,fontFace:F,fontSize:10,bold:true,color:k===2?GREEN:GREY});
      s.addText(c[k+3],{x:x+0.14,y:cy+0.66,w:3.58,h:H-0.72,fontFace:F,fontSize:10,color:INK,lineSpacing:13.5,valign:'top'});
    }
    cy+=H+0.14;
  });
  s.addText('세 사례 모두 증상을 감추는 대신 원인을 제거하는 방향으로 해결하였고, 검증되지 않은 구성요소를 안전 판단 경로에 올리지 않는다는 원칙을 개발 전 과정에 적용하였다.',
    {x:0.55,y:cy+0.02,w:12.23,h:0.44,fontFace:F,fontSize:12,bold:true,color:NAVY,lineSpacing:18,valign:'top'});
  note(s,'근거 : esp32_sensor_node.ino (핀 상수 · THERMAL_SPI_HZ · Wire.setClock · recoverThermalIfStale) · RaspberryPi/Ondevice_AI/models/model_manifest.json (validation_status: BLOCKED).', 6.66);
}

/* ============ P14 ============ */
{
  const {s,y} = page(14,'5.1  기술적 차별성');
  const big=[
    ['fail-closed 판단 보류','증거가 무효이거나 결측이면 마지막 정상값을 재사용하지 않는다. 네 채널이 모두 무효이면 risk_score 와 risk_level 을 None 으로 두고 system_health 를 FAILED 로 기록한다. 무응답을 정상으로 해석하지 않는다.','RaspberryPi/Ondevice_AI/risk/fallback.py','SW 검증','sw'],
    ['유효성·신선도의 1급 상태 관리','값과 함께 valid 플래그를 전송하며, 유효하지 않은 수치는 0으로 대체하지 않고 null 로 보낸다. ESP32 와 Raspberry Pi 가 신선도를 각각 독립적으로 판정하고, STALE 입력은 판단에서 제외한다.','formatNullableFloat() · SensorStore','SW 검증','sw'],
    ['RGB 카메라 없는 이종 센서 증거 융합','개인 식별이 가능한 RGB 카메라를 쓰지 않는다. mmWave 의 미세 움직임, 열화상의 열 분포, CO₂ 의 환경 추세, PIR 의 움직임 이벤트가 서로 다른 실패 모드를 상쇄한다. 80×62 열화상은 개인 식별에 쓰기 어려운 해상도라 촬영이 통제되는 구역에도 적용할 수 있다.','RaspberryPi/Ondevice_AI/risk/risk_engine.py','SW 검증','sw']];
  big.forEach((r,i)=>{
    const yy=y+0.06+i*1.22;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:0.56,h:1.12,fill:{color:BLUE},line:{color:BLUE},rectRadius:0.06});
    s.addText(String(i+1),{x:0.55,y:yy,w:0.56,h:1.12,fontFace:F,fontSize:20,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.19,yy,7.11,1.12,SOFT,LINE);
    s.addText(r[0],{x:1.36,y:yy+0.10,w:2.86,h:0.58,fontFace:F,fontSize:13,bold:true,color:NAVY,valign:'top',lineSpacing:17});
    s.addText(r[2],{x:1.36,y:yy+0.72,w:2.86,h:0.26,fontFace:M,fontSize:8.5,color:BLUE,valign:'middle'});
    s.addText(r[1],{x:4.34,y:yy+0.06,w:3.80,h:1.00,fontFace:F,fontSize:10,color:INK,lineSpacing:14,valign:'middle'});
  });
  const small=[['검증 등급에 따른 배포 통제','모델마다 검증 범위와 배포 허용 여부를 매니페스트에 기록한다. 재현 검증에 실패한 모델은 실제로 배포가 차단되었다.','RaspberryPi/Ondevice_AI/models/model_manifest.json','오프라인 검증','warn'],
               ['프레임 무결성과 자동 복구','CRC-16/CCITT-FALSE 검사, 헤더 범위 재계산, 시퀀스 교차 확인을 거치며 30초 무프레임 시 GPIO RESET 으로 센서를 재초기화한다.','thermalFrameCrc() · recoverThermalIfStale()','실기기 검증','hw']];
  small.forEach((r,i)=>{
    const yy=y+3.86+i*0.76;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:0.56,h:0.66,fill:{color:'9AA5B1'},line:{color:'9AA5B1'},rectRadius:0.06});
    s.addText(String(i+4),{x:0.55,y:yy,w:0.56,h:0.66,fontFace:F,fontSize:14,bold:true,color:'FFFFFF',align:'center',valign:'middle'});
    box(s,1.19,yy,7.11,0.66,'FFFFFF',LINE);
    s.addText(r[0],{x:1.36,y:yy,w:2.50,h:0.66,fontFace:F,fontSize:11.5,bold:true,color:NAVY,valign:'middle',lineSpacing:15});
    s.addText(r[1],{x:3.98,y:yy,w:4.16,h:0.66,fontFace:F,fontSize:10,color:INK,valign:'middle',lineSpacing:13.5});
  });
  [...big,...small].forEach((r,i)=>{
    const yy = i<3 ? y+0.47+i*1.22 : y+4.04+(i-3)*0.76;
    badge(s,8.44,yy,r[3],r[4]);
  });
  s.addImage({ path:A+'/ui_lcd_6_failed.jpg', x:9.90, y:y+0.06, w:2.88, h:1.66 });
  s.addShape(pptx.ShapeType.rect,{x:9.90,y:y+0.06,w:2.88,h:1.66,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 3] 전 센서 무효 시 표시 화면. 정상으로 표시하지 않고 점검 필요 상태를 출력한다. 표시 계층 검증용 시나리오 화면이며 실센서 측정값이 아니다.',
    {x:9.90,y:y+1.78,w:2.88,h:1.00,fontFace:F,fontSize:9.5,color:GREY,lineSpacing:13,valign:'top'});
  note(s,'각 항목은 03_CLAIM_EVIDENCE_LEDGER 의 근거 파일과 1:1로 연결되어 있다.', 6.72);
}

/* ============ P15 ============ */
{
  const {s,y} = page(15,'5.2  기존 방식 및 유사 사례 비교');
  const rows=[[hdr('비교 축'),hdr('가스감지기'),hdr('CCTV'),hdr('PIR'),hdr('웨어러블'),hdr('Vayyar Care'),hdr('TI IWR6843'),hdr('SafeNest')],
   ['사생활 보호 (비영상)','○','×','○','○','○','○','○'],
   ['정지 인체에 대한 증거','×','△','×','○','○','○','○'],
   ['환경 위험 감시','○','×','×','×','×','×','○'],
   ['다중 증거 교차 확인','×','×','×','×','×','×','○'],
   ['무효·결측 데이터 인지','×','×','×','△','확인 불가','확인 불가','○'],
   ['증거 부재 시 판단 보류','×','×','×','×','확인 불가','확인 불가','○']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    const mk=(c==='○'||c==='×'||c==='△');
    let col=INK, fill=undefined, fs=12;
    if(mk){ col = c==='×'?RED:(c==='△'?AMBER:GREEN); fs=15; }
    if(c==='확인 불가'){ col=GREY; fs=9.5; }
    if(ci===7 && ri>0) fill={color: c==='×' ? 'FBE9E7' : LBLUE};
    return {text:c,options:{align:(mk||c==='확인 불가')?'center':'left',color:col,bold:mk,fill,fontSize:fs}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[3.03,1.28,1.05,1.00,1.25,1.42,1.55,1.65],rowH:0.25,...TB});
  s.addText([{text:'SafeNest 는 감지 성능보다 증거를 다루는 정책에서 차이를 둔다. ',options:{bold:true,color:NAVY}},
   {text:'조사한 세 사례 모두 공개 자료에서 무효·결측 인지와 판단 보류 정책을 확인할 수 없었다. SafeNest 는 이 두 축을 설계 요구사항으로 명시하고 구현·검증하였다.',options:{color:INK}}],
   {x:0.55,y:y+2.80,w:12.23,h:0.48,fontFace:F,fontSize:12,lineSpacing:18,valign:'top'});
  const ref=[['Vayyar Care\n(상용 제품)','60 GHz 4D 이미징 레이더 기반 낙상 감지 장치. 카메라·마이크·웨어러블을 쓰지 않고 1대가 약 16 m²를 감시하며 낙상을 3단계로 구분한다. 환경 가스 감시 기능은 제품 설명에서 확인되지 않는다.'],
    ['TI IWR6843\n(상용 부품)','60~64 GHz FMCW 단일칩 mmWave 센서. 재실 감지와 생체신호 검출 레퍼런스 디자인이 공개되어 있다. 센서 단위 부품이므로 환경 센서 융합과 판단 보류 정책은 범위 밖이다.'],
    ['학술 연구\n(arXiv 2403.05634, 2024)','TI mmWave 레이더 3대로 다중 인체 추적과 낙상 감지를 수행하여 정확도 96.3 %를 보고하였다. 단일 모달리티 실험이며 센서 무효·결측 시의 처리 정책은 다루지 않는다.']];
  ref.forEach((r,i)=>{
    const yy=y+3.42+i*0.54;
    s.addText(r[0],{x:0.55,y:yy,w:2.55,h:0.50,fontFace:F,fontSize:10.5,bold:true,color:NAVY,valign:'middle',lineSpacing:13});
    box(s,3.20,yy,9.58,0.50,SOFT,LINE);
    s.addText(r[1],{x:3.38,y:yy,w:9.22,h:0.50,fontFace:F,fontSize:10.5,color:INK,valign:'middle',lineSpacing:14});
  });
  note(s,'○ 충족 · △ 조건부 충족 · × 미충족 · 확인 불가는 공개 자료에서 판정 근거를 찾지 못한 항목이다.  출처 : vayyar.com/care-pages/how, ti.com/tool/IWR6843ISK, arXiv:2403.05634.');
}

/* ============ P16 ============ */
{
  const {s,y} = page(16,'5.3  구현 결과 및 검증 수준');
  const rows=[[hdr('구성요소'),hdr('구현'),hdr('검증 수준'),hdr('증거'),hdr('확장 방향')],
   ['ESP32 4센서 통합 노드','완료','SW 검증','esp32_sensor_node.ino 1,042줄 · RAM 9.9 % / Flash 20.5 % · 자기진단 9종','다중 노드 확장'],
   ['TCP v1 송·수신 및 유효성 검사','완료','SW 검증','수신기 테스트 4건 통과 · CRC-16 · 범위 재계산 · 이중 TTL','장시간 운용 모니터링'],
   ['Risk Engine · fail-closed','완료','SW 검증','위험도 테스트 22건 실행 통과','현장 데이터 기반 임계값 조정'],
   ['mmWave 채널','완료','실기기 검증','9.990 Hz · 1,201 레코드 · 오류 0 · 리플레이 MAE 0.270 rpm','상시 운용 데이터 축적'],
   ['CO₂ 채널','완료','실기기 검증','실측 4세션 · 재측정 결측 0 % · 호기 최고 1,493 ppm','결측 계약 고도화'],
   ['Thermal 채널','완료','실기기 E2E','Production 경로 · Pi 5 p50 162.70 / p95 173.90 ms · 유효 97.8 % · fail-closed 6종','도메인 정합 데이터 확대'],
   ['Web · LCD · 부저 · 외함','완료','SW 검증 + 실물','상태 6종 표시·경보 확인 · 하우징 2종 출력·조립 완료','관제 화면 다중 노드 대응'],
   ['4센서 통합 실기기 E2E','완료','실기기 E2E','[검증 후 입력]','다중 노드 동시 수용']];
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    let col=INK,bold=false;
    if(ci===2){ if(c.indexOf('실기기')>=0||c.indexOf('실물')>=0){col=GREEN;bold=true;} else {col=BLUE;bold=true;} }
    if(ci===1 && c==='완료'){ col=GREEN; bold=true; }
    return {text:c,options:{color:col,bold,align:(ci===1||ci===2)?'center':'left'}};
  })),{x:0.55,y:y+0.04,w:12.23,colW:[2.72,0.92,1.48,4.51,2.60],rowH:0.22,...TB,fontSize:9.5});
  box(s,0.55,y+2.62,12.23,0.72,LBLUE,BLUE);
  s.addText('테스트 실행 기준',{x:0.78,y:y+2.65,w:4.2,h:0.26,fontFace:F,fontSize:11,bold:true,color:BLUE});
  s.addText('정본 트리에서 하드웨어 없이 실행 가능한 테스트 40건을 직접 실행하여 전부 통과하였다 (LCD 4 · 위험도 22 · CO₂ 10 · mmWave 4).\n재편 이전 트리의 실패 2건은 결과를 보정하지 않고 실패로 기록하였다. 테스트 함수 1,483개는 소스에 정의된 개수이므로 실행 건수와 구분한다.',
    {x:0.78,y:y+2.88,w:11.77,h:0.42,fontFace:F,fontSize:9.5,color:INK,lineSpacing:13,valign:'top'});
  s.addImage({ path:A+'/hw_product_full_crop.jpg', x:0.55, y:y+3.38, w:3.08, h:1.40 });
  s.addShape(pptx.ShapeType.rect,{x:0.55,y:y+3.38,w:3.08,h:1.40,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 4] 완성품. 좌측 표시부, 우측 센서 노드. 하우징 2종은 자체 설계 STL 출력물이다.',
    {x:0.55,y:y+4.84,w:3.08,h:0.62,fontFace:F,fontSize:9,color:GREY,lineSpacing:12,valign:'top'});
  const lcds=[['ui_lcd_2_normal_occupied.jpg','안전 · 재실'],
              ['ui_lcd_3_caution.jpg','주의 · CO₂ 높음'],
              ['ui_lcd_4_danger.jpg','위험 · 호흡 이상'],
              ['ui_lcd_5_emergency.jpg','긴급 · 복합 위험']];
  lcds.forEach((v,i)=>{
    const x=4.09+i*2.19;
    s.addImage({ path:A+'/'+v[0], x, y:y+3.38, w:2.06, h:1.20 });
    s.addShape(pptx.ShapeType.rect,{x,y:y+3.38,w:2.06,h:1.20,fill:{type:'none'},line:{color:LINE,width:1}});
    s.addText(v[1],{x,y:y+4.60,w:2.06,h:0.26,fontFace:F,fontSize:10.5,bold:true,color:NAVY,align:'center'});
  });
  s.addText('[그림 5] 위험도 등급별 표시·경보 화면. 주의는 화면 경고, 위험부터는 부저 경보가 함께 출력된다. 화면 값은 표시 계층 검증용 시나리오 입력이며 실센서 측정값이 아니다.',
    {x:4.09,y:y+4.86,w:8.69,h:0.44,fontFace:F,fontSize:9,color:GREY,align:'center',lineSpacing:12,valign:'top'});
  note(s,'검증 수준 : SW 검증은 소프트웨어 테스트 통과, 실기기 검증은 실제 센서·보드에서 확인, 실기기 E2E 는 실센서부터 추론까지 관통을 뜻한다.');
}

/* ============ P17 ============ */
{
  const {s,y} = page(17,'6.1  적용 분야 및 기대효과');
  box(s,0.55,y+0.02,12.23,0.94,LBLUE,BLUE);
  s.addText('RGB 카메라를 쓰지 않기 때문에 열리는 적용 영역',{x:0.78,y:y+0.06,w:6,h:0.30,fontFace:F,fontSize:12.5,bold:true,color:BLUE});
  s.addText('SafeNest 는 개인을 식별할 수 있는 RGB 카메라를 쓰지 않는다. 열화상은 80×62 저해상도 표면 온도 분포이고, mmWave·CO₂·PIR 은 형상을 남기지 않는다.\n그래서 RGB 영상 기반 감시에 비해 개인정보 노출 가능성이 낮고, 촬영 장비 반입이 통제되는 공간에서도 사람의 존재와 상태를 감시할 수 있다.',
    {x:0.78,y:y+0.36,w:11.77,h:0.54,fontFace:F,fontSize:11.5,color:INK,lineSpacing:16,valign:'top'});

  sub(s,0.55,y+1.08,'적용 분야');
  const uses=[
    ['① 밀폐공간 무인 감시', BLUE,
     '산업안전보건법 시행규칙 별표18이 정한 맨홀·정화조·집수정 등',
     '제619조가 산소·유해가스 농도 측정과 감시인 배치를 사업주 의무로 정하지만 감시인 상시 배치가 어려운 소규모 사업장이 대다수다. 공기질과 사람의 상태를 함께 확인해 가스 감지기 단독 운용의 공백을 메운다.'],
    ['② 보안 통제구역 · 연구시설 (확장 적용 분야)', NAVY,
     '촬영 장비 반입이 통제되어 CCTV 로 인원 상태를 볼 수 없는 구역',
     '보안 규정을 건드리지 않고 재실·이상 상태만 감시한다. RGB 영상을 남기지 않아 반출 심사 부담이 작다. 1인 작업이 잦은 클린룸·시험동이 우선 적용 대상이며, 반도체 팹·군사시설은 현장 검증 전 단계의 적용 후보다.'],
    ['③ 어린이 통학차량 잔류 감지', GREEN,
     '도로교통법 제53조가 하차 확인과 하차확인장치 작동을 의무화',
     '현행 장치는 운전자가 버튼을 눌러 확인하는 방식이라 사람의 행위에 의존한다. mmWave 채널 단독 리플레이 평가에서 좌석 거리에 해당하는 0.6~0.9 m 구간 재실 검출률 1.000 을 얻었다. 잔류 여부를 사람의 조작 없이 센서가 판정한다.']];
  uses.forEach((u,i)=>{
    const yy=y+1.42+i*1.20;
    s.addShape(pptx.ShapeType.rect,{x:0.55,y:yy,w:0.06,h:1.10,fill:{color:u[1]}});
    s.addText(u[0],{x:0.74,y:yy,w:5.84,h:0.28,fontFace:F,fontSize:12.5,bold:true,color:u[1]});
    s.addText(u[2],{x:0.74,y:yy+0.28,w:5.84,h:0.22,fontFace:F,fontSize:10,color:GREY,valign:'top'});
    s.addText(u[3],{x:0.74,y:yy+0.52,w:5.84,h:0.58,fontFace:F,fontSize:10.5,color:INK,lineSpacing:14,valign:'top'});
  });

  s.addImage({ path:A+'/ui_web.png', x:6.85, y:y+1.08, w:5.93, h:3.00 });
  s.addShape(pptx.ShapeType.rect,{x:6.85,y:y+1.08,w:5.93,h:3.00,fill:{type:'none'},line:{color:LINE,width:1}});
  s.addText('[그림 6] 관제 웹 화면. QR 로 공간을 식별해 밀폐공간 A-01, 통학차량 B-02, 창고 C-03 을 등록·조회한다. 화면에는 RGB 영상 없이 상태값만 남는다.',
    {x:6.85,y:y+4.20,w:5.93,h:0.40,fontFace:F,fontSize:9.5,color:GREY,lineSpacing:13,valign:'top'});
  note(s,'근거 : 산업안전보건법 제619조 · 시행규칙 별표18 · 도로교통법 제53조 제4항·제5항. 감지 거리 : archive/legacy_main_repo/devices/mmwave/validation_results/replay_v5/benchmark_summary.csv.');
}

/* ============ P18 ============ */
{
  const {s,y} = page(18,'6.2  판매가치 · 시장성 및 발전 가능성');
  sub(s,0.55,y,'판매가치 : 도입 비용 (실구매 결제액 기준)');
  const bom=[[hdr('구분'),hdr('구성품'),hdr('금액(원)')],
   ['감지 노드','Thermal-90 열화상 모듈 (Waveshare 80×62 · 90° FOV)','104,223'],
   ['','MR60BHA2 60 GHz mmWave 센서','56,013'],
   ['','SCD40 CO₂ 센서 · PIR 인체감지 센서 (HC-SR501)','19,894'],
   ['','ESP32 DevKit V1 · 실리콘 점퍼 배선 · 하우징 3D 출력','33,578'],
   ['','소계','213,708'],
   ['관제 노드','Raspberry Pi 5 8GB','178,170'],
   ['','7인치 IPS 정전식 터치 LCD 1024×600 · 피에조 부저','40,700'],
   ['','표시부 하우징 3D 출력 (PLA)','15,000'],
   ['','소계','233,870'],
   ['합계','1개 공간 1식','447,578']];
  s.addTable(bom.map((r,ri)=>r.map((c,ci)=>{
    if(typeof c!=='string') return c;
    const isSum = (c==='소계'||r[0]==='합계');
    return {text:c,options:{bold:isSum||ci===0, align:ci===2?'right':'left',
      color:isSum?NAVY:INK, fill:isSum?{color:SOFT}:undefined}};
  })),{x:0.55,y:y+0.36,w:6.03,colW:[1.02,3.61,1.40],rowH:0.24,...TB,fontSize:9});

  box(s,0.55,y+4.14,6.03,1.12,'EAF5EF',GREEN);
  s.addText('공간을 늘릴 때 추가되는 비용',{x:0.75,y:y+4.18,w:4,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:GREEN});
  s.addText([
    {text:'관제 노드 1대가 다수의 감지 노드를 수용하므로, 감시 공간을 늘릴 때 드는 추가 비용은 감지 노드 213,708원뿐이다.\n',options:{color:INK}},
    {text:'1개 공간 447,578원 · 3개 874,994원(공간당 291,665원) · 5개 1,302,410원(공간당 260,482원)\n',options:{color:INK}},
    {text:'보조 안전설비의 초기 도입비이며, 5개 공간 기준 공간당 260,482원으로 감시인 1명 월 인건비의 약 12 % 수준이다.',options:{bold:true,color:GREEN}}
  ],{x:0.75,y:y+4.44,w:5.63,h:0.74,fontFace:F,fontSize:10,lineSpacing:14,valign:'top'});

  sub(s,6.85,y,'발전 가능성 : 센서 등급 상향에 따른 적용 범위 확장');
  const up=[[hdr('구성'),hdr('현재 구성의 실측 한계'),hdr('상위 센서 채택 시')],
   ['mmWave','MR60BHA2 60 GHz 단일 안테나.\n0.6~0.9 m 검출률 1.000, 1.2 m 0.814,\n1.5 m 에서 lock loss 로 유효 창 0','다중 송수신 FMCW(예: TI IWR6843) 채택 시\n검출 거리와 다중 인원 동시 추적 범위 확대'],
   ['열화상','Waveshare 80×62 · 90° FOV.\n저해상도라 원거리 인체 형상 분리가 어렵다','160×120 이상 LWIR 채택 시\n원거리 자세 분류와 다인 분리 가능'],
   ['적용 공간','소형 밀폐공간 · 차량 실내 등\n단일 노드로 덮이는 범위','창고·작업장·클린룸 등 중대형 공간.\n노드 분산 배치와 상위 센서를 함께 적용']];
  s.addTable(up.map(r=>r.map(c=>typeof c==='string'?{text:c}:c)),
    {x:6.85,y:y+0.36,w:5.93,colW:[0.92,2.55,2.46],rowH:0.50,...TB,fontSize:9});
  s.addText('판단 계층이 센서에 독립적인 계약(base_sensor · InferenceResult)으로 분리되어 있어, 센서를 상위 등급으로 교체해도 위험도 산출과 fail-closed 정책은 그대로 재사용한다.',
    {x:6.85,y:y+2.52,w:5.93,h:0.50,fontFace:F,fontSize:10,color:INK,lineSpacing:14,valign:'top'});

  sub(s,6.85,y+3.06,'시장성 : 수요가 법령으로 발생하는 시장');
  const mk=[['밀폐공간', BLUE,'산업안전보건법 제619조가 산소·유해가스 농도 측정과 감시인 배치를 사업주 의무로 규정한다. 최근 10년 질식재해 174건 · 재해자 338명 · 사망 136명.'],
    ['어린이 통학차량', GREEN,'도로교통법 제53조가 하차 확인과 어린이 하차확인장치 작동을 의무화하고 있어 장착 수요가 이미 제도화되어 있다.'],
    ['보안 통제구역', NAVY,'촬영 장비 반입이 통제되어 CCTV 로 대체할 수 없는 구간이다. RGB 영상을 남기지 않는 감시 수단에 대한 대체재가 없다.']];
  mk.forEach((m,i)=>{
    const yy=y+3.36+i*0.46;
    s.addShape(pptx.ShapeType.rect,{x:6.85,y:yy,w:0.05,h:0.42,fill:{color:m[1]}});
    s.addText(m[0],{x:7.00,y:yy,w:1.32,h:0.42,fontFace:F,fontSize:10,bold:true,color:m[1],valign:'middle'});
    s.addText(m[2],{x:8.36,y:yy,w:4.42,h:0.42,fontFace:F,fontSize:9,color:INK,valign:'middle',lineSpacing:12});
  });
  s.addText('세 시장 모두 법령과 보안 규정이 수요를 만든다. SafeNest 는 안전 인력과 측정 설비를 보조하는 장비이며, 초기 도입비는 감시인 인건비의 12~21 % 수준이다.',
    {x:6.85,y:y+4.78,w:5.93,h:0.42,fontFace:F,fontSize:9.5,color:NAVY,bold:true,lineSpacing:13,valign:'top'});
  note(s,'단가 : 2026-07-02 실구매 결제액(열화상·mmWave·CO₂·LCD·배선) · 국내 유통가(Pi 5·ESP32) · 통상가 추정(PIR·부저·3D 출력). 인건비 : 2026년 최저임금 월 환산액 2,156,880원(고용노동부 고시).', 6.70);
}

/* ============ P19 ============ */
{
  const {s,y} = page(19,'7.1  개발 일정 및 주요 설계 변경');
  sub(s,0.55,y,'실제 수행 일정');
  const tl=[['7월','요구사항 정의 · 시스템 설계 · 부품 확보 · 개발환경 구축 · 센서별 드라이버 착수'],
    ['8/01','mmWave 장시간 실측. 빈 공간 30분 / 재실 31분 원시 로그 확보'],
    ['8/02–8/03','저장소 통합 및 기기·책임 영역 재편 · CODEOWNERS 정의 · 회귀 테스트'],
    ['8/08','mmWave 라이브 검증(9.990 Hz, 오류 0) · 실측 로그 리플레이 벤치마크 12종'],
    ['8/11','Thermal-90 실기기 E2E 검증(Production 경로) · fail-closed 6종 · Pi 5 지연 실측'],
    ['8/12','SCD40 실기기 4세션 측정 · ESP32 → Pi TCP 실경로 확인 · 검증 리포트 작성'],
    ['8/16–8/21','mmWave 물리 측정 정합 감사 · 패키징 시점 개발 스냅샷 확정'],
    ['8/23','하우징 STL 출력·조립 완료 · 표시·경보 계층 상태 6종 확인'],
    ['8/24','4센서 통합 운용 점검 · 개발완료보고서 최종 정리'],
    ['','4센서 통합 실기기 E2E 검증 · 통합 시나리오 계측']];
  tl.forEach((t,i)=>{
    const yy=y+0.32+i*0.33;
    const last = i===tl.length-1;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:1.35,h:0.33,fill:{color:last?'FFFFFF':LBLUE},line:{color:last?NAVY:BLUE},rectRadius:0.06});
    s.addText(t[0],{x:0.55,y:yy,w:1.35,h:0.33,fontFace:F,fontSize:11,bold:true,color:last?NAVY:BLUE,align:'center',valign:'middle'});
    s.addText(t[1],{x:2.05,y:yy,w:10.7,h:0.33,fontFace:F,fontSize:12,color:INK,valign:'middle',bold:last});
  });
  sub(s,0.55,y+3.76,'개발 과정에서 내린 주요 설계 변경');
  const dec=[['MCU 교체','XIAO ESP32-C6 → ESP32 DevKit V1','GPIO 자원 부족으로 열화상 RESET 제어가 불가능해 자동 복구 요구사항을 충족할 수 없었다.'],
    ['열화상 전송 구조','TCP 스트리밍 → 전용 UDP 경로','단일 TCP 연결에 9,952 B 패킷을 초당 약 6.25회 실으면서 1초 telemetry 주기가 무너졌다.'],
    ['모델 배포 통제','mmWave v0.1.0 배포 차단','재현 검증에서 클래스 붕괴를 확인하여 검증 실패 모델을 안전 경로에 올리지 않기로 하였다.']];
  dec.forEach((d,i)=>{
    const x=0.55+i*4.13;
    box(s,x,y+4.14,3.86,0.98,SOFT,AMBER);
    s.addText(d[0],{x:x+0.14,y:y+4.17,w:3.58,h:0.28,fontFace:F,fontSize:11.5,bold:true,color:'9A5B0B'});
    s.addText(d[1],{x:x+0.14,y:y+4.44,w:3.58,h:0.24,fontFace:F,fontSize:11,bold:true,color:NAVY});
    s.addText(d[2],{x:x+0.14,y:y+4.69,w:3.58,h:0.40,fontFace:F,fontSize:10,color:INK,lineSpacing:14,valign:'top'});
  });
  note(s,'일정은 저장소 커밋 이력과 검증 문서의 실제 일자를 기준으로 작성하였으며, 계획서의 예정 간트를 그대로 옮기지 않았다.');
}

/* ============ P20 ============ */
{
  const {s,y} = page(20,'7.2  업무 분장 및 협업 구조');
  const team=[
   ['김진수','팀장','mmWave 펌웨어·어댑터·실측, 저장소 구조 통합, 문서 총괄','ESP32/reference/mmwave_platformio/ · archive/ · .github/ · 저장소 전체 기본 리뷰어','MR60 실측 로그 30분·31분, 라이브 검증(9.990 Hz), 리플레이 벤치 12종'],
   ['강유나','팀원','PIR 어댑터, 3D 하우징 CAD 설계 및 출력, LCD·Web 초기 골격','hardware/ · RaspberryPi/Ondevice_AI/sensors/pir/','STL 4종 + 설계사양 2종, 하우징 출력·조립, PIR 어댑터, LCD 초기 서버'],
   ['김태균','팀원','Thermal-90 드라이버·프레임 파서·전처리, 열화상 온디바이스 AI 검증','RaspberryPi/Ondevice_AI/sensors/thermal44/ · research/thermal_ai/','Production 경로 E2E 관통, fail-closed 6종, Pi 5 지연 실측(p95 173.9 ms)'],
   ['유승하','팀원','CO₂(SCD40) 연동·실측, ESP32 4센서 노드 펌웨어, Pi LCD·부저 서버, 회로','ESP32/ · RaspberryPi/Runtime/ · RaspberryPi/Web/','esp32_sensor_node.ino(1,042줄), CO₂ 실측 4세션·검증 리포트, TCP v1 송·수신'],
   ['한준우','팀원','데이터셋 출처·분할, 모델 학습·비교·재현, Pi AI 준비, 위험 판단 연계','RaspberryPi/Ondevice_AI/','모델 3종 매니페스트, 재현 검증·클래스 붕괴 발견 및 배포 차단']];
  const rows=[[hdr('성명'),hdr('구분'),hdr('담당 업무'),hdr('책임 영역 (저장소 경로)'),hdr('주요 산출물')]];
  team.forEach(t=>rows.push(t));
  s.addTable(rows.map((r,ri)=>r.map((c,ci)=>typeof c==='string'?{text:c,options:{bold:ci===0,align:ci<=1?'center':'left'}}:c)),
    {x:0.55,y:y+0.04,w:12.23,colW:[1.05,0.80,3.35,3.08,3.95],rowH:0.48,...TB,fontSize:10.5});
  sub(s,0.55,y+3.16,'담당 경계를 고정한 협업 인터페이스');
  const ifc=[['센서 계약','RaspberryPi/Ondevice_AI/sensors/base_sensor.py','모든 센서 담당자 ↔ AI 담당자'],
    ['텔레메트리 스키마','safenest.telemetry.v1 (valid 블록 포함)','ESP32 담당 ↔ 수신 서버 담당'],
    ['패킷 규격','SafeNest TCP protocol v1 (16 B 헤더)','ESP32 담당 ↔ Pi 수신 담당'],
    ['추론 결과 계약','InferenceResult / SensorState','센서 담당 ↔ 위험도 담당'],
    ['위험도 출력','SafeNestRiskOutput (schema 5.0)','위험도 담당 ↔ 표시·경보 담당']];
  ifc.forEach((f,i)=>{
    const yy=y+3.52+i*0.32;
    s.addShape(pptx.ShapeType.roundRect,{x:0.55,y:yy,w:2.30,h:0.30,fill:{color:LBLUE},line:{color:BLUE},rectRadius:0.05});
    s.addText(f[0],{x:0.55,y:yy,w:2.30,h:0.30,fontFace:F,fontSize:11,bold:true,color:BLUE,align:'center',valign:'middle'});
    s.addText(f[1],{x:3.05,y:yy,w:4.80,h:0.30,fontFace:M,fontSize:10,color:INK,valign:'middle'});
    s.addText(f[2],{x:8.05,y:yy,w:4.73,h:0.30,fontFace:F,fontSize:11,color:GREY,valign:'middle'});
  });
  note(s,'담당 표기는 저장소 CODEOWNERS 와 실제 산출물로 확인한 범위만 기재하였으며, 기여도를 인위적으로 균등화하지 않았다.');
}

pptx.writeFile({ fileName: OUT + '/2026ESWContest_자유공모_가만있어도SANDI_개발완료보고서.pptx' })
  .then(f => console.log('WROTE:', f));
