// ═══════════════════════════════════
// ROUTER
// ═══════════════════════════════════
function go(hash) { location.hash = hash; }

async function route() {
  const h = location.hash || '#/';
  if (h === '#/team') {
    if (!S.currentUser?.is_admin) { go('#/'); return; }
    S.view='team'; S.pid=null; S.tags=[]; S.priorities=[]; S.members=[]; S.subview='kanban';
  } else if (h.startsWith('#/board/')) {
    const parts = h.split('/');
    const newPid = parseInt(parts[2]);
    const sub = parts[3] || 'kanban';
    if (newPid !== S.pid) {
      S.pid = newPid;
      const [tags, priorities] = await Promise.all([
        GET(`/projects/${S.pid}/tags/`).catch(() => []),
        GET(`/projects/${S.pid}/priorities/`).catch(() => []),
      ]);
      S.tags = tags;
      S.priorities = priorities;
    }
    S.subview = sub;
    S.view = 'board';
    if (sub === 'team') await loadMembers();
  } else { S.view='dashboard'; S.pid=null; S.tags=[]; S.priorities=[]; S.members=[]; S.subview='kanban'; }
  render();
}

window.addEventListener('hashchange', route);
