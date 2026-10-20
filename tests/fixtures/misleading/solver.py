# This comment claims BFS; the implementation below uses a LIFO stack.
def bfs(start):
    stack = [start]
    while stack:
        state = stack.pop()
        stack.extend(successors(state))
