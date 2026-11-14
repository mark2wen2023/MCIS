"""Deterministic human review questions, not factual findings or approval."""
from copy import deepcopy
from research.expert_group.packet import _packet, load_packet, ROLES
from research.expert_meeting.citations import citation_view

QUESTIONS = {
    'no_current_opinion': '当前轮次尚无意见；是否需要补充两席审读？未回答前不得假定已有结论。',
    'missing_role': '当前轮次缺少一席意见；是否补充审读或记录不能完成的原因？',
    'different_labels': '两席声明标签不同；各自引用是否支持其理由？请记录分歧，不强制归并。',
    'declared_insufficient': '有意见声明资料不足；还需要哪些可核查材料？不得从缺失推定事实。',
    'human_review_required': '请核对原报告、人工测试主张及每席不确定性；相同标签也不构成共识或事实确认。',
}


def review_plan(snapshot):
    view = citation_view(snapshot)
    packet = _packet(load_packet())
    current_round = len(view['comparison'])
    tasks = []
    for item in packet['items']:
        opinions = [row for row in view['rows'] if row['itemId']==item['itemId'] and row['round']==current_round]
        missing = [role for role in ROLES if role not in {row['roleId'] for row in opinions}]
        reasons = []
        if not opinions: reasons.append('no_current_opinion')
        elif missing: reasons.append('missing_role')
        labels = {row['declaredLabel'] for row in opinions}
        if len(labels)>1: reasons.append('different_labels')
        if 'insufficient' in labels: reasons.append('declared_insufficient')
        reasons.append('human_review_required')
        tasks.append({'taskId':view['snapshotSha256']+':'+item['itemId'],
                      'itemId':item['itemId'], 'round':current_round,
                      'status':'pending_human_review', 'claimKind':'human_authored_test_claim_including_counterexamples',
                      'claim':item['claim'], 'sourceSha256':item['sourceSha256'],
                      'sourceLocator':deepcopy(item['sourceLocator']),
                      'fixedReportCitation':deepcopy(item['citation']),
                      'missingRoles':missing, 'reasonCodes':reasons,
                      'questions':[QUESTIONS[reason] for reason in reasons],
                      'opinions':[{'roleId':row['roleId'], 'ticketId':row['ticketId'],
                                   'declaredLabel':row['declaredLabel'], 'uncertainty':row['uncertainty'],
                                   'rationale':row['rationale'], 'quote':row['reviewerSelectedCitation']['quote']}
                                  for row in opinions],
                      'semanticSupportVerified':False, 'factActivated':False})
    return {'schemaVersion':1,'kind':'offline_human_review_questions',
            'snapshotSha256':view['snapshotSha256'],'packetSha256':view['packetSha256'],
            'meetingId':view['meetingId'],'phase':view['phase'],'currentRound':current_round,
            'tasks':tasks,'status':'pending_human_review', 'identityAuthenticated':False,
            'modelExecutionVerified':False,'consensusComputed':False,'factActivated':False}
