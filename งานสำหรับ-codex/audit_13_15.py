import json,sys,re,ast,runpy,subprocess,difflib
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OWN={'content/tpat3/thinking.py','content/tpat3/numeric_fluid_energy.py','content/tpat3/aptitude_lessons.py'}
lessons=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'data/lessons').glob('*.json'))]
own=[l for l in lessons if l.get('generated_from','').startswith(('content/tgat1/','content/tgat3/')) or l.get('generated_from') in OWN]
mode=sys.argv[1]
sel=[l for l in own if len(sys.argv)<3 or l['topic_id'].startswith(sys.argv[2])]
if len(sys.argv)>4 and mode!='patch14':sel=sel[int(sys.argv[3]):int(sys.argv[4])]
def ps(l):
 if mode=='metrics_old':return json.loads(subprocess.check_output(['git','show','0fcddf6:data/problems/'+l['topic_id']+'.json'],cwd=ROOT).decode('utf-8'))['problems']
 return json.loads((ROOT/'data/problems'/(l['topic_id']+'.json')).read_text(encoding='utf-8'))['problems']
if mode=='review14':
 plans=[json.loads((ROOT/'งานสำหรับ-codex'/f).read_text(encoding='utf-8')) for f in ['แก้-รอบ14.json','แก้-รอบ14-เพิ่มเติม.json']]
 ids={r['id'] for plan in plans for r in plan}
 out=[{'id':p['id'],'stem':p['stem_md'],'choices':[c['md'] for c in p['choices']]} for l in own for p in ps(l) if p['id'] in ids]
 print(json.dumps(out[int(sys.argv[2]):int(sys.argv[3])],ensure_ascii=False))
elif mode=='options':
 print(json.dumps([{'id':p['id'],'stem':p['stem_md'],'choices':[c['md'] for c in p['choices']]} for l in sel for p in ps(l)],ensure_ascii=False))
elif mode in ['metrics','metrics_old']:
 absolute=re.compile(r'เสมอ|แน่นอน|ทันที|ทุกคน|ทุกกรณี|ทุกชนิด|ทุกตัว|เท่านั้น|อย่างเดียว|\b(?:always|never|all|only|every)\b',re.I)
 rows=[]
 polite=re.compile(r'^(?:Please\b|Sorry\b|I\x27m sorry\b|Excuse me\b|Thanks\b|Thank you\b|Could (?:you|I)\b|Would (?:you|it)\b|May I\b)',re.I)
 def two(s):return len(re.findall(r'[.!?](?:\s|$)',s))>=2
 def sequence(s):
  verbs=re.findall(r'หยุด|ตรวจ|แจ้ง|สอบถาม|ชวน|เสนอ|ทดลอง|ติดตาม|วัด|กำหนด|รวบรวม|สำรวจ|เปรียบเทียบ|ประสาน|ฝึก|สื่อสาร|จัด|ปรับ|ฟัง|คุย|บอก|เลือก|ทบทวน|สรุป|ปฏิเสธ|แยก|ขอ',s)
  return len(verbs)>=2
 for l in sel:
  probs=ps(l);row={'tid':l['topic_id'],'n':len(probs)};pos=Counter();long=short=0;unique_polite=unique_sent=unique_before=unique_seq=0;wrong_abs=right_abs=multi=0
  for p in probs:
   cs=p['choices'];ai=next(i for i,c in enumerate(cs) if c['is_answer']);pos[ai+1]+=1;lens=[len(c['md']) for c in cs]
   if max(lens)>=25:
    row['length_n']=row.get('length_n',0)+1;long+=int(lens[ai]==max(lens) and lens.count(max(lens))==1);short+=int(lens[ai]==min(lens) and lens.count(min(lens))==1)
   for func,key in [(polite.search,'polite'),(two,'sent'),(lambda s:bool(re.search('ก่อน|แล้วค่อย',s)),'before'),(sequence,'seq')]:
    flags=[bool(func(c['md'])) for c in cs];row[key]=row.get(key,0)+int(flags[ai] and sum(flags)==1)
   w=sum(bool(absolute.search(c['md'])) for c in cs if not c['is_answer']);wrong_abs+=w;right_abs+=int(bool(absolute.search(cs[ai]['md'])));multi+=int(w>=2)
  row.update(pos=dict(pos),long=long,short=short,wrong_abs=wrong_abs,right_abs=right_abs,multi=multi,no_reason=sum(not re.search('เพราะ|จาก|because',p['answer_explanation_md'],re.I) for p in probs))
  rows.append(row)
 print(json.dumps(rows,ensure_ascii=False))
elif mode=='patch14':
 plan=json.loads((ROOT/'งานสำหรับ-codex'/(sys.argv[3] if len(sys.argv)>3 else 'แก้-รอบ14.json')).read_text(encoding='utf-8'))
 changes={}
 for row in plan:
  tid=row['id'][5:].rsplit('.',1)[0]
  l=next(l for l in own if l['topic_id']==tid)
  file=ROOT/l['generated_from']
  if len(sys.argv)>2 and file.name!=sys.argv[2]:continue
  src=changes.setdefault(file,{'old':file.read_text(encoding='utf-8'),'edits':[]})
  tree=ast.parse(src['old'])
  matches=[n for n in ast.walk(tree) if isinstance(n,ast.Constant) and n.value==row['old']]
  if not matches:
   for call in ast.walk(tree):
    if isinstance(call,ast.Call) and isinstance(call.func,ast.Name) and call.func.id=='d' and all(isinstance(a,ast.Constant) for a in call.args):
     formatted='  \n'.join('**'+a.value.partition(': ')[0]+':** '+a.value.partition(': ')[2] for a in call.args)
     if formatted==row['old']:matches.append(call)
  if len(matches)!=1:raise ValueError((row['id'],row['old'],len(matches)))
  n=matches[0]
  lines=src['old'].splitlines(keepends=True)
  replacement=json.dumps(row['new'],ensure_ascii=False)
  def span(node):
   return (sum(len(s.encode('utf-8')) for s in lines[:node.lineno-1])+node.col_offset,sum(len(s.encode('utf-8')) for s in lines[:node.end_lineno-1])+node.end_col_offset)
  src['edits'].append((*span(n),replacement))
  if row.get('oldReason') is not None:
   parent=next(t for t in ast.walk(tree) if isinstance(t,ast.Tuple) and n in t.elts)
   rn=parent.elts[-1]
   assert isinstance(rn,ast.Constant) and rn.value==row['oldReason']
   src['edits'].append((*span(rn),json.dumps(row['reason'],ensure_ascii=False)))
 print('*** Begin Patch')
 for file,src in changes.items():
  if len(sys.argv)>2 and file.name!=sys.argv[2]:continue
  oldlines=src['old'].splitlines()
  b=src['old'].encode('utf-8')
  for start,end,val in sorted(set(src['edits']),reverse=True):b=b[:start]+val.encode('utf-8')+b[end:]
  newlines=b.decode('utf-8').splitlines()
  print('*** Update File: '+file.as_posix())
  for line in list(difflib.unified_diff(oldlines,newlines,lineterm='',n=0))[2:]:print('@@' if line.startswith('@@') else line)
 print('*** End Patch')
elif mode in ['absolute','no_reason']:
 absolute=re.compile(r'เสมอ|แน่นอน|ทันที|ทุกคน|ทุกกรณี|ทุกชนิด|ทุกตัว|เท่านั้น|อย่างเดียว|\b(?:always|never|all|only|every)\b',re.I)
 out=[]
 for l in sel:
  for p in ps(l):
   if mode=='absolute':
    choices=[{'md':c['md'],'score':c.get('score',1 if c['is_answer'] else 0),'reason':p['distractor_reasons'].get(str(i))} for i,c in enumerate(p['choices'])]
    if any(absolute.search(c['md']) and not c['is_answer'] for c in p['choices']):out.append({'id':p['id'],'stem':p['stem_md'].split('---')[-1].strip(),'choices':choices})
   elif not re.search('เพราะ|จาก|because',p['answer_explanation_md'],re.I):
    out.append({'id':p['id'],'answer':next(c['md'] for c in p['choices'] if c['is_answer']),'explain':p['answer_explanation_md'],'clue':p['solution_steps'][0]['why_md']})
 print(json.dumps(out,ensure_ascii=False))
elif mode=='delta':
 rows=[]
 for l in own:
  rel='data/lessons/'+l['topic_id']+'.json'
  old=json.loads(subprocess.check_output(['git','show','0fcddf6:'+rel],cwd=ROOT).decode('utf-8'))
  if old==l:continue
  added=[b for b in l['blocks'] if b not in old['blocks']]
  missing={t for p in ps(l) for t in p['misconception_tags']}-{b['misconception_tag'] for b in old['blocks'] if b['type']=='pitfall'}
  rows.append({'tid':l['topic_id'],'missing':sorted(missing),'changes':[{'type':b['type'],'name':b.get('heading',b.get('title',b.get('question_md','')))} for b in added]})
 print(json.dumps(rows,ensure_ascii=False))
elif mode=='inventory':
 print('count',len(own),Counter(l['topic_id'].split('.')[0] for l in own))
 for l in own:
  tags={b['misconception_tag'] for b in l['blocks'] if b['type']=='pitfall'}
  missing={t for p in ps(l) for t in p['misconception_tags']}-tags
  print(l['topic_id'],l['generated_from'],'checks',sum(b['type']=='check' for b in l['blocks']),'missing',sorted(missing))
elif mode in ['checks','lessons','problems','brief']:
 for l in sel:
  print('\nTOPIC',l['topic_id'])
  if mode in ['problems','brief']:
   for p in ps(l):
    stem=p['stem_md'].split('---')[-1].strip() if mode=='brief' else p['stem_md']
    print(p['id'].split('.')[-1],stem,p['misconception_tags'])
  else:
   counts=Counter()
   for b in l['blocks']:
    counts[b['type']]+=1
    if mode=='checks':
     if b['type']=='check':print('CHECK',b['question_md'],b['choices'])
     if b['type']=='example':print('EXAMPLE',b['stem_md'])
    else:print(b['type'],counts[b['type']],{k:v for k,v in b.items() if k!='type'})
elif mode=='patterns':
 absolute=re.compile(r'เสมอ|แน่นอน|ทันที|ทุกคน|ทุกกรณี|ทุกชนิด|ทุกตัว|เท่านั้น|อย่างเดียว|\b(?:always|never|all|only|every)\b',re.I)
 for l in sel:
  probs=ps(l);wrong=right=multi=no=0
  for p in probs:
   c=sum(bool(absolute.search(c['md'])) for c in p['choices'] if not c['is_answer']);wrong+=c
   right+=sum(bool(absolute.search(c['md'])) for c in p['choices'] if c['is_answer'])
   if c>=2:print('MULTI',p['id'],[(c['md'],c.get('score'),p['distractor_reasons'].get(str(i))) for i,c in enumerate(p['choices'])]);multi+=1
   if not re.search('เพราะ|จาก|because',p['answer_explanation_md'],re.I):print('NO_REASON',p['id'],p['answer_explanation_md']);no+=1
  print('COUNTS',l['topic_id'],len(probs),wrong,right,multi,no)
