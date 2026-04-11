f = open('server/environment.py', 'r', encoding='utf-8')
lines = f.readlines()
f.close()

# Find and replace the entire get_task_score function
new_function = '''    def get_task_score(self) -> float:
        """Compute final normalised score, strictly between 0 and 1."""
        if self._state.total_classifications == 0:
            return 0.05
        max_possible = self._state.total_emails * 1.0 + BONUS_HIGH_ACCURACY
        if max_possible <= 0:
            return 0.05
        raw = self._state.cumulative_reward / max_possible
        # Clamp strictly between 0 and 1 (not 0.0, not 1.0)
        score = max(0.05, min(0.95, raw))
        return round(score, 4)
'''

# Find the function start and end
start = None
end = None
for i, line in enumerate(lines):
    if 'def get_task_score' in line:
        start = i
    if start and i > start and line.startswith('    def ') and 'get_task_score' not in line:
        end = i
        break

if start and end:
    lines[start:end] = new_function.splitlines(keepends=True)
    f = open('server/environment.py', 'w', encoding='utf-8')
    f.writelines(lines)
    f.close()
    print('Done! Function replaced successfully.')
else:
    print(f'start={start} end={end} - could not find function')