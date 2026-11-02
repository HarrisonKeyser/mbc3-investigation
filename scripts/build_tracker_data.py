"""
Builds the data behind the progress tracker (docs/index.html) and the spreadsheet version
(docs/relaxation_tracker.csv): English name, pose and first coaching line of each relaxation exercise.
Usage: python3 scripts/build_tracker_data.py <game>/Common evidence/relaxation_exercises.csv docs/
The JSON it writes (tracker_data.json) is pasted into docs/index.html as `const DATA = ...`.
"""
import re,csv,json,collections,sys,os
G, CSV_IN, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
L=open(G+'/Scripts/LOCALISATION.lua',encoding='latin-1').read()
ids=dict((k,int(v)) for k,v in re.findall(r'^\s*(\w+)\s*=\s*(\d+)',L,re.M))
S=open(G+'/Localisation/LOCALISATION_EN.PLOC','rb').read()[4:].decode('utf-16-le').split('\x00')
loc=lambda k: S[ids[k]-1].strip() if k in ids else None
E=open(G+'/Scripts/Exercises.lua',encoding='latin-1').read()
E=E[E.index('\nExercises ='):]
def body(n):
    m=re.search(r'\n\s*'+n+r'\s*=\s*\{',E); p=m.end(); d=1; q=p
    while d:
        c=E[q]; d+= c=='{'; d-= c=='}'; q+=1
    return E[p:q]
R=list(csv.DictReader(open(CSV_IN)))
POSE={'Fitness':'standing','Stand':'standing','Knee':'kneeling','Sit':'sitting','LieDownL':'lying down','LieDownR':'lying down'}
out=[]
for r in R:
    n=r['exercise']; b=body(n)
    pose=re.search(r'Position\s*=\s*PoseType\.(\w+)',b); pose=pose.group(1) if pose else ''
    tm=re.search(r'Tips\s*=\s*\{([^}]*)\}',b); tips=re.findall(r'"(TIP_\w+)"',tm.group(1)) if tm else []
    name=loc('GUI_'+n)
    if not name:
        base=re.sub(r'_[LR]$','',n)
        for alt in (base, base+'_L', base+'_R'):
            if loc('GUI_'+alt): name=loc('GUI_'+alt)+(' (other side)' if alt!=base else ''); break
    tip=next((loc(t) for t in tips if loc(t)),'')
    ses=r['relaxation_session']
    if r['note'].startswith('breathing intro'): where='Intro'
    else:
        pos=r['positions'].split('|')
        where=ses+' · '+('standing or floor' if len(pos)==2 else ('standing' if pos[0]=='Stand' else 'floor'))
    out.append(dict(id=n,name=name or n,type=r['type'],where=where,levels=r['levels'].split('|') if r['levels'] else [],
                    pose=POSE.get(pose,pose.lower()),tip=tip))
print(collections.Counter(o['where'] for o in out))
print(collections.Counter(o['pose'] for o in out))
print(sum(1 for o in out if not o['tip']), 'without tip;', sum(1 for o in out if o['name']==o['id']),'without name')

dn=collections.Counter(o['name'] for o in out)
for o in out:
    if dn[o['name']]>1: o['name']+=' (%s side)'%('left' if o['id'].endswith('_L') else 'right')
json.dump(out,open(os.path.join(OUT,'tracker_data.json'),'w'),ensure_ascii=False)
dn=collections.Counter(o['name'] for o in out); print([k for k,v in dn.items() if v>1])

GROUP={'Intro':'Breathing intro (any session)','Breath · standing':'Breath session, standing','Pilates · standing':'Pilates session, standing',
       'Pilates · standing or floor':'Pilates session, standing or floor','Pilates · floor':'Pilates session, floor',
       'Suppleness · standing':'Suppleness session, standing','Suppleness · floor':'Suppleness session, floor'}
GOALS={'Intro':'any','Breath':'Peace and calm / An active and balanced life','Pilates':'any','Suppleness':'Lose weight'}
order=list(GROUP)
with open(os.path.join(OUT,'relaxation_tracker.csv'),'w',newline='',encoding='utf-8-sig') as f:
    w=csv.writer(f)
    w.writerow(['Done','Exercise','Where it comes up','Goals that give that session','Levels','Pose','Coach says','Counts toward','Game ID'])
    for o in sorted(out,key=lambda o:(order.index(o['where']),len(o['levels']),o['name'])):
        w.writerow(['',o['name'],GROUP[o['where']],GOALS[o['where'].split(' · ')[0]],', '.join(o['levels']) or 'any',o['pose'],o['tip'],o['type'],o['id']])
