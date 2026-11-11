# 由 index.v2.4.bak.html + p6/* 生成 index.html（可重复执行）
import os
d=os.path.dirname(os.path.abspath(__file__))
src=open(os.path.join(d,'index.v2.4.bak.html'),encoding='utf-8').read()
P=lambda n: open(os.path.join(d,'p6',n),encoding='utf-8').read()
def rep(s,a,b,count=1):
    assert s.count(a)>=1, a
    return s.replace(a,b,count)
s=src
s=rep(s,'  </style>\n</head>', P('p6.css')+'  </style>\n</head>')
s=rep(s,'      </nav>\n', P('nav.html')+'      </nav>\n')
s=rep(s,'调查与仿真工作流 (8 SCREENS)','调查与仿真工作流 (8 + 9 SCREENS)')
s=rep(s,'    </main>', P('s09_11.html')+P('s12_14.html')+P('s15_17.html')+'    </main>')
s=rep(s,'var VALID_ROUTES = ["lobby", "case", "ships", "env", "track", "sim", "ecfc", "analysis"];',
 'var VALID_ROUTES = ["lobby", "case", "ships", "env", "track", "sim", "ecfc", "analysis", "evidence", "interview", "colreg", "whatif", "hf", "systemic", "recs", "knowledge", "access"];')
s=rep(s,'        if (item.getAttribute("data-route") === route) {\n          item.classList.add("active");',
 '        if (item.getAttribute("data-route") === route) {\n          item.classList.add("active");\n          var navEl = document.getElementById("sidebar-nav"), subLbl = navEl && navEl.querySelector(".nav-sub-label");\n          if (navEl && subLbl) { navEl.scrollTop = j >= 8 ? (subLbl.getBoundingClientRect().top - navEl.getBoundingClientRect().top + navEl.scrollTop - 4) : 0; }')
s=rep(s,'        } else if (idx < activeIdx) {','        } else if (idx < activeIdx && activeIdx < 8) {')
s=rep(s,'</body>', P('p6.js')+'</body>')
open(os.path.join(d,'index.html'),'w',encoding='utf-8').write(s)
print('built', len(s))
