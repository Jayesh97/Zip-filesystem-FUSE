import errno
import fuse
import os,sys
import stat
import time
from fuse import FUSE, FuseOSError, LoggingMixIn, Operations
from os import path
import zipfile

class Fs(Operations):
    def __init__(self, root, base='.'):
        self.root = root
	self.base=path.realpath(base)
        self.__handles={}
  	self._load_time=time.time()

    def _full_path(self, partial):
        partial = partial.lstrip("/")
        path = os.path.join(self.root, partial)
        return path

    def _metafiles(self, p):
        meta = os.path.join(self.base, 'meta', os.path.basename(p))
        return [meta + suffix for suffix in ('.dir', '.stream', '.jump')]

    def access(self, p, m):

        full_path = self._full_path(p)
        if not os.access(full_path, m):
            raise FuseOSError(errno.EACCES)

    def getattr(self, path, fh=None):
        if (path == '/'):
            uid, gid, pid = fuse.fuse_get_context()

            return {
                'st_uid': uid,
                'st_gid': gid,
                'st_mode': stat.S_IFDIR | 0555,
                'st_nlink': 2,

                'st_atime': self._load_time,
                'st_mtime': self._load_time,
                'st_ctime': self._load_time,
            }
        else:
            full_path = self._full_path(path)
            st = os.lstat(full_path)
            return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                         'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    def readdir(self, path, fh):
        full_path = self._full_path(path)
        yield '.'
        yield '..'
        dirents = []
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, a1):
        for meta in self._metafiles(a1):
            link = os.readlink(meta)

            try:
                name, ext = link.rsplit('.', 1)

                if meta.rsplit('.', 1)[1] == ext:
                    return name
            except ValueError:
                continue

        return -errno.EINVAL


    def rmdir(self, a1):
        full_path = self._full_path(a1)
        return os.rmdir(full_path)

    def mkdir(self, a1, mode):
        return os.mkdir(self._full_path(a1), mode)

    def statfs(self, a1):
        full_path = self._full_path(a1)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))


    def symlink(self, t, s):
        for t, s in zip(self._metafiles(t), self._metafiles(s)):
            if not path.islink(t) or os.readlink(t) != s:
                os.symlink(s, t)

    def rename(self, old, new):
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, t, n):
        return os.link(self._full_path(t), self._full_path(n))

    def open(self, p, f):
        full_path = self._full_path(p)
        return os.open(full_path, f)

    def create(self, p, m, fi=None):
        full_path = self._full_path(p)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, m)

    def read(self, path, length, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def flush(self, path, fh):
        return os.fsync(fh)

    def release(self, path, fh):
        return os.close(fh)



def main(mountpoint, root):
    FUSE(Fs(root), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
   zip_ref = zipfile.ZipFile(sys.argv[1],'r')
   zip_ref.extractall("store")
   main(sys.argv[2], "store")

