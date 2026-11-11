using System;
using System.Collections.Generic;

namespace Mcis.Domain.Colreg
{
    /// <summary>规则目录的技术核查要点，供清单展示和条目关联。</summary>
    public sealed class ColregRuleDefinition
    {
        /// <summary>规则标识。</summary>
        public ColregRuleId Id { get; }
        /// <summary>显示标题。</summary>
        public string Title { get; }
        /// <summary>核查要点摘要。</summary>
        public string Summary { get; }

        /// <summary>构造规则目录条目。</summary>
        public ColregRuleDefinition(ColregRuleId id, string title, string summary)
        {
            Id = id;
            Title = title;
            Summary = summary;
        }
    }

    /// <summary>确定性规则引擎使用的规则目录；摘要用于技术分析，不替代完整条文。</summary>
    public static class ColregRules
    {
        /// <summary>本阶段逐条核查的规则目录。</summary>
        public static IReadOnlyList<ColregRuleDefinition> Catalog { get; } = Array.AsReadOnly(new[]
        {
            new ColregRuleDefinition(ColregRuleId.R5, "瞭望", "须结合 VDR 音频、驾驶台值班和雷达/ARPA 记录核查持续正规瞭望；仅凭航迹不能评估。"),
            new ColregRuleDefinition(ColregRuleId.R6, "安全航速", "结合观测航速、能见度、水域与操纵性能人工研判；配置航速仅作提示。"),
            new ColregRuleDefinition(ColregRuleId.R7, "碰撞危险判断", "依据航迹 CPA 序列识别首次碰撞危险及 DCPA/TCPA 演变；实际雷达标绘使用情况须另有记录。"),
            new ColregRuleDefinition(ColregRuleId.R8, "避免碰撞的行动", "行动应及早、明显，并使船舶在安全距离驶过；须核查行动效果。"),
            new ColregRuleDefinition(ColregRuleId.R9, "狭水道", "尽量靠近本船右舷的航道外缘行驶；缺少航道几何时保留核查项并说明限制。"),
            new ColregRuleDefinition(ColregRuleId.R13, "追越", "追越船应让清被追越船；存疑按追越处理，并保持至驶过让清。"),
            new ColregRuleDefinition(ColregRuleId.R14, "对遇", "有碰撞危险的互见机动船对遇时，双方均应向右转向。"),
            new ColregRuleDefinition(ColregRuleId.R15, "交叉相遇", "他船在本船右舷时本船应让路，并避免横越他船前方。"),
            new ColregRuleDefinition(ColregRuleId.R16, "让路船的行动", "让路船应及早采取大幅度行动，宽裕地让清他船。"),
            new ColregRuleDefinition(ColregRuleId.R17, "直航船的行动", "直航船应保向保速；让路船明显未适当行动时可行动，紧迫时应采取最有助于避碰的行动；交叉时应核查向左转向限制，让路船义务继续。"),
            new ColregRuleDefinition(ColregRuleId.R18, "船舶之间的责任", "在R13追越义务优先的前提下，机动船应让清失控船和操限船；船舶状态须结合号灯号型、VHF通报、VDR音频和轮机日志确认，其余状态组合需人工研判。"),
            new ColregRuleDefinition(ColregRuleId.R19, "能见度不良时的行动", "未互见时双方均有行动义务；核查安全航速、正横以前避免向左转向（正在被本船追越的目标除外）及正横或以后避免朝来船转向。"),
            new ColregRuleDefinition(ColregRuleId.R34_35, "操纵、警告及能见度不良声号", "须结合 VDR 音频、声号设备记录及驾驶台记录核查操纵、警告和能见度不良声号；仅凭航迹不能评估。")
        });

        /// <summary>查找规则定义；未知标识返回空值。</summary>
        public static ColregRuleDefinition Get(ColregRuleId id)
        {
            for (int i = 0; i < Catalog.Count; i++)
            {
                if (Catalog[i].Id == id) return Catalog[i];
            }
            return null;
        }
    }
}
