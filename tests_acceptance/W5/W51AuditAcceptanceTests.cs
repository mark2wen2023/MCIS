using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using Mcis.Domain.Evidence;
using Mcis.Domain.Interview;
using Xunit;

namespace Mcis.Acceptance.W5
{
    // Independent W5.1 follow-up for W3's 21:32 rulings. Fictional data only.
    public class W51AuditAcceptanceTests
    {
        private sealed class FailingSink : IInvestigationAuditSink
        {
            public bool Fail = true;
            public readonly List<InvestigationAuditEntry> Entries = new List<InvestigationAuditEntry>();
            public void Append(InvestigationAuditEntry entry)
            {
                if (Fail) throw new IOException("simulated audit failure");
                Entries.Add(entry);
            }
        }

        private static CrossCheckResult Result(string id) => new CrossCheckResult(
            id, "IR-03", CrossCheckOutcome.Consistent, 0, "deg", "fictional claim", "fictional observation", "fictional VDR", "rule");

        [Fact]
        public void SubmitAuditFailureReturnsCodeAndPreservesRegisterThenRetrySucceeds()
        {
            var sink = new FailingSink();
            var register = new CrossCheckRegister(sink);
            var utc = new DateTimeOffset(2026, 5, 19, 10, 0, 0, TimeSpan.Zero);
            var result = register.Submit(Result("S-1"), "fictional investigator", utc);
            Assert.False(result.IsSuccess);
            Assert.Equal("crosscheck_audit_failed", result.ErrorCode);
            Assert.Empty(register.Entries);
            Assert.Null(register.Get("S-1"));
            Assert.Empty(sink.Entries);
            sink.Fail = false;
            Assert.True(register.Submit(Result("S-1"), "fictional investigator", utc).IsSuccess);
            Assert.Single(register.Entries);
            Assert.Single(sink.Entries);
        }

        [Fact]
        public void OptionalBatchIdExtensionPreservesLegacyAuditFields()
        {
            var utc = new DateTimeOffset(2026, 5, 19, 10, 0, 0, TimeSpan.Zero);
            var old = new InvestigationAuditEntry(utc, "fictional investigator", "action", "Interview", "command", "before", "after");
            var extended = new InvestigationAuditEntry(utc, "fictional investigator", "action", "Interview", "command", "before", "after", "batch-01");
            using var a = JsonDocument.Parse(old.ToJsonLine());
            using var b = JsonDocument.Parse(extended.ToJsonLine());
            Assert.False(a.RootElement.TryGetProperty("x-batchId", out _));
            Assert.Equal("batch-01", b.RootElement.GetProperty("x-batchId").GetString());
            Assert.Equal(a.RootElement.EnumerateObject().Count() + 1, b.RootElement.EnumerateObject().Count());
            foreach (var p in a.RootElement.EnumerateObject())
                Assert.Equal(p.Value.GetRawText(), b.RootElement.GetProperty(p.Name).GetRawText());
        }
    }
}
