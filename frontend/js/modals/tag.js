// ═══════════════════════════════════
// MODAL: Tag
// ═══════════════════════════════════

// Project tags list modal (used from project context menu)
function mProjectTags(pid) {
  const p = S.projects.find(x => x.id === pid);
  const cu = S.currentUser;
  const canManage = cu && p && (cu.id === p.owner?.id || cu.id === p.leader?.id);
  const tagRows = S.tags.length
    ? S.tags.map(t => `
        <div class="flex items-center justify-between py-2.5 border-b" style="border-color:rgba(255,255,255,.06)">
          <div class="flex items-center gap-3">
            <div class="w-5 h-5 rounded-full flex-shrink-0" style="background:${t.color}"></div>
            <div>
              <div class="text-sm text-white font-medium">${esc(t.name)}</div>
              <div class="text-xs text-slate-600">${t.color}</div>
            </div>
          </div>
          ${canManage ? `<div class="flex gap-0.5">
            <button class="btn-icon" onclick="closeM();mTag(${t.id})"><span class="ms ms-sm">edit</span></button>
            <button class="btn-icon" style="color:#6b7280" onmouseenter="this.style.color='#f87171'" onmouseleave="this.style.color='#6b7280'" onclick="closeM();confirmDel('tag',${t.id},'${esc(t.name)}')"><span class="ms ms-sm">delete</span></button>
          </div>` : ''}
        </div>`).join('')
    : `<p class="text-slate-500 text-sm text-center py-6">${canManage ? 'Sin etiquetas. Crea la primera.' : 'Este proyecto no tiene etiquetas aún.'}</p>`;
  showModal(`
    ${mhdr('Etiquetas', esc(p?.name||''))}
    <div class="max-h-64 overflow-y-auto -mx-5 px-5">${tagRows}</div>
    ${canManage ? `<button class="btn btn-primary w-full mt-4" onclick="closeM();mTag()"><span class="ms ms-sm">add</span>Nueva Etiqueta</button>` : ''}`);
}

// Tag create/edit modal
function mTag(id) {
  const t = id ? S.tags.find(x=>x.id===id) : null;
  const col = t?.color||'#3B82F6';
  showModal(`
    ${mhdr(t?'Editar Etiqueta':'Nueva Etiqueta')}
    <form onsubmit="saveTag(event,${id||'null'})">
      <input type="hidden" name="color" value="${col}">
      <div class="mb-3">
        <label class="lbl">Nombre</label>
        <input name="name" class="inp" placeholder="ej. Backend" value="${esc(t?.name||'')}" required>
      </div>
      <div class="mb-1">
        <label class="lbl">Color</label>
        ${swatches(col,'color')}
      </div>
      ${mfoot(t?'Guardar':'Crear Etiqueta', false)}
    </form>`);
}

async function saveTag(e, id) {
  e.preventDefault();
  const f = e.target;
  const b = { name: f.name.value, color: f.color.value };
  try {
    id
      ? await PATCH(`/projects/${S.pid}/tags/${id}`, b)
      : await POST(`/projects/${S.pid}/tags/`, b);
    closeM(); await loadAll(); render(); toast(id?'Etiqueta actualizada':'Etiqueta creada');
  } catch(err) { toast(err.message,'err'); }
}
