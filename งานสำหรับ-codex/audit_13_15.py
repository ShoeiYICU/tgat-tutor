import json,sys,re,ast,runpy
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
OWN={'content/tpat3/thinking.py','content/tpat3/numeric_fluid_energy.py','content/tpat3/aptitude_lessons.py'}
lessons=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'data/lessons').glob('*.json'))]
own=[l for l in lessons if l.get('generated_from','').startswith(('content/tgat1/','content/tgat3/')) or l.get('generated_from') in OWN]
mode=sys.argv[1]
sel=[l for l in own if len(sys.argv)<3 or l['topic_id'].startswith(sys.argv[2])]
if len(sys.argv)>3:sel=sel[int(sys.argv[3]):int(sys.argv[4])]
def ps(l):return json.loads((ROOT/'data/problems'/(l['topic_id']+'.json')).read_text(encoding='utf-8'))['problems']
if mode=='inventory':
 print('count',len(own),Counter(l['topic_id'].split('.')[0] for l in own))
 for l in own:
  tags={b['misconception_tag'] for b in l['blocks'] if b['type']=='pitfall'}
  missing={t for p in ps(l) for t in p['misconception_tags']}-tags
  print(l['topic_id'],l['generated_from'],'checks',sum(b['type']=='check' for b in l['blocks']),'missing',sorted(missing))
elif mode in ['checks','lessons','problems']:
 for l in sel:
  print('\nTOPIC',l['topic_id'])
  if mode=='problems':
   for p in ps(l):print(p['id'].split('.')[-1],p['stem_md'],p['misconception_tags'])
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
