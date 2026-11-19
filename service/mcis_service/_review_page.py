"""Pure page shaping from the registration path, not a request capability flag."""


def _review_page(html, *, task_routes):
    if type(task_routes) is not bool:
        raise ValueError('explicit registration capability required')
    if task_routes:
        return html
    markers = {
        '<details data-task-controls>': '<details data-task-controls hidden inert>',
        'const taskRoutesAvailable=true;': 'const taskRoutesAvailable=false;',
        '<!-- review-capability-notice -->': '<p role="status">限定核对模式：不提供模型任务创建、查询、打开或任务产物下载；可导入已有结果并核对。任务来源记录仍须通过服务端原有绑定核验。</p>',
    }
    for marker, replacement in markers.items():
        if html.count(marker) != 1:
            raise ValueError('review page capability marker mismatch')
        html = html.replace(marker, replacement)
    return html
