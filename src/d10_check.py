# d10_check.py —— D10 评测集自检（做完检查那三条，一条命令跑完）
import json, os, re

D = json.load(open('eval_set.json', encoding='utf-8'))
items = D.get('items', [])
corpus = set(os.listdir('corpus'))
ans = [x for x in items if x.get('answerable')]
noans = [x for x in items if not x.get('answerable')]

print('===== 检查 1：数量 =====')
print('总数  ', len(items), '/ 20', '  OK' if len(items) == 20 else '  MISS ' + str(20 - len(items)))
print('有答案', len(ans), '/ 15', '  OK' if len(ans) == 15 else '  MISS ' + str(15 - len(ans)))
print('无答案', len(noans), '/ 5', '  OK' if len(noans) == 5 else '  MISS ' + str(5 - len(noans)))

print()
print('===== 检查 2：expected_source 都在 corpus/ 里吗 =====')
bad = []
for x in ans:
    s = x.get('expected_source')
    if not s:
        bad.append((x['id'], '(没写)'))
    elif s not in corpus:
        bad.append((x['id'], s))
print('  OK 全部真实存在' if not bad else '  BAD ' + str(bad))

print()
print('===== 检查 3：问题像不像标题 =====')
susp = []
for x in ans:
    stem = (x.get('expected_source') or '').replace('.md', '')
    toks = [t for t in re.split(r'[-_.]', stem) if t]
    hit = [t for t in toks if t and t.lower() in x['question'].lower()]
    if hit:
        susp.append((x['id'], x['question'], hit))
print('  无自动可疑项（仍需人工通读）' if not susp else '  WARN ' + str(susp))

print()
print('===== frozen_at =====')
print('  ', repr(D.get('corpus_frozen_at', '(没填)')))
