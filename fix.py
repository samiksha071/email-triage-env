f = open('server/environment.py', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

for i in range(568, 578):
    lines[i] = '    ' + lines[i]

f = open('server/environment.py', 'w', encoding='utf-8')
f.writelines(lines)
f.close()
print('Done!')