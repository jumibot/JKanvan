// ═══════════════════════════════════
// VIEW: Tags (project-scoped)
// ═══════════════════════════════════
function vProjectTags() {
  const p = S.projects.find(x => x.id === S.pid);
  const cu = S.currentUser;
  const canManage = cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id);
  if (!S.tags.length) return `<div class="flex flex-col items-center justify-center h-full gap-4 text-center px-4">
    <span class="ms mb-1" style="font-size:42px;color:#1e2d44">label</span>
    <div class="text-white font-semibold">Sin etiquetas</div>
    <div class="text-sm text-slate-500">${canManage ? 'Crea la primera etiqueta para clasificar tareas.' : 'Este proyecto no tiene etiquetas aún.'}</div>
    ${canManage ? `<button class="btn btn-primary" onclick="mTag()"><span class="ms ms-sm">add</span>Nueva Etiqueta</button>` : ''}
  </div>`;
  return `<div class="p-6"><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    ${S.tags.map(t=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background:${t.color}1a;border:1px solid ${t.color}28">
          <div class="w-3 h-3 rounded-full" style="background:${t.color}"></div>
        </div>
        <div>
          <div class="text-sm font-medium text-white">${esc(t.name)}</div>
          <div class="text-xs text-slate-600">${t.color}</div>
        </div>
      </div>
      ${canManage ? `<div class="flex gap-0.5">
        <button class="btn-icon" onclick="mTag(${t.id})"><span class="ms ms-sm">edit</span></button>
        <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="confirmDel('tag',${t.id},'${t.name}')"><span class="ms ms-sm">delete</span></button>
      </div>` : ''}
    </div>`).join('')}
    ${canManage ? `<button class="glass-card rounded-2xl p-4 flex items-center justify-center gap-2 text-slate-600 hover:text-primary hover:border-primary/25 transition-all text-sm font-medium" style="border:2px dashed rgba(100,116,139,.18)" onclick="mTag()">
      <span class="ms ms-sm">add</span>Nueva Etiqueta
    </button>` : ''}
  </div></div>`;
}

// Standalone tags view (legacy/unused — kept for completeness)
function vTags() {
  if (!S.tags.length) return emptyState('label','Sin etiquetas','Crea la primera etiqueta para clasificar tareas.');
  return `<div class="p-6"><div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
    ${S.tags.map(t=>`<div class="glass-card rounded-2xl p-4 flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg flex items-center justify-center" style="background:${t.color}1a;border:1px solid ${t.color}28">
          <div class="w-3 h-3 rounded-full" style="background:${t.color}"></div>
        </div>
        <div>
          <div class="text-sm font-medium text-white">${esc(t.name)}</div>
          <div class="text-xs text-slate-600">${t.color}</div>
        </div>
      </div>
      <div class="flex gap-0.5">
        <button class="btn-icon" onclick="mTag(${t.id})"><span class="ms ms-sm">edit</span></button>
        <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="confirmDel('tag',${t.id},'${t.name}')"><span class="ms ms-sm">delete</span></button>
      </div>
    </div>`).join('')}
  </div></div>`;
}
