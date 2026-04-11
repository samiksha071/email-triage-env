f = open('inference.py', 'r', encoding='utf-8')
c = f.read()
f.close()

old = '        grader = env_post("/run_grader", {})\n        final_score = grader["score"]'
new = '        grader = env_post("/run_grader", {})\n        raw_score = grader["score"]\n        final_score = max(0.05, min(0.95, float(raw_score)))'

c = c.replace(old, new)
f = open('inference.py', 'w', encoding='utf-8')
f.write(c)
f.close()
print('Done!')