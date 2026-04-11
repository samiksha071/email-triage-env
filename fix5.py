f = open('inference.py', 'r', encoding='utf-8')
c = f.read()
f.close()

c = c.replace('if scores else 0.0', 'if scores else 0.05')
c = c.replace("'final_score': 0.0,", "'final_score': 0.05,")
c = c.replace('round(avg, 4)', 'round(max(0.05, min(0.95, avg)), 4)')

f = open('inference.py', 'w', encoding='utf-8')
f.write(c)
f.close()
print('Done!')