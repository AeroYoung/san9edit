from pathlib import Path
import json
import shutil

def get_project_root() -> Path:
    # 从当前脚本所在目录开始
    current = Path(__file__).resolve().parent

    # 标志文件：出现任意一个就认为是项目根目录
    markers = (".git", "pyproject.toml", "requirements.txt", "setup.py", "Pipfile", ".env")

    for parent in [current] + list(current.parents):
        if any((parent / marker).exists() for marker in markers):
            return parent

    # 如果都没找到，就退回脚本所在目录
    return current

PROJECT_ROOT = get_project_root()

Dst_Dir = get_project_root() / "assets"
SRC_Dir = Path(__file__).resolve().parent

def copy_file(src, dst_dir, new_name=None, overwrite=True):
    """
    把 src 复制到 dst_dir。
    new_name: 如果传了，就改名为 new_name；不传则保持原名。
    overwrite: 是否覆盖同名文件。
    """
    src = Path(src)
    dst_dir = Path(dst_dir)

    if not src.is_file():
        raise FileNotFoundError(f"源文件不存在：{src}")

    dst_dir.mkdir(parents=True, exist_ok=True)
    dst = dst_dir / (new_name if new_name else src.name)

    # 避免源和目标是同一个文件
    if src.resolve() == dst.resolve():
        raise shutil.SameFileError(f"源文件和目标文件相同：{src}")

    if dst.exists():
        if not overwrite:
            raise FileExistsError(f"目标已存在：{dst}")
        # 如果目标是目录，不能直接覆盖
        if dst.is_dir():
            raise IsADirectoryError(f"目标是一个目录：{dst}")
        # 直接 copy2 也会覆盖，这里先删更明确
        dst.unlink()

    shutil.copy2(src, dst)
    return dst

def main():
    try:
        copy_file(SRC_Dir / "map_with_boundaries.geojson",Dst_Dir,"map.geojson" )
        print("复制了map.geojson")
        copy_file(SRC_Dir / "roads.geojson",Dst_Dir )
        print("复制了roads.geojson")
    except Exception:
        pass
    

if __name__ == "__main__":
    main()