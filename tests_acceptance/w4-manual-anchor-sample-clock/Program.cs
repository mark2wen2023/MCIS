using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;
using Mcis.Core;
using Mcis.Data.Vdr;
using Mcis.Domain.Timeline;

namespace Mcis.Acceptance.W4.SampleClock
{
    /// <summary>
    /// Direct core sample-clock check: import, manual anchors, estimate, calibrate,
    /// then read the calibrated timeline point by point. Does not call the CLI.
    /// </summary>
    public static class Program
    {
        public const string ProductPin = "94d5e38c926fda232bb987b60fa9145e4bcf01a7";
        public const string FixtureSourceSha = "3c408593143ae1dddc5f065ea8549566fcd40be8";
        public const string CaseEpochText = "2026-03-01T08:00:00Z";
        public const string ReferenceSourceId = "SYN-GNSS";
        public const string FastSourceId = "SYN-VDR";
        public const double ExpectedOffsetSeconds = 12.0;
        public const double TimeTol = 1e-9;
        public const double ValueTol = 1e-9;

        public static int Main(string[] args)
        {
            Console.OutputEncoding = new UTF8Encoding(false);
            string fixturesDir = null;
            string outDir = null;
            for (int i = 0; i < args.Length; i++)
            {
                if (args[i] == "--fixtures" && i + 1 < args.Length)
                {
                    fixturesDir = args[++i];
                }
                else if (args[i] == "--out" && i + 1 < args.Length)
                {
                    outDir = args[++i];
                }
            }

            if (string.IsNullOrWhiteSpace(fixturesDir) || string.IsNullOrWhiteSpace(outDir))
            {
                Console.Error.WriteLine("usage: W4SampleClock --fixtures <dir> --out <empty-dir>");
                return 2;
            }

            Directory.CreateDirectory(outDir);
            var errors = new List<string>();
            DateTimeOffset epoch = DateTimeOffset.Parse(CaseEpochText, CultureInfo.InvariantCulture, DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal);

            try
            {
                List<Track> imported = ImportBoth(fixturesDir, epoch, errors);
                if (errors.Count > 0 || imported == null)
                {
                    return Fail(outDir, errors, null);
                }

                IReadOnlyList<ManualAnchor> manuals = LoadManuals(fixturesDir, epoch, errors);
                if (errors.Count > 0)
                {
                    return Fail(outDir, errors, null);
                }

                JsonObject withAnchors = RunScenario(
                    "with-manual-anchors",
                    imported,
                    manuals,
                    epoch,
                    expectCalibrated: true,
                    errors);

                JsonObject withoutAnchors = RunScenario(
                    "without-manual-anchors",
                    imported,
                    Array.Empty<ManualAnchor>(),
                    epoch,
                    expectCalibrated: false,
                    errors);

                var receipt = new JsonObject
                {
                    ["passed"] = errors.Count == 0,
                    ["productPin"] = ProductPin,
                    ["fixtureSourceSha"] = FixtureSourceSha,
                    ["offsetDefinition"] = "offsetSeconds = source time − reference time; calibrated = source − offset",
                    ["expectedOffsetSeconds"] = ExpectedOffsetSeconds,
                    ["referenceSourceId"] = ReferenceSourceId,
                    ["fastSourceId"] = FastSourceId,
                    ["cliUsed"] = false,
                    ["scope"] = "synthetic sample-clock core path only; not W4 whole package",
                    ["errors"] = StringArray(errors),
                    ["withManualAnchors"] = withAnchors,
                    ["withoutManualAnchors"] = withoutAnchors
                };
                WriteJson(Path.Combine(outDir, "receipt.json"), receipt);
                if (withAnchors != null)
                {
                    WriteJson(Path.Combine(outDir, "points-with-manual-anchors.json"), withAnchors);
                }
                if (withoutAnchors != null)
                {
                    WriteJson(Path.Combine(outDir, "points-without-manual-anchors.json"), withoutAnchors);
                }

                if (errors.Count > 0)
                {
                    Console.Error.WriteLine("W4 sample-clock stopped: " + errors[0]);
                    return 1;
                }

                Console.Out.Write(receipt.ToJsonString(JsonOptions()) + "\n");
                return 0;
            }
            catch (Exception ex)
            {
                errors.Add(ex.GetType().Name + ": " + ex.Message);
                Console.Error.WriteLine(ex.ToString());
                return Fail(outDir, errors, null);
            }
        }

        private static int Fail(string outDir, List<string> errors, JsonObject extra)
        {
            var receipt = new JsonObject
            {
                ["passed"] = false,
                ["productPin"] = ProductPin,
                ["fixtureSourceSha"] = FixtureSourceSha,
                ["cliUsed"] = false,
                ["scope"] = "synthetic sample-clock core path only; not W4 whole package",
                ["errors"] = StringArray(errors),
                ["firstFailure"] = errors.Count > 0 ? errors[0] : "unknown"
            };
            if (extra != null)
            {
                receipt["detail"] = extra;
            }
            WriteJson(Path.Combine(outDir, "receipt.json"), receipt);
            if (errors.Count > 0)
            {
                Console.Error.WriteLine("W4 sample-clock stopped: " + errors[0]);
            }
            return 1;
        }

        private static List<Track> ImportBoth(string fixturesDir, DateTimeOffset epoch, List<string> errors)
        {
            var tracks = new List<Track>();
            foreach (var pair in new[] { (ReferenceSourceId, "syn-gnss.csv"), (FastSourceId, "syn-vdr.csv") })
            {
                Result<VdrImportResult> imported = VdrCsvImporter.Import(
                    File.ReadAllLines(Path.Combine(fixturesDir, pair.Item2), Encoding.UTF8),
                    Mapping(),
                    new VdrImportOptions
                    {
                        SourceId = pair.Item1,
                        CaseEpochUtc = epoch,
                        EmitGnssAnchors = false
                    });
                if (!imported.IsSuccess)
                {
                    errors.Add("import " + pair.Item1 + " failed: " + imported.ErrorCode + " " + imported.ErrorMessage);
                    return null;
                }
                if (imported.Value.Anchors != null && imported.Value.Anchors.Count > 0)
                {
                    errors.Add("import " + pair.Item1 + " emitted automatic anchors; EmitGnssAnchors was false");
                    return null;
                }
                tracks.AddRange(imported.Value.Tracks);
            }
            return tracks;
        }

        private static IReadOnlyList<ManualAnchor> LoadManuals(string fixturesDir, DateTimeOffset epoch, List<string> errors)
        {
            Result<IReadOnlyList<ManualAnchor>> result = ManualAnchorCsvImporter.Import(
                File.ReadAllLines(Path.Combine(fixturesDir, "manual-anchors-valid.csv"), Encoding.UTF8),
                epoch);
            if (!result.IsSuccess)
            {
                errors.Add("manual anchors failed: " + result.ErrorCode + " " + result.ErrorMessage);
                return Array.Empty<ManualAnchor>();
            }
            if (result.Value.Count != 3)
            {
                errors.Add("expected 3 UTC manual anchors, got " + result.Value.Count);
            }
            return result.Value;
        }

        private static JsonObject RunScenario(
            string name,
            IReadOnlyList<Track> imported,
            IReadOnlyList<ManualAnchor> manuals,
            DateTimeOffset epoch,
            bool expectCalibrated,
            List<string> errors)
        {
            IReadOnlyList<AnchorObservation> auto = Array.Empty<AnchorObservation>();
            IReadOnlyList<AnchorObservation> allAnchors = ManualAnchors.Merge(auto, manuals);
            IReadOnlyList<ClockOffsetEstimate> estimates = Array.Empty<ClockOffsetEstimate>();
            string estimateError = null;
            if (expectCalibrated)
            {
                Result<IReadOnlyList<ClockOffsetEstimate>> estimated =
                    ClockOffsetEstimator.Estimate(allAnchors, ReferenceSourceId, OffsetMethod.Median);
                if (!estimated.IsSuccess)
                {
                    errors.Add(name + ": estimate failed: " + estimated.ErrorCode + " " + estimated.ErrorMessage);
                    return null;
                }
                estimates = estimated.Value;
            }
            else
            {
                Result<IReadOnlyList<ClockOffsetEstimate>> estimated =
                    ClockOffsetEstimator.Estimate(allAnchors, ReferenceSourceId, OffsetMethod.Median);
                if (estimated.IsSuccess)
                {
                    errors.Add(name + ": estimate unexpectedly succeeded without anchors");
                    estimates = estimated.Value;
                }
                else
                {
                    estimateError = estimated.ErrorCode + ": " + estimated.ErrorMessage;
                    if (estimated.ErrorCode != "timeline_no_reference")
                    {
                        errors.Add(name + ": expected timeline_no_reference, got " + estimateError);
                    }
                }
            }

            CalibrationResult calibration = TimelineCalibrator.Calibrate(imported, estimates);
            JsonArray points = new JsonArray();
            int importedCount = CountSamples(imported);
            int calibratedCount = CountSamples(calibration.Timeline.Tracks);
            if (importedCount != calibratedCount)
            {
                errors.Add(name + ": sample count changed " + importedCount + " -> " + calibratedCount);
            }

            if (imported.Count != calibration.Timeline.Tracks.Count)
            {
                errors.Add(name + ": track count changed " + imported.Count + " -> " + calibration.Timeline.Tracks.Count);
            }

            int n = Math.Min(imported.Count, calibration.Timeline.Tracks.Count);
            for (int t = 0; t < n; t++)
            {
                Track before = imported[t];
                Track after = calibration.Timeline.Tracks[t];
                if (before.Id != after.Id || before.SourceId != after.SourceId || !before.Kind.Equals(after.Kind))
                {
                    errors.Add(name + ": track identity changed at index " + t + " " + before.Id + " -> " + after.Id);
                }
                int sn = Math.Min(before.Samples.Count, after.Samples.Count);
                if (before.Samples.Count != after.Samples.Count)
                {
                    errors.Add(name + ": sample count on " + before.Id + " changed " + before.Samples.Count + " -> " + after.Samples.Count);
                }
                for (int i = 0; i < sn; i++)
                {
                    TimelineSample input = before.Samples[i];
                    TimelineSample output = after.Samples[i];
                    double expectedShift = 0.0;
                    if (expectCalibrated && string.Equals(before.SourceId, FastSourceId, StringComparison.Ordinal))
                    {
                        expectedShift = -ExpectedOffsetSeconds;
                    }
                    double expectedSeconds = input.Time.Seconds + expectedShift;
                    bool timeOk = Math.Abs(output.Time.Seconds - expectedSeconds) <= TimeTol;
                    bool valueOk = ValuesEqual(input, output);
                    if (!timeOk)
                    {
                        errors.Add(string.Format(
                            CultureInfo.InvariantCulture,
                            "{0}: {1}[{2}] calibrated seconds {3} expected {4} (input {5})",
                            name, before.Id, i, output.Time.Seconds, expectedSeconds, input.Time.Seconds));
                    }
                    if (!valueOk)
                    {
                        errors.Add(name + ": " + before.Id + "[" + i + "] observation value changed");
                    }
                    if (expectCalibrated)
                    {
                        if (string.Equals(before.SourceId, ReferenceSourceId, StringComparison.Ordinal))
                        {
                            if (after.CalibrationStatus != CalibrationStatus.Reference)
                            {
                                errors.Add(name + ": " + before.Id + " status " + after.CalibrationStatus + " expected Reference");
                            }
                        }
                        else if (string.Equals(before.SourceId, FastSourceId, StringComparison.Ordinal))
                        {
                            if (after.CalibrationStatus != CalibrationStatus.Calibrated)
                            {
                                errors.Add(name + ": " + before.Id + " status " + after.CalibrationStatus + " expected Calibrated");
                            }
                        }
                    }
                    else if (after.CalibrationStatus != CalibrationStatus.Uncalibrated)
                    {
                        errors.Add(name + ": " + before.Id + " status " + after.CalibrationStatus + " expected Uncalibrated");
                    }

                    points.Add(new JsonObject
                    {
                        ["scenario"] = name,
                        ["trackId"] = before.Id,
                        ["sourceId"] = before.SourceId,
                        ["kind"] = before.Kind.ToString(),
                        ["index"] = i,
                        ["referenceSourceId"] = ReferenceSourceId,
                        ["inputSeconds"] = input.Time.Seconds,
                        ["inputTimeUtc"] = FormatUtc(input.Time.ToUtc(epoch)),
                        ["calibratedSeconds"] = output.Time.Seconds,
                        ["calibratedTimeUtc"] = FormatUtc(output.Time.ToUtc(epoch)),
                        ["expectedCalibratedSeconds"] = expectedSeconds,
                        ["timeShiftSeconds"] = output.Time.Seconds - input.Time.Seconds,
                        ["value"] = Finite(output.Value),
                        ["inputValue"] = Finite(input.Value),
                        ["text"] = output.Text,
                        ["hasPosition"] = output.HasPosition,
                        ["calibrationStatus"] = after.CalibrationStatus.ToString(),
                        ["timeOk"] = timeOk,
                        ["valueOk"] = valueOk
                    });
                }
            }

            var offsets = new JsonArray();
            foreach (ClockOffsetEstimate e in estimates)
            {
                offsets.Add(new JsonObject
                {
                    ["sourceId"] = e.SourceId,
                    ["referenceSourceId"] = e.ReferenceSourceId,
                    ["offsetSeconds"] = Finite(e.OffsetSeconds),
                    ["isReference"] = e.IsReference,
                    ["status"] = e.Status.ToString(),
                    ["manualAnchorCount"] = e.ManualAnchorCount,
                    ["anchorCount"] = e.AnchorCount
                });
            }

            return new JsonObject
            {
                ["name"] = name,
                ["estimateError"] = estimateError,
                ["allCalibrated"] = calibration.AllCalibrated,
                ["uncalibratedSources"] = StringArray(calibration.UncalibratedSources.ToList()),
                ["clockOffsets"] = offsets,
                ["importedSampleCount"] = importedCount,
                ["calibratedSampleCount"] = calibratedCount,
                ["trackCount"] = calibration.Timeline.Tracks.Count,
                ["points"] = points
            };
        }

        private static bool ValuesEqual(TimelineSample a, TimelineSample b)
        {
            if (a.HasPosition != b.HasPosition)
            {
                return false;
            }
            if (!string.Equals(a.Text, b.Text, StringComparison.Ordinal))
            {
                return false;
            }
            if (double.IsNaN(a.Value) && double.IsNaN(b.Value))
            {
                return true;
            }
            return Math.Abs(a.Value - b.Value) <= ValueTol;
        }

        private static int CountSamples(IReadOnlyList<Track> tracks)
        {
            int n = 0;
            for (int i = 0; i < tracks.Count; i++)
            {
                n += tracks[i].Samples.Count;
            }
            return n;
        }

        private static VdrCsvMapping Mapping()
        {
            return new VdrCsvMapping
            {
                TimeColumn = "time_utc",
                Columns =
                {
                    new VdrCsvColumnMapping { Column = "sog_kn", Kind = TrackKind.SpeedOverGround },
                    new VdrCsvColumnMapping { Column = "cog_deg", Kind = TrackKind.CourseOverGround }
                }
            };
        }

        private static string FormatUtc(DateTimeOffset value)
        {
            return value.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffZ", CultureInfo.InvariantCulture);
        }

        private static JsonNode Finite(double d)
        {
            return double.IsNaN(d) || double.IsInfinity(d) ? null : JsonValue.Create(d);
        }

        private static JsonArray StringArray(IReadOnlyList<string> items)
        {
            var arr = new JsonArray();
            if (items == null)
            {
                return arr;
            }
            for (int i = 0; i < items.Count; i++)
            {
                arr.Add(items[i]);
            }
            return arr;
        }

        private static JsonSerializerOptions JsonOptions()
        {
            return new JsonSerializerOptions
            {
                WriteIndented = true,
                Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
                TypeInfoResolver = new System.Text.Json.Serialization.Metadata.DefaultJsonTypeInfoResolver()
            };
        }

        private static void WriteJson(string path, JsonNode node)
        {
            File.WriteAllText(path, node.ToJsonString(JsonOptions()) + "\n", new UTF8Encoding(false));
        }
    }
}
