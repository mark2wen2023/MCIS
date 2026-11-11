using System;
using System.IO;
using System.Security.Cryptography;
using System.Text;

namespace Mcis.Data.CasePackage
{
    /// <summary>SHA-256 文件与字节摘要工具（十六进制小写）。</summary>
    public static class Sha256Util
    {
        public static string ComputeFileHex(string filePath)
        {
            using (FileStream stream = File.OpenRead(filePath))
            {
                return ComputeStreamHex(stream);
            }
        }

        public static string ComputeBytesHex(byte[] data)
        {
            if (data == null)
            {
                data = Array.Empty<byte>();
            }

            using (SHA256 sha = SHA256.Create())
            {
                return ToHex(sha.ComputeHash(data));
            }
        }

        public static string ComputeStreamHex(Stream stream)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return ToHex(sha.ComputeHash(stream));
            }
        }

        public static string ToHex(byte[] hash)
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
