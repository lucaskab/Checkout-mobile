// Lists the Portuguese texts written in src/ and desktop/ (string literals and `templates ${x}` → "{0}").
// Used by missing.cjs.
const ts=require("typescript");
const fs=require("fs"),path=require("path");
const root=path.resolve(__dirname,"../..");
const dirs=["src","desktop"];
const files=[];
function walk(d){for(const f of fs.readdirSync(d,{withFileTypes:true})){const p=path.join(d,f.name);if(f.isDirectory()){if(f.name!=="i18n")walk(p);}else if(/\.(ts|tsx)$/.test(f.name)&&!/\.d\.ts$/.test(f.name))files.push(p);}}
dirs.forEach(d=>walk(path.join(root,d)));
const ID_KEYS=new Set(["id","icon","route","action","category","kind","tone","variant","art","eraId","status","sectorId","shelfId","productCategory","role","layout","style","state","lane","vehicle","origin","backdrop","tint","careSpot","gauge","unit","method","zone","ruin","targetId","type","key","sound","image","after","shift","phase","moodTone","row","focus","requestId","customerId","slotId","incidentKind","box","model","clip","color","prop","art","testID","name_id","fontFamily","source","uri","href","pathname","shelfType","fixture","fixtureId","decorId","lotId","contractId","eventId","requiredEra","minEra","eraName_id","trigger","metric","stat","reward_type","rewardType","group_id","asset","sprite","texture"]);
const out=[];
function isDisplay(s){
  if(!/[A-Za-zÀ-ÿ]/.test(s))return false;
  if(/^[a-z0-9]+([-_][a-z0-9]+)*$/.test(s))return false;     // ids, kebab/snake
  if(/^[a-z]+[A-Z][A-Za-z0-9]*$/.test(s))return false;         // camelCase
  if(/^[A-Za-z0-9_\-./@]+\/[A-Za-z0-9_\-./]*$/.test(s))return false; // paths
  if(/\.(png|jpg|json|ts|tsx|mp3|wav|fbx|glb)$/i.test(s))return false;
  if(/^#?[0-9A-Fa-f]{3,8}$/.test(s))return false;
  if(/^[!~]?[a-z-]+(:[\w-]*)*$/.test(s))return false; // routes
  if(/^(true|false|null|undefined)$/.test(s))return false;
  return true;
}
function keyOf(node){
  let p=node.parent;
  while(p&&(ts.isConditionalExpression(p)||ts.isParenthesizedExpression(p)||ts.isBinaryExpression(p)&&(p.operatorToken.kind===ts.SyntaxKind.QuestionQuestionToken||p.operatorToken.kind===ts.SyntaxKind.BarBarToken)))p=p.parent;
  if(p&&ts.isPropertyAssignment(p)&&p.initializer)return p.name.getText();
  return "";
}
function skip(node){
  const p=node.parent;
  if(!p)return true;
  if(ts.isImportDeclaration(p)||ts.isExportDeclaration(p)||ts.isExternalModuleReference(p)||ts.isLiteralTypeNode(p))return true;
  if((ts.isPropertyAssignment(p)||ts.isPropertySignature(p)||ts.isMethodDeclaration(p)||ts.isPropertyDeclaration(p)||ts.isEnumMember(p))&&p.name===node)return true;
  if(ts.isElementAccessExpression(p)&&p.argumentExpression===node)return true;
  if(ts.isCaseClause(p))return true;
  if(ts.isBinaryExpression(p)&&[ts.SyntaxKind.EqualsEqualsEqualsToken,ts.SyntaxKind.ExclamationEqualsEqualsToken,ts.SyntaxKind.EqualsEqualsToken,ts.SyntaxKind.ExclamationEqualsToken,ts.SyntaxKind.InKeyword].includes(p.operatorToken.kind))return true;
  if(ts.isCallExpression(p)){const c=p.expression.getText();if(/(^require$|includes$|startsWith$|endsWith$|getGameEvent$|split$|join$|replace$|indexOf$|has$|get$|getItem|setItem|Error$|console|test$|match$|localeCompare)/.test(c))return true;}
  const k=keyOf(node); if(ID_KEYS.has(k))return true;
  return false;
}
function tpl(node){ // template expression -> pattern
  let s=node.head.text;let i=0;for(const sp of node.templateSpans){s+=`{${i++}}`+sp.literal.text;}return s;
}
function concat(node){ // flatten + chain
  const parts=[];(function f(n){if(ts.isBinaryExpression(n)&&n.operatorToken.kind===ts.SyntaxKind.PlusToken){f(n.left);f(n.right);}else parts.push(n);})(node);
  if(!parts.some(n=>ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n)))return null;
  let s="",i=0;for(const n of parts){if(ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n))s+=n.text;else if(ts.isTemplateExpression(n))s+=tpl(n).replace(/\{\d+\}/g,()=>`{${i++}}`);else s+=`{${i++}}`;}
  return s;
}
for(const file of files){
  const text=fs.readFileSync(file,"utf8");
  const sf=ts.createSourceFile(file,text,ts.ScriptTarget.Latest,true,file.endsWith("x")?ts.ScriptKind.TSX:ts.ScriptKind.TS);
  const rel=path.relative(root,file);
  function add(s,node,kind){const lit=s.replace(/\{\d+\}/g,"");if(!isDisplay(lit.trim()||"x")&&!(kind!=="literal"&&/[A-Za-zÀ-ÿ]{2}/.test(lit)))return;if(kind!=="literal"&&!/[A-Za-zÀ-ÿ]{2}/.test(lit))return;
    out.push({text:s,file:rel,line:sf.getLineAndCharacterOfPosition(node.getStart()).line+1,kind,key:keyOf(node)});}
  (function visit(n){
    if(ts.isBinaryExpression(n)&&n.operatorToken.kind===ts.SyntaxKind.PlusToken&&!(ts.isBinaryExpression(n.parent)&&n.parent.operatorToken.kind===ts.SyntaxKind.PlusToken)){
      const c=concat(n); if(c&&/\{\d\}/.test(c)&&!skip(n))add(c,n,"concat");
    }
    if(ts.isJsxText(n)){const t=n.getText().trim();if(t&&isDisplay(t))out.push({text:t.replace(/\s+/g," "),file:rel,line:sf.getLineAndCharacterOfPosition(n.getStart()).line+1,kind:"jsx",key:""});}
    if((ts.isStringLiteral(n)||ts.isNoSubstitutionTemplateLiteral(n))&&!skip(n)){if(isDisplay(n.text))add(n.text,n,"literal");}
    else if(ts.isTemplateExpression(n)&&!skip(n)){add(tpl(n),n,"template");}
    ts.forEachChild(n,visit);
  })(sf);
}
module.exports=out;
