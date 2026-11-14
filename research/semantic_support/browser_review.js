/* Offline worksheet download only. No identity, storage, fetch, or fact transition. */
(() => {
  'use strict';
  const template = JSON.parse(document.getElementById('worksheet-template').textContent);
  const fields = [...document.querySelectorAll('fieldset')];
  const flags = ['timeAssociationNeedsCheck', 'sourceAssociationNeedsCheck', 'otherNeedsCheck'];
  const button = document.getElementById('download-notes');
  const status = document.getElementById('download-status');
  let revision = 0;
  document.addEventListener('input', () => {
    revision += 1;
    status.textContent = '当前修改尚未导出。刷新或关闭可能丢失。';
  });
  button.addEventListener('click', () => {
    let url;
    let link;
    try {
      if (fields.length !== template.items.length) throw new Error('coverage');
      const worksheet = JSON.parse(JSON.stringify(template));
      fields.forEach((field, index) => {
        const boxes = [...field.querySelectorAll('input[type="checkbox"]')];
        const area = field.querySelector('textarea');
        if (boxes.length !== flags.length || !area) throw new Error('controls');
        const note = area.value;
        // Python counts Unicode code points; reject lone UTF-16 surrogates as its UTF-8 encoder does.
        if ([...note].length > 4000 || /[\uD800-\uDFFF]/u.test(note)) {
          area.focus();
          status.textContent = `第 ${index + 1} 项备注须为有效 Unicode，最多 4000 个字符。未发起下载。`;
          throw new RangeError('note');
        }
        // Match Python str.strip(), including its four additional control separators.
        if (boxes.some(box => box.checked) && !note.replace(/^[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+|[\u0009-\u000d\u001c-\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000]+$/gu, '')) {
          area.focus();
          status.textContent = `第 ${index + 1} 项已标记待核实，请填写原因。未发起下载。`;
          throw new RangeError('reason');
        }
        flags.forEach((flag, i) => { worksheet.items[index][flag] = boxes[i].checked; });
        worksheet.items[index].note = note;
      });
      const blob = new Blob([JSON.stringify(worksheet, null, 2)], {type: 'application/json;charset=utf-8'});
      url = URL.createObjectURL(blob);
      link = document.createElement('a');
      link.href = url;
      link.download = `research-notes-${template.corpusSha256.slice(0, 12)}-${template.predictionsSha256.slice(0, 12)}.json`;
      document.body.appendChild(link);
      link.click();
      status.textContent = `已请求下载当前备注（编辑版本 ${revision}）；请在浏览器下载列表确认文件已保存。取消或阻止下载不会保存；可再次点击导出。`;
    } catch (error) {
      if (!(error instanceof RangeError)) status.textContent = '无法发起下载；备注仍在本页，请重试或手动保留文本。未确认保存。';
    } finally {
      if (link) link.remove();
      // Keep the URL alive long enough for browsers to consume the download.
      if (url) setTimeout(() => URL.revokeObjectURL(url), 60000);
    }
  });
})();
