f = open('server/app.py', 'r', encoding='utf-8')
c = f.read()
f.close()

old = '''    return GraderResponse(
        task_id=s.task_id, score=score,
        correct=s.correct_classifications, total=s.total_classifications,
        cumulative_reward=s.cumulative_reward,
        message=f"Episode {'complete' if s.done else 'in progress'}. Score: {score:.4f}",
    )'''

new = '''    # Score must be strictly between 0 and 1
    score = max(0.05, min(0.95, score))
    return GraderResponse(
        task_id=s.task_id, score=round(score, 4),
        correct=s.correct_classifications, total=s.total_classifications,
        cumulative_reward=s.cumulative_reward,
        message=f"Episode {'complete' if s.done else 'in progress'}. Score: {score:.4f}",
    )'''

c = c.replace(old, new)
f = open('server/app.py', 'w', encoding='utf-8')
f.write(c)
f.close()
print('Done!')