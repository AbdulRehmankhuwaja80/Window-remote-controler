using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;

namespace RemoDesk.Host.FileServer
{
    public class FileEntry
    {
        public string Name { get; set; } = string.Empty;
        public string Path { get; set; } = string.Empty;
        public bool IsDirectory { get; set; }
        public long Size { get; set; }
        public DateTime ModifiedAt { get; set; }
    }

    public class RemoteFileManager
    {
        private readonly List<string> _authorizedRoots;

        public RemoteFileManager(List<string> authorizedRoots)
        {
            _authorizedRoots = authorizedRoots;
        }

        public bool IsPathAuthorized(string requestedPath)
        {
            if (string.IsNullOrWhiteSpace(requestedPath)) return false;
            try
            {
                string fullPath = Path.GetFullPath(requestedPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                foreach (var root in _authorizedRoots)
                {
                    if (string.IsNullOrWhiteSpace(root)) continue;
                    string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
                    if (fullPath.Equals(fullRoot, StringComparison.OrdinalIgnoreCase) ||
                        fullPath.StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase))
                    {
                        return true;
                    }
                }
            }
            catch
            {
                return false;
            }
            return false;
        }

        public List<FileEntry> GetRoots()
        {
            var result = new List<FileEntry>();
            foreach (var root in _authorizedRoots)
            {
                if (Directory.Exists(root))
                {
                    var di = new DirectoryInfo(root);
                    result.Add(new FileEntry
                    {
                        Name = di.Name,
                        Path = di.FullName,
                        IsDirectory = true,
                        Size = 0,
                        ModifiedAt = di.LastWriteTimeUtc,
                    });
                }
            }
            return result;
        }

        public List<FileEntry> ListDirectory(string path)
        {
            if (string.IsNullOrEmpty(path)) return GetRoots();

            if (!IsPathAuthorized(path))
            {
                throw new UnauthorizedAccessException("Path is not within authorized directories.");
            }

            var entries = new List<FileEntry>();
            var di = new DirectoryInfo(path);

            foreach (var dir in di.GetDirectories())
            {
                try
                {
                    entries.Add(new FileEntry
                    {
                        Name = dir.Name,
                        Path = dir.FullName,
                        IsDirectory = true,
                        Size = 0,
                        ModifiedAt = dir.LastWriteTimeUtc,
                    });
                }
                catch { }
            }

            foreach (var file in di.GetFiles())
            {
                try
                {
                    entries.Add(new FileEntry
                    {
                        Name = file.Name,
                        Path = file.FullName,
                        IsDirectory = false,
                        Size = file.Length,
                        ModifiedAt = file.LastWriteTimeUtc,
                    });
                }
                catch { }
            }

            return entries;
        }

        public byte[] ReadFileChunk(string path, long offset, int length, out bool isEof, out string sha256)
        {
            if (!IsPathAuthorized(path))
            {
                throw new UnauthorizedAccessException("Unauthorized file access.");
            }

            using var fs = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
            fs.Seek(offset, SeekOrigin.Begin);
            byte[] buffer = new byte[length];
            int read = fs.Read(buffer, 0, length);
            isEof = (fs.Position >= fs.Length);

            if (read < length)
            {
                Array.Resize(ref buffer, read);
            }

            using var sha = SHA256.Create();
            byte[] hash = sha.ComputeHash(buffer);
            sha256 = BitConverter.ToString(hash).Replace("-", "").ToLowerInvariant();

            return buffer;
        }

        public void WriteFileChunk(string path, long offset, byte[] data, bool isComplete)
        {
            if (!IsPathAuthorized(path))
            {
                throw new UnauthorizedAccessException("Unauthorized file write destination.");
            }

            string? dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }

            using var fs = new FileStream(path, FileMode.OpenOrCreate, FileAccess.Write, FileShare.None);
            fs.Seek(offset, SeekOrigin.Begin);
            fs.Write(data, 0, data.Length);
        }

        public void DeleteFile(string path)
        {
            if (!IsPathAuthorized(path))
            {
                throw new UnauthorizedAccessException("Unauthorized deletion target.");
            }

            if (File.Exists(path))
            {
                File.Delete(path);
            }
        }
    }
}
