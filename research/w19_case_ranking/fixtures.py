"""Hand-labeled BEFORE ranking; synthetic research vocabulary, not case facts.
Relevance rubric: reduced-visibility watchkeeping difficulty. One relevant case
uses a different human label intentionally to expose exact-tag recall limits.
"""
def identity(n): return 'KC-'+format(n,'032x')
VOCABULARY=['能见度受限','瞭望不足','交接遗漏','舵机故障','港内靠泊']
QUERY=['能见度受限','瞭望不足']
# Independent expected labels are not derived from rank output.
RELEVANT={identity(1),identity(2),identity(3)}

def card(n,tags,description,status='Published',kind='Case'):
    return {'cardId':identity(n),'status':status,'content':{
        'kind':kind,'title':'合成研究卡'+str(n),'summary':description,'body':description,
        'tags':tags,'applicability':'仅研究测试，不是真实事故机制认定。',
        'source':{'type':'Synthetic','title':'手造研究样本','locator':'fixture '+str(n),
                  'excerpt':description,'rightsNote':'完全手造，仅测试。'}}}

CARDS=[
 card(1,['能见度受限','瞭望不足'],'合成近案：雾中瞭望不足。'),
 card(2,['能见度受限','瞭望不足','交接遗漏'],'合成相关案：雾中交接遗漏造成观察空档。'),
 card(3,['交接遗漏'],'合成漏项：雾中未持续观察，但标注者仅填写交接遗漏。'),
 card(4,['舵机故障'],'雾、瞭望、碰撞：关键词相同，设定机制为舵机故障干扰项。'),
 card(5,['能见度受限','瞭望不足'],'待审近案，不纳入。',status='Candidate'),
 card(6,['能见度受限','瞭望不足'],'撤回近案，不纳入。',status='Withdrawn'),
 card(7,['能见度受限','瞭望不足'],'方法卡，不是案例。',kind='Method'),
 card(8,['未知'],'没有已校核特征。'),
 card(9,['能见度受限'],'合成非相关干扰：低能见度港内靠泊，未设瞭望问题。'),
]
