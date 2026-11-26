// 用記憶體模擬試算表，執行真正的 apps-script/Code.gs，並以 HTTP（含 CORS）提供服務。
// 用法：node tests/mock_gas.js [Code.gs 路徑]   測試用通關碼：家族 1234、管理 9999；GET /dump 看資料表，GET /reset 解除鎖定
const http=require('http'),fs=require('fs'),vm=require('vm');
class Sheet{constructor(n){this.name=n;this.data=[]}appendRow(r){this.data.push(r.slice())}setFrozenRows(){}getLastRow(){return this.data.length}
 getDataRange(){const d=this.data;return{getValues:()=>d.map(r=>r.slice())}}
 getRange(row,col,nr=1,nc=1){const s=this;return{getValues:()=>{const out=[];for(let i=0;i<nr;i++){const r=s.data[row-1+i]||[];out.push(Array.from({length:nc},(_,j)=>r[col-1+j]??''))}return out},
  setValue:v=>{while(s.data.length<row)s.data.push([]);s.data[row-1][col-1]=v},
  setValues:vals=>{vals.forEach((r,i)=>{while(s.data.length<row+i)s.data.push([]);r.forEach((v,j)=>{s.data[row-1+i][col-1+j]=v})})}}}
 clearContents(){this.data=[]}}
const ss={getName:()=>'嘉名投票',sheets:{},getSheetByName(n){return this.sheets[n]||null},insertSheet(n){return this.sheets[n]=new Sheet(n)}};
const ctx={SpreadsheetApp:{getActiveSpreadsheet:()=>ss},PropertiesService:{getScriptProperties:()=>({getProperty:k=>({FAMILY_CODE:'1234',ADMIN_CODE:'9999'})[k]||null})},
 LockService:{getScriptLock:()=>({waitLock(){},releaseLock(){}})},ContentService:{MimeType:{JSON:'json'},createTextOutput:t=>({t,setMimeType(){return this}})},console,
 CacheService:{getScriptCache:()=>({get:k=>cache[k]??null,put:(k,v)=>{cache[k]=v},remove:k=>{delete cache[k]}})},Utilities:{sleep(){}},Logger:{log:m=>console.log('LOG',m)}};const cache={};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[2]||require('path').join(__dirname,'..','apps-script','Code.gs'),'utf8'),ctx);
http.createServer((req,res)=>{let b='';req.on('data',c=>b+=c);req.on('end',()=>{const h={'Access-Control-Allow-Origin':'*','Content-Type':'application/json'};
 if(req.url.startsWith('/dump')){res.writeHead(200,h);return res.end(JSON.stringify(Object.fromEntries(Object.entries(ss.sheets).map(([k,v])=>[k,v.data]))))}
 if(req.url.startsWith('/reset')){ctx.resetLock();ctx.checkSetup();res.writeHead(200,h);return res.end('{}')}
 if(req.method==='OPTIONS'){res.writeHead(204,h);return res.end()}
 try{const o=req.method==='POST'?ctx.doPost({postData:{contents:b}}):ctx.doGet();res.writeHead(200,h);res.end(o.t)}catch(e){console.error(e);res.writeHead(500,h);res.end(String(e))}})}).listen(+(process.env.MOCK_PORT||8766),()=>console.log('mock on',process.env.MOCK_PORT||8766));
