import pathlib
import platform
import subprocess

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext


ROOT_DIR = pathlib.Path(__file__).parent.resolve()
PACKAGE_NAME = "tun2socks"
BINDING_NAME = "tun2socks"


class CMakeExtension(Extension):
    """A setuptools extension built by CMake."""

    def __init__(self, name):
        super().__init__(name, sources=[])


class BuildTun2socks(build_ext):
    """Build the Go static archive and the pybind11 extension."""

    def build_extension(self, ext):
        if self.dry_run:
            return

        system = platform.system()
        build_dir = pathlib.Path(self.build_temp).resolve() / ext.name
        go_dir = build_dir / "go"
        cmake_dir = build_dir / "cmake"
        extension_path = pathlib.Path(self.get_ext_fullpath(ext.name)).resolve()
        extension_path.parent.mkdir(parents=True, exist_ok=True)
        go_dir.mkdir(parents=True, exist_ok=True)
        cmake_dir.mkdir(parents=True, exist_ok=True)

        archive_name = f"{BINDING_NAME}.lib" if system == "Windows" else f"{BINDING_NAME}.a"
        archive_path = go_dir / archive_name

        env = __import__("os").environ.copy()
        env["CGO_ENABLED"] = "1"
        subprocess.run(
            [
                "go", "build", "-C", "tun2socks-go", "-o", str(archive_path),
                "-buildmode=c-archive", "-trimpath", "-ldflags", "-s -w -buildid=",
            ],
            cwd=ROOT_DIR, env=env, check=True,
        )

        cmake_args = [
            "cmake", "-S", str(ROOT_DIR), "-B", str(cmake_dir),
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_LIBRARY_OUTPUT_DIRECTORY={extension_path.parent.as_posix()}",
            f"-DTUN2SOCKS_ARCHIVE={archive_path.as_posix()}",
            f"-DTUN2SOCKS_INCLUDE_DIR={go_dir.as_posix()}",
        ]
        if system == "Windows":
            cmake_args += ["-G", "MinGW Makefiles"]
        subprocess.run(cmake_args, cwd=ROOT_DIR, env=env, check=True)
        subprocess.run(
            ["cmake", "--build", str(cmake_dir), "--config", "Release",
             "--target", BINDING_NAME, "--parallel"],
            cwd=ROOT_DIR, env=env, check=True,
        )

        built = list(extension_path.parent.glob("tun2socks*.pyd")) + list(extension_path.parent.glob("tun2socks*.so"))
        if not built:
            raise RuntimeError("CMake completed but no tun2socks extension was produced")
        if built[0] != extension_path:
            import shutil
            shutil.copy2(built[0], extension_path)


with (ROOT_DIR / "README.md").open("r", encoding="utf-8") as file:
    long_description = file.read()


setup(
    name=PACKAGE_NAME,
    version="2.5.2.3",
    license="GPL-3.0-only",
    description="Python bindings for go tun2socks.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.8",
    cmdclass={"build_ext": BuildTun2socks},
    ext_modules=[CMakeExtension("tun2socks.tun2socks")],
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
)
