using System;
using System.Collections.Generic;

namespace Mcis.Core
{
    /// <summary>
    /// 通用操作结果包装结构，避免在高频或解析路径抛出异常。
    /// </summary>
    /// <typeparam name="T">结果值类型。</typeparam>
    public readonly struct Result<T> : IEquatable<Result<T>>
    {
        /// <summary>是否操作成功。</summary>
        public bool IsSuccess { get; }

        /// <summary>成功时的返回值。</summary>
        public T Value { get; }

        /// <summary>失败时的错误代码。</summary>
        public string ErrorCode { get; }

        /// <summary>失败时的错误描述信息。</summary>
        public string ErrorMessage { get; }

        /// <summary>构造操作结果。</summary>
        public Result(bool isSuccess, T value, string errorCode, string errorMessage)
        {
            IsSuccess = isSuccess;
            Value = value;
            ErrorCode = errorCode;
            ErrorMessage = errorMessage;
        }

        /// <summary>创建成功结果。</summary>
        public static Result<T> Ok(T value)
        {
            return new Result<T>(true, value, null, null);
        }

        /// <summary>创建失败结果。</summary>
        public static Result<T> Fail(string code, string message)
        {
            return new Result<T>(false, default(T), code, message);
        }

        /// <inheritdoc />
        public bool Equals(Result<T> other)
        {
            return IsSuccess == other.IsSuccess &&
                   EqualityComparer<T>.Default.Equals(Value, other.Value) &&
                   string.Equals(ErrorCode, other.ErrorCode, StringComparison.Ordinal) &&
                   string.Equals(ErrorMessage, other.ErrorMessage, StringComparison.Ordinal);
        }

        /// <inheritdoc />
        public override bool Equals(object obj)
        {
            return obj is Result<T> other && Equals(other);
        }

        /// <inheritdoc />
        public override int GetHashCode()
        {
            unchecked
            {
                int hash = IsSuccess.GetHashCode();
                hash = (hash * 397) ^ (Value != null ? EqualityComparer<T>.Default.GetHashCode(Value) : 0);
                hash = (hash * 397) ^ (ErrorCode != null ? ErrorCode.GetHashCode() : 0);
                hash = (hash * 397) ^ (ErrorMessage != null ? ErrorMessage.GetHashCode() : 0);
                return hash;
            }
        }

        /// <inheritdoc />
        public override string ToString()
        {
            if (IsSuccess)
            {
                return string.Format("Ok({0})", Value);
            }
            return string.Format("Fail[{0}]: {1}", ErrorCode, ErrorMessage);
        }
    }
}
