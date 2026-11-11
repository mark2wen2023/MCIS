using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Mcis.Domain.Evidence
{
    /// <summary>SHA-256 十六进制小写摘要（与 Data 层 Sha256Util 输出一致）。</summary>
    public static class Sha256Hex
    {
        public const int HexLength = 64;
        public static readonly string Zero = new string('0', HexLength);

        public static string Of(byte[] data)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return ToHex(sha.ComputeHash(data ?? Array.Empty<byte>()));
            }
        }

        public static string Of(Stream stream)
        {
            if (stream == null)
            {
                throw new ArgumentNullException(nameof(stream));
            }

            using (SHA256 sha = SHA256.Create())
            {
                return ToHex(sha.ComputeHash(stream));
            }
        }

        public static string OfUtf8(string text)
        {
            return Of(new UTF8Encoding(false).GetBytes(text ?? string.Empty));
        }

        /// <summary>是否为 64 位十六进制（大小写均可，比较前请用 <see cref="Normalize"/>）。</summary>
        public static bool IsValid(string hex)
        {
            if (hex == null || hex.Length != HexLength)
            {
                return false;
            }

            for (int i = 0; i < hex.Length; i++)
            {
                char c = hex[i];
                bool ok = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F');
                if (!ok)
                {
                    return false;
                }
            }

            return true;
        }

        public static string Normalize(string hex)
        {
            return hex == null ? null : hex.ToLowerInvariant();
        }

        private static string ToHex(byte[] hash)
        {
            var sb = new StringBuilder(hash.Length * 2);
            for (int i = 0; i < hash.Length; i++)
            {
                sb.Append(hash[i].ToString("x2"));
            }

            return sb.ToString();
        }
    }
}
