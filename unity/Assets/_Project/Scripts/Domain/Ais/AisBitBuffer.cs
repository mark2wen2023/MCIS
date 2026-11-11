using System;
using System.Globalization;
using System.Text;

namespace Mcis.Domain.Ais
{
    /// <summary>
    /// AIS 6-bit 载荷比特流读写缓冲与 NMEA 6-bit 装甲/解装甲工具。
    /// </summary>
    public sealed class AisBitBuffer
    {
        private readonly byte[] _bits;
        private int _bitLength;

        /// <summary>有效比特总长度。</summary>
        public int BitLength
        {
            get { return _bitLength; }
        }

        /// <summary>按指定比特容量构造比特缓冲。</summary>
        public AisBitBuffer(int bitCapacity = 512)
        {
            _bits = new byte[Math.Max(bitCapacity, 64)];
            _bitLength = 0;
        }

        private AisBitBuffer(byte[] bits, int bitLength)
        {
            _bits = bits;
            _bitLength = bitLength;
        }

        /// <summary>从 6-bit 装甲载荷字符串解码构造比特流。</summary>
        public static bool TryFromPayload(string payload, int fillBits, out AisBitBuffer buffer, out string error)
        {
            buffer = null;
            error = null;
            if (string.IsNullOrEmpty(payload))
            {
                error = "Empty AIS payload.";
                return false;
            }
            if (fillBits < 0 || fillBits > 5)
            {
                error = "Invalid fill bits count.";
                return false;
            }

            int totalBits = payload.Length * 6 - fillBits;
            if (totalBits <= 0)
            {
                error = "Payload bit length is non-positive after removing fill bits.";
                return false;
            }

            byte[] bits = new byte[payload.Length * 6];
            int bitIndex = 0;
            for (int i = 0; i < payload.Length; i++)
            {
                int val = payload[i] - 48;
                if (val > 40)
                {
                    val -= 8;
                }
                if (val < 0 || val > 63)
                {
                    error = string.Format(CultureInfo.InvariantCulture, "Invalid 6-bit armor char '{0}'.", payload[i]);
                    return false;
                }

                bits[bitIndex++] = (byte)((val >> 5) & 1);
                bits[bitIndex++] = (byte)((val >> 4) & 1);
                bits[bitIndex++] = (byte)((val >> 3) & 1);
                bits[bitIndex++] = (byte)((val >> 2) & 1);
                bits[bitIndex++] = (byte)((val >> 1) & 1);
                bits[bitIndex++] = (byte)(val & 1);
            }

            buffer = new AisBitBuffer(bits, totalBits);
            return true;
        }

        /// <summary>读取无符号整数（最多 32 位）。</summary>
        public uint GetUInt(int startBit, int length)
        {
            if (length <= 0 || startBit < 0 || startBit >= _bitLength)
            {
                return 0u;
            }
            uint result = 0u;
            int end = startBit + length;
            for (int i = startBit; i < end; i++)
            {
                result <<= 1;
                if (i < _bitLength && _bits[i] != 0)
                {
                    result |= 1u;
                }
            }
            return result;
        }

        /// <summary>读取二进制补码有符号整数（最多 32 位）。</summary>
        public int GetInt(int startBit, int length)
        {
            if (length <= 0 || startBit < 0 || startBit >= _bitLength)
            {
                return 0;
            }
            uint unsignedVal = GetUInt(startBit, length);
            uint signBit = 1u << (length - 1);
            if ((unsignedVal & signBit) != 0u)
            {
                uint mask = length >= 32 ? 0xFFFFFFFFu : ((1u << length) - 1u);
                return (int)(unsignedVal | ~mask);
            }
            return (int)unsignedVal;
        }

        /// <summary>读取 AIS 6-bit ASCII 字符串并去除尾部 '@' 与空格填充。</summary>
        public string GetString(int startBit, int bitLength)
        {
            if (bitLength <= 0 || startBit < 0 || startBit >= _bitLength)
            {
                return string.Empty;
            }
            int charCount = bitLength / 6;
            StringBuilder sb = new StringBuilder(charCount);
            for (int i = 0; i < charCount; i++)
            {
                int pos = startBit + i * 6;
                if (pos >= _bitLength)
                {
                    break;
                }
                uint val = GetUInt(pos, 6);
                char ch = val < 32u ? (char)(val + 64u) : (char)val;
                sb.Append(ch);
            }
            return sb.ToString().TrimEnd('@', ' ');
        }

        /// <summary>写入无符号整数到指定比特区间。</summary>
        public void SetUInt(int startBit, int length, uint value)
        {
            int end = startBit + length;
            if (end > _bitLength)
            {
                _bitLength = end;
            }
            for (int i = 0; i < length; i++)
            {
                int bitPos = end - 1 - i;
                _bits[bitPos] = (byte)((value >> i) & 1u);
            }
        }

        /// <summary>写入有符号二进制补码整数到指定比特区间。</summary>
        public void SetInt(int startBit, int length, int value)
        {
            uint mask = length >= 32 ? 0xFFFFFFFFu : ((1u << length) - 1u);
            SetUInt(startBit, length, ((uint)value) & mask);
        }

        /// <summary>写入 AIS 6-bit ASCII 字符串（不足部分以 '@' 即 0 填充）。</summary>
        public void SetString(int startBit, int bitLength, string text)
        {
            int charCount = bitLength / 6;
            string safe = (text ?? string.Empty).ToUpperInvariant();
            for (int i = 0; i < charCount; i++)
            {
                char ch = i < safe.Length ? safe[i] : '@';
                uint code;
                if (ch >= '@' && ch <= '_')
                {
                    code = (uint)(ch - 64);
                }
                else if (ch >= ' ' && ch <= '?')
                {
                    code = (uint)ch;
                }
                else
                {
                    code = 0u;
                }
                SetUInt(startBit + i * 6, 6, code);
            }
        }

        /// <summary>将当前比特缓冲编码为 6-bit 装甲载荷与填充位数。</summary>
        public string ToArmoredPayload(out int fillBits)
        {
            int rem = _bitLength % 6;
            fillBits = rem == 0 ? 0 : (6 - rem);
            int total = _bitLength + fillBits;
            int charCount = total / 6;
            StringBuilder sb = new StringBuilder(charCount);
            for (int i = 0; i < charCount; i++)
            {
                uint val = GetUInt(i * 6, 6);
                int ascii = (int)val + 48;
                if (ascii > 87)
                {
                    ascii += 8;
                }
                sb.Append((char)ascii);
            }
            return sb.ToString();
        }
    }
}
