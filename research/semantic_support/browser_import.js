/* Explicit local file restore; no upload, storage, identity or fact approval. */
(() => {
  'use strict';
  const expected = JSON.parse(document.getElementById('worksheet-template').textContent);
  const fields = [...document.querySelectorAll('fieldset')];
  const flags = ['timeAssociationNeedsCheck', 'sourceAssociationNeedsCheck', 'otherNeedsCheck'];
  const picker = document.getElementById('import-file');
  const apply = document.getElementById('apply-import');
  const cancel = document.getElementById('cancel-import');
  const clear = document.getElementById('clear-notes');
  const confirmClear = document.getElementById('confirm-clear');
  const status = document.getElementById('import-status');
  let generation = 0;
  let pending = null;
  const whitespace = /^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu;
  const exact = (value, keys) => {
    if (!value || Array.isArray(value) || typeof value !== 'object' || Object.keys(value).sort().join('|') !== keys.slice().sort().join('|')) throw Error('keys');
  };
  // A bounded parser rejects duplicate keys before they can be collapsed by JSON.parse.
  // The worksheet's only number is integer schemaVersion: reject floating/exponent spelling too.
  function parse(text) {
    let pos = 0;
    const ws = () => { while (/[\x20\t\r\n]/.test(text[pos] || '\0')) pos++; };
    function value(depth) {
      if (depth > 16) throw Error('depth');
      ws();
      if (text[pos] === '"') {
        const match = /^"(?:[^"\\\x00-\x1f]|\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))*"/.exec(text.slice(pos));
        if (!match) throw Error('string');
        pos += match[0].length; return JSON.parse(match[0]);
      }
      if (text[pos] === '{' || text[pos] === '[') {
        const object = text[pos++] === '{'; const end = object ? '}' : ']';
        const result = object ? Object.create(null) : [];
        ws(); if (text[pos] === end) { pos++; return result; }
        while (true) {
          if (object) {
            ws(); if (text[pos] !== '"') throw Error('key');
            const key = value(depth + 1); ws();
            if (Object.hasOwn(result, key) || text[pos++] !== ':') throw Error('duplicate');
            result[key] = value(depth + 1);
          } else result.push(value(depth + 1));
          ws(); if (text[pos] === end) { pos++; return result; }
          if (text[pos++] !== ',') throw Error('separator');
        }
      }
      const token = /^(?:true|false|null|-?(?:0|[1-9][0-9]*))/.exec(text.slice(pos));
      if (!token) throw Error('token');
      pos += token[0].length; return JSON.parse(token[0]);
    }
    const result = value(0); ws(); if (pos !== text.length) throw Error('trailing'); return result;
  }
  function validate(value) {
    exact(value, ['schemaVersion', 'status', 'corpusSha256', 'predictionsSha256', 'items']);
    for (const key of ['schemaVersion', 'status', 'corpusSha256', 'predictionsSha256']) if (value[key] !== expected[key]) throw Error('binding');
    if (!Array.isArray(value.items) || value.items.length !== expected.items.length) throw Error('coverage');
    const rows = new Map();
    for (const row of value.items) {
      exact(row, ['itemId', ...flags, 'note']);
      if (typeof row.itemId !== 'string' || rows.has(row.itemId)) throw Error('item');
      if (flags.some(flag => typeof row[flag] !== 'boolean')) throw Error('flag');
      if (typeof row.note !== 'string' || [...row.note].length > 4000 || /[\uD800-\uDFFF]/u.test(row.note)) throw Error('note');
      if (flags.some(flag => row[flag]) && !row.note.replace(whitespace, '')) throw Error('reason');
      rows.set(row.itemId, row);
    }
    return expected.items.map(row => { if (!rows.has(row.itemId)) throw Error('item'); return rows.get(row.itemId); });
  }
  function reset() {
    generation++; pending = null; picker.value = ''; apply.disabled = true; confirmClear.hidden = true;
  }
  function controls() {
    if (fields.length !== expected.items.length) throw Error('coverage');
    return fields.map(field => {
      const boxes = [...field.querySelectorAll('input[type="checkbox"]')];
      const area = field.querySelector('textarea');
      if (boxes.length !== 3 || !area) throw Error('controls');
      return {boxes, area};
    });
  }
  function replace(rows) {
    const targets = controls(); // Preflight all targets before changing any editor.
    targets.forEach(({boxes, area}, i) => {
      flags.forEach((flag, j) => { boxes[j].checked = rows[i][flag]; }); area.value = rows[i].note;
    });
    document.dispatchEvent(new Event('input'));
  }
  document.addEventListener('input', event => {
    if (event.target === picker) return;
    reset(); status.textContent = '当前编辑已变化；未应用的导入或清空已取消。';
  });
  picker.addEventListener('change', async () => {
    const file = picker.files && picker.files[0]; reset(); const token = generation;
    if (!file) { status.textContent = '已取消选择，当前备注未变。'; return; }
    status.textContent = '正在本地读取并校验；当前备注未变。';
    try {
      if (file.size > 4 * 1024 * 1024) throw Error('size');
      const bytes = await file.arrayBuffer();
      if (token !== generation) return;
      if (bytes.byteLength > 4 * 1024 * 1024) throw Error('size');
      const rows = validate(parse(new TextDecoder('utf-8', {fatal: true, ignoreBOM: true}).decode(bytes)));
      controls(); pending = rows; apply.disabled = false;
      status.textContent = `已校验 ${rows.length} 项，语料与模型输出双摘要一致。确认替换将覆盖当前全部备注；仍属未认证研究记录。可取消并先导出当前编辑。`;
    } catch (_) {
      if (token !== generation) return;
      pending = null; apply.disabled = true;
      status.textContent = '导入拒绝：文件格式、绑定、内容或读取失败。当前备注未变，请选择匹配的备注 JSON。';
    }
  });
  apply.addEventListener('click', () => {
    if (!pending) return;
    try { const rows = pending; replace(rows); reset(); status.textContent = '已恢复到本页，仍未核实；未上传或写入案件。请显式下载以保存后续修改。'; }
    catch (_) { reset(); status.textContent = '页面控件不完整，未应用导入。'; }
  });
  cancel.addEventListener('click', () => { reset(); status.textContent = '已取消待处理操作，当前备注未变。'; });
  clear.addEventListener('click', () => { reset(); confirmClear.hidden = false; status.textContent = '清空会移除本页所有备注和标记；可取消并先导出。'; });
  confirmClear.addEventListener('click', () => {
    if (confirmClear.hidden) return;
    try { replace(expected.items); reset(); status.textContent = '已清空本页备注与标记；未标记不表示已核实，不删除已下载文件。'; }
    catch (_) { reset(); status.textContent = '页面控件不完整，未清空。'; }
  });
  reset();
})();
