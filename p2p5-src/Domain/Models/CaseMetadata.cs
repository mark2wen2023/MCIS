using System;
using Mcis.Domain.Common;

namespace Mcis.Domain.Models
{
    /// <summary>案件基本信息与元数据（对应 ARCHITECTURE 5.2 节）。</summary>
    public sealed class CaseMetadata
    {
        public const string CurrentSchemaVersion = "1.0.0";

        public string CaseId { get; }
        public string SchemaVersion { get; }
        public string Title { get; }
        public string AccidentCode { get; }
        public string AccidentType { get; }
        public string AccidentGrade { get; }
        public DateTimeOffset IncidentTimeUtc { get; }
        public DateTimeOffset CaseEpochUtc { get; }
        public int DisplayTimeZoneOffsetMinutes { get; }
        public GeoCoord IncidentLocation { get; }
        public double SeaLevelOffsetM { get; }
        public string LeadInvestigator { get; }
        public string AgencyName { get; }

        /// <summary>是否为虚构演示数据（如 Lily/Mary 案例，UI 与报告强制显示水印）。</summary>
        public bool IsFictionalDemo { get; }

        public string SummaryNotes { get; }

        public CaseMetadata(
            string caseId,
            string schemaVersion,
            string title,
            string accidentCode,
            string accidentType,
            string accidentGrade,
            DateTimeOffset incidentTimeUtc,
            DateTimeOffset caseEpochUtc,
            int displayTimeZoneOffsetMinutes,
            GeoCoord incidentLocation,
            double seaLevelOffsetM,
            string leadInvestigator,
            string agencyName,
            bool isFictionalDemo,
            string summaryNotes)
        {
            CaseId = caseId ?? string.Empty;
            SchemaVersion = string.IsNullOrWhiteSpace(schemaVersion) ? CurrentSchemaVersion : schemaVersion;
            Title = title ?? string.Empty;
            AccidentCode = accidentCode ?? string.Empty;
            AccidentType = accidentType ?? string.Empty;
            AccidentGrade = accidentGrade ?? string.Empty;
            IncidentTimeUtc = incidentTimeUtc;
            CaseEpochUtc = caseEpochUtc;
            DisplayTimeZoneOffsetMinutes = displayTimeZoneOffsetMinutes;
            IncidentLocation = incidentLocation;
            SeaLevelOffsetM = seaLevelOffsetM;
            LeadInvestigator = leadInvestigator ?? string.Empty;
            AgencyName = agencyName ?? string.Empty;
            IsFictionalDemo = isFictionalDemo;
            SummaryNotes = summaryNotes ?? string.Empty;
        }

        public CaseMetadata WithFictionalFlag(bool isFictionalDemo)
        {
            return new CaseMetadata(
                CaseId, SchemaVersion, Title, AccidentCode, AccidentType, AccidentGrade,
                IncidentTimeUtc, CaseEpochUtc, DisplayTimeZoneOffsetMinutes, IncidentLocation,
                SeaLevelOffsetM, LeadInvestigator, AgencyName, isFictionalDemo, SummaryNotes);
        }
    }
}
