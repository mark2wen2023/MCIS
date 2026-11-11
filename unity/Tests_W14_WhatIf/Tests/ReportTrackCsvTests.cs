using System;
using System.Collections.Generic;
using System.Linq;
using Xunit;
using Mcis.Simulation.WhatIf.Cases;

namespace Mcis.Tests.W14
{
    public class ReportTrackCsvTests
    {
        [Fact]
        public void RealCsvHas54DataRowsAndPreservesProvenanceColumns()
        {
            IReadOnlyList<ReportTrackRow> rows = ReportTrackCsv.Parse(Yangze22TestData.ReadTrackLines());

            Assert.Equal(54, rows.Count);
            Assert.Equal(21, rows.Count(r => r.HasPosition));
            Assert.All(rows, row =>
            {
                Assert.False(string.IsNullOrWhiteSpace(row.VesselId));
                Assert.False(string.IsNullOrWhiteSpace(row.Provenance));
            });
            Assert.Contains(rows, r => r.Provenance == "ReportFigure-VDR");
            Assert.Contains(rows, r => r.Provenance == "ReportFigure-AIS");
            Assert.Contains(rows, r => r.Provenance == "ReportNarrative");

            ReportTrackRow firstYangze = rows.First(r => r.VesselId == "yangze22" && r.Provenance == "ReportFigure-VDR" &&
                r.TimeBeijing.ToString("HH:mm:ss") == "21:58:30");
            Assert.Equal(2024, firstYangze.TimeBeijing.Year);
            Assert.Equal("ReportFigure-VDR", firstYangze.Provenance);
            Assert.Equal(31, firstYangze.Page);
            Assert.Equal(33, firstYangze.PdfPage);
            Assert.Equal("746", firstYangze.Line);
            Assert.Equal("图19", firstYangze.Figure);
            Assert.Contains("Heading 114.4", firstYangze.FigureReading);

            ReportTrackRow collisionRow = rows.First(r =>
                r.VesselId == "yangze22" && r.TimeBeijing.ToString("HH:mm:ss") == "22:01:54" &&
                r.Provenance == "ReportFigure-VDR");
            Assert.Equal(48.0, collisionRow.HdgDeg);
            Assert.Equal(9.3, collisionRow.StwKn);
            Assert.NotNull(collisionRow.LatDeg);
            Assert.NotNull(collisionRow.LonDeg);
        }

        [Fact]
        public void QuotedFieldsWithCommasAndEscapedQuotesAreParsed()
        {
            string[] lines =
            {
                "# comment line",
                "vesselId,timeBeijing,positionText,quote,note,page,pdfPage,line,provenance",
                "yangze22,2024-12-30T22:01:54+08:00,\"39号灯浮,下游\",\"他说\"\"右满舵\"\"\",,15,17,404,ReportFigure-VDR"
            };

            IReadOnlyList<ReportTrackRow> rows = ReportTrackCsv.Parse(lines);

            Assert.Single(rows);
            Assert.Equal("39号灯浮,下游", rows[0].PositionText);
            Assert.Equal("他说\"右满舵\"", rows[0].Quote);
            Assert.Equal(15, rows[0].Page);
            Assert.Equal(17, rows[0].PdfPage);
            Assert.Equal("404", rows[0].Line);
            Assert.False(rows[0].HasPosition);
        }

        [Fact]
        public void EmptyValuesBecomeNullAndDefaults()
        {
            string[] lines =
            {
                "vesselId,timeBeijing,approximate,latDeg,lonDeg,sogKn,provenance",
                "vega_dream,2024-12-30T21:58:30+08:00,True,,,10.5,ReportNarrative"
            };

            ReportTrackRow row = ReportTrackCsv.Parse(lines)[0];

            Assert.True(row.Approximate);
            Assert.Null(row.LatDeg);
            Assert.Null(row.LonDeg);
            Assert.Null(row.HdgDeg);
            Assert.Equal(10.5, row.SogKn);
            Assert.Null(row.Page);
            Assert.Equal(string.Empty, row.Note);
        }

        [Fact]
        public void ColumnCountMismatchThrowsFormatException()
        {
            string[] lines =
            {
                "vesselId,timeBeijing,positionText",
                "yangze22,2024-12-30T22:01:54+08:00,a,b"
            };

            Assert.Throws<FormatException>(() => ReportTrackCsv.Parse(lines));
        }

        [Fact]
        public void MissingRequiredColumnThrowsFormatException()
        {
            string[] lines = { "vesselId,positionText", "yangze22,a" };
            Assert.Throws<FormatException>(() => ReportTrackCsv.Parse(lines));
        }

        [Fact]
        public void SplitLineHandlesQuotedComma()
        {
            string[] fields = ReportTrackCsv.SplitLine("a,\"b,c\",\"d\"\"e\",");
            Assert.Equal(new[] { "a", "b,c", "d\"e", "" }, fields);
        }
    }
}
